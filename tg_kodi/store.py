from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamItem:
    message: Any  # telethon Message
    document: Any  # telethon Document
    size: int
    mime_type: str
    file_name: str
    added_at: float


class TokenStore:
    """In-memory map of opaque token -> Telegram media reference."""

    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._items: dict[str, StreamItem] = {}

    def add(self, item: StreamItem) -> str:
        self._gc()
        token = secrets.token_urlsafe(16)
        self._items[token] = item
        return token

    def get(self, token: str) -> StreamItem | None:
        self._gc()
        return self._items.get(token)

    def _gc(self) -> None:
        cutoff = time.time() - self._ttl
        stale = [k for k, v in self._items.items() if v.added_at < cutoff]
        for k in stale:
            del self._items[k]
