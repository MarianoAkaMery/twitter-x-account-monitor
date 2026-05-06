# Usage and Cost Notes

X API Pay-per-use costs are controlled from the Developer Console. This project avoids hardcoding prices because endpoint pricing can change.

## Recommended Test Settings

```text
MAX_POLLS=1
MAX_RESULTS=5
SKIP_EXISTING_ON_START=true
DRY_RUN=true
```

## Developer Console Settings

- Disable auto-recharge while testing.
- Set a low spending limit.
- Watch usage analytics after each run.
- Increase `POLL_SECONDS` for long-running monitors.
- Remember that each monitored account can require one timeline request per poll cycle.

## Usage Command

Show a readable usage summary:

```powershell
.\.venv\Scripts\python.exe usage.py --days 30
```

Show the raw X API response:

```powershell
.\.venv\Scripts\python.exe usage.py --json
```

## Future Cost Chart

The project has a `twitter-monitor-usage` command that prints usage data from X. A future chart can save daily snapshots and render:

- posts consumed by day
- users consumed by day
- estimated cost by day
- total spend for the selected window

The first implementation should store raw API responses before trying to infer cost from incomplete dashboard data.
