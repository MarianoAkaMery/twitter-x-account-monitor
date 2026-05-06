import logging

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
        prefix = f"New post by @{username}"
        if post.created_at:
            prefix += f" at {post.created_at.isoformat()}"
        message = f"{prefix}\n{post_url(username, post.id)}\n\n{post.text}"
        self._send(message)

    def _send(self, message: str) -> None:
        self._logger.info("Notification payload:\n%s", message)
        if self._config.dry_run or not self._config.discord_webhook_url:
            if self._config.dry_run:
                self._logger.info("DRY_RUN=true, webhook delivery skipped.")
            elif not self._config.discord_webhook_url:
                self._logger.info("No DISCORD_WEBHOOK_URL configured, console notification only.")
            return

        self._logger.info("Sending Discord webhook notification.")
        response = requests.post(
            self._config.discord_webhook_url,
            json={"content": message},
            timeout=15,
        )
        response.raise_for_status()
        self._logger.info("Discord webhook delivered.")
