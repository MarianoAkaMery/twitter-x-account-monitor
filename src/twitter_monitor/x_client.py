import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from xdk import Client

from .config import Config


_TCO_URL_RE = re.compile(r"\s+https://t\.co/[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Post:
    id: str
    text: str
    created_at: datetime | None
    kind: str = "post"
    media_urls: tuple[str, ...] = ()


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
            tweet_fields=["attachments", "created_at", "entities", "referenced_tweets"],
            expansions=[
                "attachments.media_keys",
                "referenced_tweets.id",
                "referenced_tweets.id.attachments.media_keys",
            ],
            media_fields=["preview_image_url", "type", "url"],
        )

        response = next(iter(pages), None)
        if response is None:
            self._logger.info("X API returned no page for this poll.")
            return []

        media_by_key = _media_by_key(_get(response, "includes", None))
        tweets_by_id = _tweets_by_id(_get(response, "includes", None))
        posts = []
        for tweet in response.data or []:
            media_urls = _post_media_urls(tweet, media_by_key, tweets_by_id)
            posts.append(
                Post(
                    id=str(_get(tweet, "id")),
                    text=_strip_trailing_media_link(str(_get(tweet, "text", "")), media_urls),
                    created_at=_parse_datetime(_get(tweet, "created_at", None)),
                    kind=_post_kind(tweet),
                    media_urls=media_urls,
                )
            )
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
        if not self._config.include_reposts:
            excludes.append("retweets")
        return excludes or None


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _media_by_key(includes: Any) -> dict[str, Any]:
    media_items = _get(includes, "media", []) or []
    return {str(_get(media, "media_key")): media for media in media_items if _get(media, "media_key")}


def _tweets_by_id(includes: Any) -> dict[str, Any]:
    tweets = _get(includes, "tweets", []) or []
    return {str(_get(tweet, "id")): tweet for tweet in tweets if _get(tweet, "id")}


def _post_media_urls(tweet: Any, media_by_key: dict[str, Any], tweets_by_id: dict[str, Any]) -> tuple[str, ...]:
    urls = list(_tweet_media_urls(tweet, media_by_key))
    for referenced_tweet in _referenced_tweets(tweet, tweets_by_id):
        urls.extend(_tweet_media_urls(referenced_tweet, media_by_key))
    return tuple(dict.fromkeys(urls))


def _tweet_media_urls(tweet: Any, media_by_key: dict[str, Any]) -> tuple[str, ...]:
    attachments = _get(tweet, "attachments", {}) or {}
    media_keys = _get(attachments, "media_keys", []) or []
    urls: list[str] = []
    for media_key in media_keys:
        media = media_by_key.get(str(media_key))
        if media is None:
            continue
        url = _get(media, "url") or _get(media, "preview_image_url")
        if url:
            urls.append(str(url))
    return tuple(dict.fromkeys(urls))


def _referenced_tweets(tweet: Any, tweets_by_id: dict[str, Any]) -> tuple[Any, ...]:
    references = _get(tweet, "referenced_tweets", []) or []
    tweets = []
    for reference in references:
        referenced_tweet = tweets_by_id.get(str(_get(reference, "id")))
        if referenced_tweet is not None:
            tweets.append(referenced_tweet)
    return tuple(tweets)


def _post_kind(tweet: Any) -> str:
    reference_types = {
        str(_get(reference, "type", "")).lower()
        for reference in (_get(tweet, "referenced_tweets", []) or [])
    }
    if "retweeted" in reference_types:
        return "repost"
    if "quoted" in reference_types:
        return "quote"
    return "post"


def _strip_trailing_media_link(text: str, media_urls: tuple[str, ...]) -> str:
    if not media_urls:
        return text

    return _TCO_URL_RE.sub("", text.rstrip()).rstrip()


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
