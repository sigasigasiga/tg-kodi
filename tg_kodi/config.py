from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    bot_token: str
    whitelist: frozenset[int]


@dataclass(frozen=True)
class StreamConfig:
    host: str
    port: int
    ttl_seconds: int


@dataclass(frozen=True)
class KodiConfig:
    host: str
    port: int
    user: str
    password: str


@dataclass(frozen=True)
class Config:
    telegram: TelegramConfig
    stream: StreamConfig
    kodi: KodiConfig


def load(path: Path) -> Config:
    data = tomllib.loads(path.read_text())

    tg = data["telegram"]
    if not tg.get("api_id") or not tg.get("api_hash") or not tg.get("bot_token"):
        raise ValueError("telegram.api_id, api_hash, and bot_token are required")

    return Config(
        telegram=TelegramConfig(
            api_id=int(tg["api_id"]),
            api_hash=str(tg["api_hash"]),
            bot_token=str(tg["bot_token"]),
            whitelist=frozenset(int(x) for x in tg.get("whitelist", [])),
        ),
        stream=StreamConfig(
            host=str(data["stream"]["host"]),
            port=int(data["stream"]["port"]),
            ttl_seconds=int(data["stream"].get("ttl_seconds", 3000)),
        ),
        kodi=KodiConfig(
            host=str(data["kodi"]["host"]),
            port=int(data["kodi"]["port"]),
            user=str(data["kodi"].get("user", "")),
            password=str(data["kodi"].get("password", "")),
        ),
    )
