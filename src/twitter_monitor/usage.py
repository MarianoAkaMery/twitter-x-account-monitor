import argparse
import json
from typing import Any

from .config import load_config
from .logging_setup import setup_logging
from .x_client import XClient


def main() -> None:
    args = _parse_args()
    config = load_config()
    setup_logging(config.log_level, config.log_file)
    usage = XClient(config).get_usage(days=args.days)

    if args.json:
        print(json.dumps(usage, indent=2, sort_keys=True))
        return

    print(format_usage_report(usage, days=args.days))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show X API Post usage for the configured app.")
    parser.add_argument("--days", type=int, default=7, help="Number of days to request from X API, from 1 to 90.")
    parser.add_argument("--json", action="store_true", help="Print the raw X API usage response.")
    args = parser.parse_args()
    args.days = max(1, min(90, args.days))
    return args


def format_usage_report(payload: dict[str, Any], *, days: int) -> str:
    data = payload.get("data", payload)
    project_usage = _as_int(data.get("project_usage"))
    project_cap = _as_int(data.get("project_cap"))
    cap_reset_day = data.get("cap_reset_day")

    lines = [
        "X API Usage",
        "===========",
        f"Window requested: last {days} day(s)",
    ]

    if project_usage is not None:
        lines.append(f"Project Post usage: {project_usage}")
    if project_cap is not None:
        lines.append(f"Project monthly cap: {project_cap}")
    if project_usage is not None and project_cap:
        percentage = (project_usage / project_cap) * 100
        lines.append(f"Cap used: {percentage:.2f}%")
    if cap_reset_day is not None:
        lines.append(f"Cap reset day: {cap_reset_day}")

    project_daily = _project_daily_usage(data)
    if project_daily:
        lines.extend(["", "Daily project usage:"])
        for date, usage in project_daily:
            lines.append(f"- {date}: {usage} post(s)")

    app_daily = _app_daily_usage(data)
    if app_daily:
        lines.extend(["", "Daily app usage:"])
        for app_id, rows in app_daily.items():
            lines.append(f"- App {app_id}:")
            for date, usage in rows:
                lines.append(f"  - {date}: {usage} post(s)")

    if not project_daily and not app_daily and project_usage is None:
        lines.extend(
            [
                "",
                "No usage rows found in the response.",
                "Run with --json to inspect the raw X API payload.",
            ]
        )

    lines.extend(
        [
            "",
            "Notes:",
            "- X bills successful responses that return billable resources.",
            "- Re-fetching the same Post within the UTC deduplication window should count once.",
            "- Check the X Developer Console for actual prices, credits, and spending limits.",
        ]
    )
    return "\n".join(lines)


def _project_daily_usage(data: dict[str, Any]) -> list[tuple[str, int]]:
    daily_project_usage = data.get("daily_project_usage")

    if isinstance(daily_project_usage, dict):
        return _usage_rows(daily_project_usage.get("usage", []))

    if isinstance(daily_project_usage, list):
        rows: list[tuple[str, int]] = []
        for item in daily_project_usage:
            if not isinstance(item, dict):
                continue
            date = str(item.get("date", "unknown"))
            for usage in item.get("usage", []):
                if isinstance(usage, dict):
                    rows.append((date, _as_int(usage.get("tweets_consumed")) or _as_int(usage.get("usage")) or 0))
        return rows

    return []


def _app_daily_usage(data: dict[str, Any]) -> dict[str, list[tuple[str, int]]]:
    daily_client_app_usage = data.get("daily_client_app_usage")
    if not isinstance(daily_client_app_usage, list):
        return {}

    result: dict[str, list[tuple[str, int]]] = {}
    for app in daily_client_app_usage:
        if not isinstance(app, dict):
            continue
        app_id = str(app.get("client_app_id") or app.get("app_id") or "unknown")
        result[app_id] = _usage_rows(app.get("usage", []))
    return result


def _usage_rows(rows: Any) -> list[tuple[str, int]]:
    if not isinstance(rows, list):
        return []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date = str(row.get("date", "unknown"))
        usage = _as_int(row.get("usage")) or _as_int(row.get("tweets_consumed")) or 0
        result.append((date, usage))
    return result


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
