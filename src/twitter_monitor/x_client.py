import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from xdk import Client

from .config import Config


@dataclass(frozen=True)
class Post:
    id: str
    text: str
    created_at: datetime | None


class XClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = Client(bearer_token=config.bearer_token)
        self._logger = logging.getLogger(__name__)

    def get_user_id(self, username: str) -> str:
        self._logger.info("Resolving X user id for @%s.", username)
        response = self._client.users.get_by_username(username=username)
        if response.data is None:
            raise RuntimeError(f"User not found: @{username}")
        user_id = str(_get(response.data, "id"))
        self._logger.info("Resolved @%s to user_id=%s.", username, user_id)
        return user_id

    def get_recent_posts(self, user_id: str, since_id: str | None) -> list[Post]:
        self._logger.info(
            "Requesting posts: user_id=%s since_id=%s max_results=%s exclude=%s.",
            user_id,
            since_id or "none",
            self._config.max_results,
            self._get_excludes() or "none",
        )

        # XDK auto-paginates. The monitor intentionally consumes only the first page
        # per poll so MAX_RESULTS remains the cost/volume guardrail users expect.
        pages = self._client.users.get_posts(
            id=user_id,
            max_results=self._config.max_results,
            since_id=since_id,
            exclude=self._get_excludes(),
            tweet_fields=["created_at"],
        )

        response = next(iter(pages), None)
        if response is None:
            self._logger.info("X API returned no page for this poll.")
            return []

        posts = [
            Post(
                id=str(_get(tweet, "id")),
                text=str(_get(tweet, "text", "")),
                created_at=_parse_datetime(_get(tweet, "created_at", None)),
            )
            for tweet in response.data or []
        ]
        posts.sort(key=lambda post: int(post.id))
        self._logger.info("X API returned %s post(s) for this poll.", len(posts))
        return posts

    def get_usage(self, days: int | None = None) -> dict[str, Any]:
        self._logger.info("Requesting raw X API usage data.")
        response = self._client.usage.get(days=days)
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        if isinstance(response, dict):
            return response
        return {"raw": str(response)}

    def _get_excludes(self) -> list[str] | None:
        excludes: list[str] = []
        if self._config.exclude_replies:
            excludes.append("replies")
        if self._config.exclude_reposts:
            excludes.append("retweets")
        return excludes or None


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None
