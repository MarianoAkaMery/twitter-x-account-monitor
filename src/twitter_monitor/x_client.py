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

    def get_user_id(self, username: str) -> str:
        response = self._client.users.get_by_username(username=username)
        if response.data is None:
            raise RuntimeError(f"User not found: @{username}")
        return str(_get(response.data, "id"))

    def get_recent_posts(self, user_id: str, since_id: str | None) -> list[Post]:
        pages = self._client.users.get_posts(
            id=user_id,
            max_results=self._config.max_results,
            since_id=since_id,
            exclude=self._get_excludes(),
            tweet_fields=["created_at"],
        )

        response = next(iter(pages), None)
        if response is None:
            return []

        posts = [
            Post(
                id=str(_get(tweet, "id")),
                text=str(_get(tweet, "text", "")),
                created_at=_get(tweet, "created_at", None),
            )
            for tweet in response.data or []
        ]
        posts.sort(key=lambda post: int(post.id))
        return posts

    def get_usage(self) -> dict[str, Any]:
        response = self._client.usage.get()
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
