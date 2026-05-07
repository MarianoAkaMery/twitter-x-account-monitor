import logging
from datetime import timezone
from typing import Any

import requests

from .config import Config
from .x_client import Post


def post_url(username: str, post_id: str) -> str:
    return f"https://x.com/{username}/status/{post_id}"


class Notifier:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def post(self, username: str, post: Post) -> None:
        prefix = f"{_notification_title(post)} by @{username}"
        if post.created_at:
            prefix += f" at {post.created_at.isoformat()}"
        message = f"{prefix}\n{post_url(username, post.id)}\n\n{_description(post)}"
        payload = self._build_discord_payload(username, post, fallback_message=message)
        self._send(payload, fallback_message=message)

    def _send(self, payload: dict[str, Any], *, fallback_message: str) -> None:
        self._logger.info("Notification payload:\n%s", fallback_message)
        if self._config.dry_run or not self._config.discord_webhook_url:
            if self._config.dry_run:
                self._logger.info("DRY_RUN=true, webhook delivery skipped.")
            elif not self._config.discord_webhook_url:
                self._logger.info("No DISCORD_WEBHOOK_URL configured, console notification only.")
            return

        self._logger.info("Sending Discord webhook notification.")
        response = requests.post(
            self._config.discord_webhook_url,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        self._logger.info("Discord webhook delivered.")

    def _build_discord_payload(self, username: str, post: Post, *, fallback_message: str) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self._config.discord_username:
            payload["username"] = self._config.discord_username
        if self._config.discord_avatar_url:
            payload["avatar_url"] = self._config.discord_avatar_url

        if not self._config.discord_use_embed:
            payload["content"] = fallback_message
            return payload

        embed: dict[str, Any] = {
            "title": f"{_notification_title(post)} by @{username}",
            "url": post_url(username, post.id),
            "description": _truncate(_description(post), 4096),
            "color": self._config.discord_color,
            "author": {"name": self._config.discord_author_name},
            "footer": {"text": self._footer_text(post)},
        }

        if self._config.discord_author_icon_url:
            embed["author"]["icon_url"] = self._config.discord_author_icon_url
        if self._config.discord_footer_icon_url:
            embed["footer"]["icon_url"] = self._config.discord_footer_icon_url
        if post.created_at:
            embed["timestamp"] = post.created_at.astimezone(timezone.utc).isoformat()
        if post.media_urls:
            embed["image"] = {"url": post.media_urls[0]}

        payload["embeds"] = [embed]
        return payload

    def _footer_text(self, post: Post) -> str:
        if not post.created_at:
            return self._config.discord_footer_text
        local_time = post.created_at.astimezone()
        return f"{self._config.discord_footer_text} • {local_time:%d/%m/%Y %H:%M}"


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 1] + "..."


def _notification_title(post: Post) -> str:
    if post.kind == "repost":
        return "New repost"
    if post.kind == "quote":
        return "New quote post"
    return "New post"


def _description(post: Post) -> str:
    if post.kind in {"repost", "quote"} and post.text:
        return f">>> {post.text}"
    return post.text
