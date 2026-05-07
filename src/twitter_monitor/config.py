import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bearer_token: str
    usernames: tuple[str, ...]
    poll_seconds: int
    state_file: Path
    max_results: int
    max_polls: int
    skip_existing_on_start: bool
    discord_webhook_url: str | None
    exclude_replies: bool
    include_reposts: bool
    dry_run: bool
    log_level: str
    log_file: Path | None
    discord_use_embed: bool
    discord_color: int
    discord_footer_text: str
    discord_footer_icon_url: str | None
    discord_author_name: str
    discord_author_icon_url: str | None
    discord_username: str | None
    discord_avatar_url: str | None


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
    usernames = _load_usernames()
    if not bearer_token:
        raise RuntimeError("Missing X_BEARER_TOKEN in environment or .env")
    if not usernames:
        raise RuntimeError("Missing X_USERNAMES or X_USERNAME in environment or .env")

    return Config(
        bearer_token=bearer_token,
        usernames=usernames,
        poll_seconds=env_int("POLL_SECONDS", 300, minimum=15),
        state_file=Path(os.getenv("STATE_FILE", ".twitter-monitor-state.json")),
        max_results=env_int("MAX_RESULTS", 5, minimum=5, maximum=100),
        max_polls=env_int("MAX_POLLS", 0, minimum=0),
        skip_existing_on_start=env_bool("SKIP_EXISTING_ON_START", True),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
        exclude_replies=env_bool("EXCLUDE_REPLIES", True),
        include_reposts=_include_reposts(),
        dry_run=env_bool("DRY_RUN", False),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        log_file=_optional_path("LOG_FILE"),
        discord_use_embed=env_bool("DISCORD_USE_EMBED", True),
        discord_color=_env_color("DISCORD_EMBED_COLOR", 0xF1D400),
        discord_footer_text=os.getenv("DISCORD_FOOTER_TEXT", "X").strip() or "X",
        discord_footer_icon_url=_optional_str("DISCORD_FOOTER_ICON_URL"),
        discord_author_name=os.getenv("DISCORD_AUTHOR_NAME", "Twitter/X Monitor").strip() or "Twitter/X Monitor",
        discord_author_icon_url=_optional_str("DISCORD_AUTHOR_ICON_URL"),
        discord_username=_optional_str("DISCORD_USERNAME"),
        discord_avatar_url=_optional_str("DISCORD_AVATAR_URL"),
    )


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name, "").strip()
    return Path(value) if value else None


def _optional_str(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _env_color(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    value = raw.removeprefix("#")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a hex color like #f1d400") from exc


def _include_reposts() -> bool:
    if os.getenv("INCLUDE_REPOSTS") is not None:
        return env_bool("INCLUDE_REPOSTS", True)
    return not env_bool("EXCLUDE_REPOSTS", False)


def _load_usernames() -> tuple[str, ...]:
    raw = os.getenv("X_USERNAMES", "").strip() or os.getenv("X_USERNAME", "").strip()
    usernames = []
    for item in raw.split(","):
        username = item.strip().lstrip("@")
        if username and username not in usernames:
            usernames.append(username)
    return tuple(usernames)
