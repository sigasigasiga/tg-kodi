# tg-kodi

Send a video to a Telegram bot → it plays on Kodi immediately, streamed (no full download first).

## How it works

```
You ──▶ Bot ──▶ tg-kodi (Telethon)
                   │
                   ├─ checks whitelist
                   ├─ local HTTP server with Range support
                   │  (proxies Telegram chunks on demand)
                   └─ Kodi JSON-RPC: Player.Open(http://127.0.0.1:9988/stream/<token>)
                                                                ▼
                                                          Kodi plays
```

Telethon is used over MTProto (not the plain Bot API) so file size is not capped at 20 MB — bots can fetch up to 2 GB.

## Setup

### 1. Telegram credentials

- Go to <https://my.telegram.org/apps> and create an app to get `api_id` and `api_hash`.
- Talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the bot token.
- In BotFather, also run `/setprivacy` → **Disable** so the bot can see videos in groups, if you want that. For DM-only use, leave it on.
- Find your numeric user ID with [@userinfobot](https://t.me/userinfobot).

### 2. Kodi

In Kodi: **Settings → Services → Control**:

- Enable **Allow remote control via HTTP**.
- Note the port (default 8080), username, password.

### 3. Install & configure

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

cp config.example.toml config.toml
# edit config.toml: api_id, api_hash, bot_token, whitelist, kodi user/pass
```

### 4. Run

```sh
python -m tg_kodi -c config.toml
```

Send a video to your bot from a whitelisted account. Kodi should start playing within a couple of seconds.

## Notes

- **File reference TTL.** Telegram file references go stale after roughly an hour. `stream.ttl_seconds` controls how long a sent video stays playable through the server; the default (50 min) sits just inside the safe window. If a stream stops working long after it was sent, just send the video again.
- **No full download.** The HTTP proxy serves bytes on demand. Kodi requests a range, the server pulls just those chunks from Telegram. Seeking works.
- **Where it listens.** Defaults to `127.0.0.1:9988` — same machine as Kodi only. Change `stream.host` to `0.0.0.0` (and open the firewall) to expose it on the LAN.
- **One concurrent stream.** Sending a new video stops the current playback and starts the new one. To queue instead, change `KodiClient.play` to call `Playlist.Add` rather than `Player.Stop` + `Player.Open`.
