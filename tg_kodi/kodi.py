from __future__ import annotations

import logging

import aiohttp

from .config import KodiConfig

log = logging.getLogger(__name__)


class KodiClient:
    def __init__(self, cfg: KodiConfig):
        self._url = f"http://{cfg.host}:{cfg.port}/jsonrpc"
        self._auth = (
            aiohttp.BasicAuth(cfg.user, cfg.password) if cfg.user else None
        )

    async def play(self, url: str) -> None:
        # Stop current playback so the new video takes over even if something
        # is already playing.
        async with aiohttp.ClientSession() as session:
            await self._call(session, "Player.Stop", {"playerid": 1})
            await self._call(
                session,
                "Player.Open",
                {"item": {"file": url}},
            )

    async def _call(
        self,
        session: aiohttp.ClientSession,
        method: str,
        params: dict,
    ) -> dict | None:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            async with session.post(
                self._url, json=payload, auth=self._auth, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                body = await resp.json(content_type=None)
                if "error" in body:
                    log.warning("kodi %s error: %s", method, body["error"])
                return body
        except Exception as e:
            log.warning("kodi %s failed: %s", method, e)
            return None
