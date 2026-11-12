# Channel Manager Bot

Telegram channel manager built with Python 3.12, Kurigram, APScheduler 3.x and JSON file storage.

## Implemented

- Owner and multi-admin access control
- Multi-channel registration, listing, removal and default-channel setting
- Bot-admin permission check when registering a channel
- Quick post flow: send/forward one message, select one or all channels, preview destinations, confirm
- Telegram copy semantics preserve supported text formatting and media
- Draft references to source messages
- One-time scheduling in a configurable timezone (default Asia/Jakarta), persisted and restored after restart
- Schedule listing and cancellation
- Named template references
- Posting history, basic statistics and activity audit log
- JSON storage with per-file asyncio locks and atomic temp-file replacement
- Rotating logs and graceful shutdown
- GitHub Actions compile check

## Requirements

- Ubuntu/Linux or another supported Python platform
- Python 3.12
- Telegram bot token from @BotFather
- API ID and API hash from https://my.telegram.org
- Bot must be an administrator in each managed channel with permission to post

## Setup

```bash
git clone https://github.com/aryasep-a/channel-manager-bot.git
cd channel-manager-bot
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

Configure `BOT_TOKEN`, `API_ID`, `API_HASH`, and `OWNER_ID`. Never commit `.env`.

## First run

1. Open the bot as the Telegram account whose ID is `OWNER_ID`, then send `/start`.
2. Add the bot to each channel as administrator with permission to post messages.
3. Run `/addchannel @channelusername`.
4. Run `/channels` to verify.
5. Run `/post`, send or forward a message, choose destinations, and confirm.
6. To schedule, run `/schedule YYYY-MM-DD HH:MM`, then send the message and choose destinations.

## Commands

| Command | Description |
|---|---|
| /start, /help | Start and help |
| /addchannel @username | Register channel |
| /delchannel CHANNEL_ID | Remove channel |
| /channels | List registered channels |
| /setdefault CHANNEL_ID | Set default channel preference |
| /addadmin USER_ID | Owner adds admin |
| /deladmin USER_ID | Owner removes admin |
| /admins | List admins (Owner only) |
| /post | Quick publish flow |
| /schedule YYYY-MM-DD HH:MM | Schedule a post |
| /schedules | List schedules |
| /cancel_schedule ID | Cancel pending schedule |
| /drafts | List saved draft references |
| /template_save NAME | Reply to a message to save a template reference |
| /templates | List template references |
| /history | Recent successful posts |
| /stats | Basic statistics |
| /settings | Current settings |
| /cancel | Cancel active composition |

## Deploy on Ubuntu VPS

```bash
sudo apt update
sudo apt install -y git python3.12 python3.12-venv
git clone https://github.com/aryasep-a/channel-manager-bot.git
cd channel-manager-bot
python3.12 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
python main.py
```

After the manual test succeeds, create a systemd unit:

```bash
sudo nano /etc/systemd/system/channel-manager-bot.service
```

Example (change `ubuntu` if your VPS user differs):

```ini
[Unit]
Description=Telegram Channel Manager Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/channel-manager-bot
EnvironmentFile=/home/ubuntu/channel-manager-bot/.env
ExecStart=/home/ubuntu/channel-manager-bot/.venv/bin/python /home/ubuntu/channel-manager-bot/main.py
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Enable and inspect:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now channel-manager-bot
sudo systemctl status channel-manager-bot
journalctl -u channel-manager-bot -f
```

Update after a GitHub push:

```bash
cd ~/channel-manager-bot
git pull
. .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart channel-manager-bot
```

## Data and operations

The bot creates these JSON files under `data/` on first startup:

- `admins.json`
- `channels.json`
- `drafts.json`
- `schedules.json`
- `templates.json`
- `history.json`
- `settings.json`
- `activity.json`

Back up `data/` regularly. Atomic file replacement prevents partially-written JSON documents, but it is not a substitute for backups. Storage locks are process-local: run one bot process per data directory.

## Scope notes

This initial release is a working foundation for channel registration, single-message publishing, draft references, one-time scheduling and basic administration. It does **not** yet implement album composition, a custom inline-keyboard builder, editing/deleting/forwarding existing channel posts, recurring schedules, auto-delete, draft/template restoration into the composer, or a full custom parse-mode editor. Drafts and templates retain source chat/message IDs, so their source messages must remain accessible to the bot. These items are intentionally documented as follow-on work rather than advertised as finished features.

A send can fail if the bot loses administrator rights, Telegram applies rate limits, or the channel restricts the content. Each target is handled independently and failures are reported in the result.
