from __future__ import annotations

import logging
import time
from typing import Any, Coroutine, cast
from urllib.parse import quote

from telethon import TelegramClient, events

from .config import Config
from .kodi import KodiClient
from .store import StreamItem, TokenStore

log = logging.getLogger(__name__)


def _video_info(message) -> tuple[int, str, str] | None:
    """Return (size, mime_type, file_name) if this message carries a video, else None."""
    f = message.file
    if f is None or f.size is None:
        return None
    mime = (f.mime_type or "").lower()
    if not mime.startswith("video/"):
        return None
    name = f.name or f"video{f.ext or '.mp4'}"
    return f.size, mime, name


def register_handlers(
    client: TelegramClient,
    cfg: Config,
    store: TokenStore,
    kodi: KodiClient,
) -> None:
    allowed = cfg.telegram.whitelist

    @client.on(events.NewMessage(incoming=True))
    async def on_message(event):
        sender_id = event.sender_id
        if sender_id not in allowed:
            log.info("rejecting message from non-whitelisted user %s", sender_id)
            # Stay quiet to non-whitelisted strangers; only reply in DMs.
            if event.is_private:
                await event.reply("Not authorized.")
            return

        info = _video_info(event.message)
        if info is None:
            if event.is_private:
                await event.reply("Send a video file and I'll play it on Kodi.")
            return

        size, mime, name = info
        token = store.add(
            StreamItem(
                message=event.message,
                document=event.message,  # Telethon iter_download accepts a Message directly
                size=size,
                mime_type=mime,
                file_name=name,
                added_at=time.time(),
            )
        )

        url = f"http://{cfg.stream.host}:{cfg.stream.port}/stream/{quote(token)}"
        log.info("queued %s (%d bytes) as %s", name, size, token)
        await kodi.play(url)
        await event.reply(f"Playing: {name}")


async def run(cfg: Config, store: TokenStore, kodi: KodiClient) -> TelegramClient:
    client = TelegramClient("bot", cfg.telegram.api_id, cfg.telegram.api_hash)
    # Telethon's start() returns a coroutine when an event loop is running, but its
    # static signature claims it returns TelegramClient directly — hence the cast.
    await cast(
        Coroutine[Any, Any, TelegramClient],
        client.start(bot_token=cfg.telegram.bot_token),
    )
    register_handlers(client, cfg, store, kodi)
    log.info("telegram bot connected")
    return client
