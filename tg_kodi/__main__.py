from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from pathlib import Path
from typing import Any, Coroutine, cast

from . import bot, config, server
from .kodi import KodiClient
from .store import TokenStore


async def main_async(cfg_path: Path) -> None:
    cfg = config.load(cfg_path)
    store = TokenStore(ttl_seconds=cfg.stream.ttl_seconds)
    kodi = KodiClient(cfg.kodi)

    client = await bot.run(cfg, store, kodi)
    server_task = asyncio.create_task(server.run(cfg.stream, client, store))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    try:
        # Run until a signal arrives, the bot disconnects, or the server crashes.
        # Telethon's run_until_disconnected/disconnect return a coroutine when the
        # loop is running; the static signature doesn't reflect that, hence the cast.
        disconnect_task = asyncio.create_task(
            cast(Coroutine[Any, Any, None], client.run_until_disconnected())
        )
        stop_task = asyncio.create_task(stop.wait())
        done, _ = await asyncio.wait(
            {disconnect_task, server_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in done:
            if t is stop_task:
                continue
            exc = t.exception()
            if exc is not None:
                raise exc
    finally:
        server_task.cancel()
        await asyncio.gather(server_task, return_exceptions=True)
        await cast(Coroutine[Any, Any, None], client.disconnect())


def main() -> None:
    parser = argparse.ArgumentParser(prog="tg-kodi")
    parser.add_argument(
        "-c", "--config", default="config.toml", help="path to config TOML"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    asyncio.run(main_async(Path(args.config)))


if __name__ == "__main__":
    main()
