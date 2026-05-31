from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from aiohttp import web

from .config import StreamConfig
from .store import StreamItem, TokenStore

log = logging.getLogger(__name__)

# Telethon requires request_size to be a power of 2 between 4 KiB and 1 MiB,
# and the offset must be a multiple of request_size. 1 MiB chunks minimize
# per-request overhead for video playback.
CHUNK = 1024 * 1024

_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def _parse_range(header: str, size: int) -> tuple[int, int] | None:
    m = _RANGE_RE.match(header.strip())
    if not m:
        return None
    start_s, end_s = m.group(1), m.group(2)
    if start_s == "" and end_s == "":
        return None
    if start_s == "":
        # Suffix range: last N bytes.
        n = int(end_s)
        if n == 0:
            return None
        return max(0, size - n), size - 1
    start = int(start_s)
    end = int(end_s) if end_s else size - 1
    if start > end or start >= size:
        return None
    return start, min(end, size - 1)


def build_app(client: Any, store: TokenStore) -> web.Application:
    """`client` is a Telethon TelegramClient (typed Any to avoid an import-time dep)."""

    async def handle(request: web.Request) -> web.StreamResponse:
        token = request.match_info["token"]
        item = store.get(token)
        if item is None:
            return web.Response(status=404, text="unknown or expired token")

        size = item.size
        range_header = request.headers.get("Range")
        rng = _parse_range(range_header, size) if range_header else None

        if rng is None:
            start, end = 0, size - 1
            status = 200
        else:
            start, end = rng
            status = 206

        length = end - start + 1
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": item.mime_type or "video/mp4",
            "Content-Disposition": f'inline; filename="{item.file_name}"',
        }
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"

        response = web.StreamResponse(status=status, headers=headers)
        await response.prepare(request)

        if request.method == "HEAD":
            await response.write_eof()
            return response

        aligned_offset = (start // CHUNK) * CHUNK
        skip = start - aligned_offset
        remaining = length

        try:
            async for chunk in client.iter_download(
                item.document,
                offset=aligned_offset,
                request_size=CHUNK,
            ):
                if skip:
                    chunk = chunk[skip:]
                    skip = 0
                    if not chunk:
                        continue
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                await response.write(chunk)
                remaining -= len(chunk)
                if remaining <= 0:
                    break
        except (asyncio.CancelledError, ConnectionResetError):
            log.debug("client disconnected from stream %s", token)
            raise
        except Exception:
            log.exception("error while streaming %s", token)
            # Connection is already in body phase; best we can do is close.

        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_route("GET", "/stream/{token}", handle)
    app.router.add_route("HEAD", "/stream/{token}", handle)
    return app


async def run(cfg: StreamConfig, client: Any, store: TokenStore) -> None:
    app = build_app(client, store)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, cfg.host, cfg.port)
    await site.start()
    log.info("stream server listening on http://%s:%d", cfg.host, cfg.port)
    # Block forever; cancellation propagates from the main task.
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
