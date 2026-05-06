import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bearer_token: str
    username: str
    poll_seconds: int
    state_file: Path
    max_results: int
    max_polls: int
    skip_existing_on_start: bool
    discord_webhook_url: str | None
    exclude_replies: bool
    exclude_reposts: bool
    dry_run: bool
    log_level: str
    log_file: Path | None


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    value = default if raw is None or raw.strip() == "" else int(raw)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def load_config() -> Config:
    load_dotenv()

    bearer_token = os.getenv("X_BEARER_TOKEN", "").strip()
    username = os.getenv("X_USERNAME", "").strip().lstrip("@")
    if not bearer_token:
        raise RuntimeError("Missing X_BEARER_TOKEN in environment or .env")
    if not username:
        raise RuntimeError("Missing X_USERNAME in environment or .env")

    return Config(
        bearer_token=bearer_token,
        username=username,
        poll_seconds=env_int("POLL_SECONDS", 300, minimum=15),
        state_file=Path(os.getenv("STATE_FILE", ".twitter-monitor-state.json")),
        max_results=env_int("MAX_RESULTS", 5, minimum=5, maximum=100),
        max_polls=env_int("MAX_POLLS", 0, minimum=0),
        skip_existing_on_start=env_bool("SKIP_EXISTING_ON_START", True),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
        exclude_replies=env_bool("EXCLUDE_REPLIES", True),
        exclude_reposts=env_bool("EXCLUDE_REPOSTS", True),
        dry_run=env_bool("DRY_RUN", False),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        log_file=_optional_path("LOG_FILE"),
    )


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value) if value else None
