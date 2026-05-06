# Twitter/X Monitor

A small Python monitor that watches one X/Twitter account and notifies when new posts appear.

The project uses the official X API v2 through X's Python XDK, stores local state to avoid duplicate notifications, and defaults to conservative settings for Pay-per-use accounts.

## Features

- Monitor new posts from one configured account.
- Monitor one or more accounts with `X_USERNAMES`.
- Use a Project App Bearer Token from X API v2.
- Cache the target `user_id` to avoid repeated user lookup calls.
- Store the newest seen post ID locally.
- Skip historical posts on first run by default.
- Print notifications to the console.
- Optionally send notifications to a Discord webhook.
- Human-readable terminal logging with startup, polling, API, and notification status.
- Optional file logging.
- Run as a simple script or as an installed CLI.

## Requirements

- Python 3.11+
- An X Developer Project App with Pay-per-use access enabled
- X API credits available in the Developer Console
- A Bearer Token from the Project App, not a legacy standalone app

## Quick Start

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy the example config:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```text
X_BEARER_TOKEN=your_bearer_token_here
X_USERNAMES=xdevelopers,github
POLL_SECONDS=300
MAX_RESULTS=5
MAX_POLLS=1
SKIP_EXISTING_ON_START=true
DRY_RUN=true
LOG_LEVEL=INFO
```

Run a one-shot test:

```powershell
.\.venv\Scripts\python.exe monitor.py
```

If the test works, set:

```text
MAX_POLLS=0
DRY_RUN=false
```

Then run it continuously:

```powershell
.\.venv\Scripts\python.exe monitor.py
```

## CLI Install

For development, install the package in editable mode:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Then use:

```powershell
twitter-monitor
twitter-monitor-usage
```

Editable installs generate `*.egg-info` metadata. It is ignored by git and can be deleted locally.

## Configuration

All settings are loaded from `.env`.

| Variable | Default | Description |
| --- | --- | --- |
| `X_BEARER_TOKEN` | required | Bearer Token from an X API v2 Project App. |
| `X_USERNAMES` | required | Comma-separated accounts to monitor, without `@`. |
| `X_USERNAME` | empty | Backward-compatible single-account fallback if `X_USERNAMES` is empty. |
| `POLL_SECONDS` | `300` | Seconds between polls. Higher values reduce API usage. |
| `STATE_FILE` | `.twitter-monitor-state.json` | Local state file for `user_id` and latest seen post. |
| `MAX_RESULTS` | `5` | Posts requested per poll. X supports 5-100 for user timelines. |
| `MAX_POLLS` | `0` | `0` runs forever. Use `1` for a one-shot test. |
| `SKIP_EXISTING_ON_START` | `true` | Initialize state without notifying old posts. |
| `DISCORD_WEBHOOK_URL` | empty | Optional Discord webhook destination. |
| `EXCLUDE_REPLIES` | `true` | Exclude replies from monitoring. |
| `EXCLUDE_REPOSTS` | `true` | Exclude reposts/retweets from monitoring. |
| `DRY_RUN` | `false` | Print notifications without sending webhooks. |
| `LOG_LEVEL` | `INFO` | Terminal logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `LOG_FILE` | empty | Optional path for writing logs to a file. |

## Cost Controls

X API Pay-per-use charges depend on the endpoint and resources returned. Check current pricing in the X Developer Console.

Recommended development settings:

```text
MAX_POLLS=1
MAX_RESULTS=5
SKIP_EXISTING_ON_START=true
DRY_RUN=true
```

Also configure these in the Developer Console:

- Disable auto-recharge while testing.
- Set a low spending limit.
- Monitor usage after each test run.

The monitor intentionally caches `user_id` in the state file. This avoids doing a user lookup on every start.

For multiple accounts, each poll cycle makes up to one timeline request per account. For example, `X_USERNAMES=a,b,c` and `POLL_SECONDS=300` means up to 3 timeline requests every 5 minutes.

## Terminal Output

The monitor logs concrete runtime events:

```text
2026-05-06 21:45:00 | INFO     | Twitter/X monitor starting.
2026-05-06 21:45:00 | INFO     | Watching accounts: @xdevelopers, @github
2026-05-06 21:45:00 | INFO     | Runtime controls: poll_seconds=300 max_results=5 max_polls=1 skip_existing_on_start=True
2026-05-06 21:45:00 | INFO     | Run mode: one-shot/test mode, stopping after 1 poll(s).
2026-05-06 21:45:00 | INFO     | Cost guardrails: requesting up to 5 post(s) per account every 300 second(s).
2026-05-06 21:45:00 | INFO     | Worst-case request volume: 2 timeline request(s) per poll cycle.
2026-05-06 21:45:01 | INFO     | Starting poll #1.
2026-05-06 21:45:01 | INFO     | Requesting posts: user_id=... since_id=... max_results=5 exclude=['replies', 'retweets'].
2026-05-06 21:45:02 | INFO     | No new posts.
2026-05-06 21:45:02 | INFO     | Reached MAX_POLLS=1. Stopping.
```

To save logs to a file:

```text
LOG_FILE=twitter-monitor.log
```

## Continuous Monitoring

Use this in `.env`:

```text
MAX_POLLS=0
POLL_SECONDS=300
```

Then run:

```powershell
.\.venv\Scripts\python.exe monitor.py
```

Stop it with `Ctrl+C`.

## Multiple Accounts

Use comma-separated usernames:

```text
X_USERNAMES=xdevelopers,github,openai
```

The state file stores each account separately:

```json
{
  "accounts": {
    "xdevelopers": {
      "last_seen_id": "...",
      "user_id": "...",
      "username": "xdevelopers"
    }
  }
}
```

Adding a new account triggers one user lookup for that account, then the `user_id` is cached.

## Usage Analytics

Print raw X API usage data:

```powershell
.\.venv\Scripts\python.exe usage.py
```

or:

```powershell
twitter-monitor-usage
```

A cost chart is planned, but the first version keeps usage output raw so the project can map the real API response format before drawing graphs.

## Project Layout

```text
src/twitter_monitor/
  cli.py          CLI entrypoint
  config.py       Environment config
  monitor.py      Polling loop
  notifiers.py    Console and Discord notifications
  logging_setup.py Terminal/file logging
  state.py        Local state file handling
  usage.py        Usage endpoint command
  x_client.py     XDK wrapper
```

Compatibility wrappers:

```text
monitor.py
usage.py
```

## Security

Never commit `.env`, `.twitter-monitor-state.json`, logs, or generated package metadata. The included `.gitignore` excludes these files.

If a Bearer Token or Discord webhook is accidentally shared, rotate it immediately in the relevant dashboard.

## Roadmap

- Multi-account monitoring.
- Better structured logging.
- Usage history snapshots.
- Cost/usage chart from saved usage snapshots.
- Additional notification providers.
- Tests for config, state, and notification formatting.
