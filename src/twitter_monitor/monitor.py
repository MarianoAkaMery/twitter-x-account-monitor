import time

import requests

from .config import Config
from .notifiers import Notifier, post_url
from .state import MonitorState, load_state, save_state
from .x_client import XClient


class Monitor:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._x = XClient(config)
        self._notifier = Notifier(config)

    def run(self) -> None:
        state = load_state(self._config.state_file)
        state.username = self._config.username

        if not state.user_id or state.username != self._config.username:
            state.user_id = self._x.get_user_id(self._config.username)
            save_state(self._config.state_file, state)

        self._notifier.info(
            f"Monitoring @{self._config.username}. Polling every {self._config.poll_seconds}s."
        )

        poll_count = 0
        while True:
            try:
                posts_seen = self._poll_once(state)
            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code == 402:
                    self._notifier.info(
                        "X API payment required: add credits or lower spending limits in the Developer Console."
                    )
                    break
                if status_code == 429:
                    self._notifier.info("X API rate limit hit. Stop the monitor and retry after the reset window.")
                    break
                self._notifier.info(f"X API error: {exc!r}")
            except Exception as exc:
                self._notifier.info(f"Monitor error: {exc!r}")
            else:
                if posts_seen == 0:
                    self._notifier.info("No new posts.")

            poll_count += 1
            if self._config.max_polls and poll_count >= self._config.max_polls:
                self._notifier.info(f"Reached MAX_POLLS={self._config.max_polls}. Stopping.")
                break

            time.sleep(self._config.poll_seconds)

    def _poll_once(self, state: MonitorState) -> int:
        if not state.user_id:
            raise RuntimeError("Missing user_id in state")

        posts = self._x.get_recent_posts(state.user_id, state.last_seen_id)

        if not state.last_seen_id and self._config.skip_existing_on_start:
            if posts:
                state.last_seen_id = posts[-1].id
                save_state(self._config.state_file, state)
                self._notifier.info(
                    "Initialized state at latest visible post: "
                    f"{post_url(self._config.username, state.last_seen_id)}"
                )
            else:
                self._notifier.info("Initialized state: no visible posts returned.")
            return 0

        for post in posts:
            self._notifier.post(self._config.username, post)
            state.last_seen_id = post.id

        if state.last_seen_id:
            save_state(self._config.state_file, state)

        return len(posts)
