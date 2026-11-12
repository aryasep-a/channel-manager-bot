# Channel Manager Bot

Telegram Channel Manager built for **Python 3.10**, Kurigram, APScheduler 3.x and JSON storage.

## Features

- Owner and multi-admin access control
- Register, list and remove managed channels
- Bot administrator permission check
- Quick publish to one or multiple channels
- One-time scheduled posts, restored after restart
- Draft and template references
- Posting history and basic statistics
- JSON storage with atomic writes
- Telegram menu interface
- Bash operations for tmux: start, stop, restart, status and safe update

## Requirements

- Ubuntu/Linux
- Python 3.10
- Git and tmux
- Telegram bot token from @BotFather
- API ID and API hash from https://my.telegram.org

## Install

```bash
git clone https://github.com/aryasep-a/channel-manager-bot.git
cd channel-manager-bot
python3.10 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Set `BOT_TOKEN`, `API_ID`, `API_HASH` and `OWNER_ID` in `.env`. Never commit this file.

## Run with tmux

Start the bot:

```bash
bash start
```

Other commands:

```bash
bash status
bash stop
bash restart
bash update
```

The scripts use the local `.venv/bin/python` and a tmux session named `channel-manager`. Logs are available through:

```bash
tmux attach -t channel-manager
```

Detach without stopping the bot using `Ctrl+B`, then `D`.

### Safe update

`bash update` checks for uncommitted changes, creates a timestamped backup of `data/`, fetches and fast-forward pulls the current branch, installs requirements and compiles the project. If validation fails, it attempts to restore the previous Git commit and restart the previous version. It never overwrites `.env` or the data directory.

## First setup in Telegram

1. Open the bot using the Telegram account whose ID is configured as `OWNER_ID`.
2. Add the bot to your channel as administrator and enable **Post Messages**.
3. Send `/addchannel @channelusername` to the bot.
4. Open **Channels** and verify the channel is listed.
5. Choose **Quick Post**, send one message, select destinations and publish.

## Commands

| Command | Description |
|---|---|
| `/start`, `/help` | Dashboard and help |
| `/channels` | List channels |
| `/addchannel @username` | Add channel |
| `/delchannel CHANNEL_ID` | Remove channel |
| `/setdefault CHANNEL_ID` | Set default channel |
| `/post` | Quick publish |
| `/schedule YYYY-MM-DD HH:MM` | Schedule a post |
| `/schedules` | List schedules |
| `/cancel_schedule ID` | Cancel a pending schedule |
| `/drafts`, `/templates` | List saved references |
| `/history`, `/stats` | History and statistics |
| `/addadmin USER_ID`, `/deladmin USER_ID` | Manage admins (owner only) |
| `/setowner USER_ID` | Transfer owner (current owner only) |
| `/settimezone Asia/Jakarta` | Set timezone |
| `/setparsemode html` | Save parse-mode preference |
| `/settings` | Show configuration |
| `/cancel` | Cancel active composition |

## Data

Persistent JSON files are stored in `data/`. Back up this directory regularly. Run only one bot process against a data directory because JSON locks are process-local.

## Current limitations

This release supports single-message publishing. Album composition, recurring schedules, auto-delete, a visual inline-keyboard builder, editing/deleting old channel posts, and full draft restoration are not implemented yet. Drafts and templates store references to source messages, not copies of message content.
