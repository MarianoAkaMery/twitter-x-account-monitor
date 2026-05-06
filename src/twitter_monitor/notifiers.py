import requests

from .config import Config
from .x_client import Post


def post_url(username: str, post_id: str) -> str:
    return f"https://x.com/{username}/status/{post_id}"


class Notifier:
    def __init__(self, config: Config) -> None:
        self._config = config

    def info(self, message: str) -> None:
        print(message, flush=True)

    def post(self, username: str, post: Post) -> None:
        prefix = f"New post by @{username}"
        if post.created_at:
            prefix += f" at {post.created_at.isoformat()}"
        message = f"{prefix}\n{post_url(username, post.id)}\n\n{post.text}"
        self._send(message)

    def _send(self, message: str) -> None:
        print(message, flush=True)
        if self._config.dry_run or not self._config.discord_webhook_url:
            return

        response = requests.post(
            self._config.discord_webhook_url,
            json={"content": message},
            timeout=15,
        )
        response.raise_for_status()
