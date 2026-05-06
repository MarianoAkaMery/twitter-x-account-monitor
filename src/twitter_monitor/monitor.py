import logging
import time

import requests

from .config import Config
from .notifiers import Notifier, post_url
from .state import AccountState, MonitorState, load_state, save_state
from .x_client import XClient


class Monitor:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._x = XClient(config)
        self._notifier = Notifier(config)
        self._logger = logging.getLogger(__name__)

    def run(self) -> None:
        self._log_startup()
        state = load_state(self._config.state_file)

        for username in self._config.usernames:
            self._ensure_account_state(state, username)
        save_state(self._config.state_file, state)
        self._logger.info("State file ready for %s account(s).", len(self._config.usernames))

        self._notifier.info(
            f"Monitoring {len(self._config.usernames)} account(s): {self._format_accounts()}."
        )

        poll_count = 0
        while True:
            self._logger.info("Starting poll #%s.", poll_count + 1)
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

            self._logger.info("Sleeping for %s second(s).", self._config.poll_seconds)
            time.sleep(self._config.poll_seconds)

    def _poll_once(self, state: MonitorState) -> int:
        total_posts = 0
        for username in self._config.usernames:
            account = state.accounts[username]
            total_posts += self._poll_account(state, account)
        return total_posts

    def _poll_account(self, state: MonitorState, account: AccountState) -> int:
        if not account.user_id or not account.username:
            raise RuntimeError("Missing account state")

        self._logger.info("Polling @%s.", account.username)
        posts = self._x.get_recent_posts(account.user_id, account.last_seen_id)

        if not account.last_seen_id and self._config.skip_existing_on_start:
            if posts:
                account.last_seen_id = posts[-1].id
                save_state(self._config.state_file, state)
                self._notifier.info(
                    "Initialized state at latest visible post: "
                    f"{post_url(account.username, account.last_seen_id)}"
                )
            else:
                self._notifier.info(f"Initialized state for @{account.username}: no visible posts returned.")
            return 0

        for post in posts:
            self._logger.info("New post detected for @%s: id=%s.", account.username, post.id)
            self._notifier.post(account.username, post)
            account.last_seen_id = post.id

        if posts and account.last_seen_id:
            save_state(self._config.state_file, state)
            self._logger.info("Saved state for @%s with last_seen_id=%s.", account.username, account.last_seen_id)
        elif account.last_seen_id:
            self._logger.info("State unchanged for @%s: last_seen_id=%s.", account.username, account.last_seen_id)

        return len(posts)

    def _log_startup(self) -> None:
        self._logger.info("Twitter/X monitor starting.")
        self._logger.info("Watching accounts: %s", self._format_accounts())
        self._logger.info("State file: %s", self._config.state_file)
        self._logger.info(
            "Runtime controls: poll_seconds=%s max_results=%s max_polls=%s skip_existing_on_start=%s",
            self._config.poll_seconds,
            self._config.max_results,
            self._config.max_polls or "forever",
            self._config.skip_existing_on_start,
        )
        if self._config.max_polls:
            self._logger.info("Run mode: one-shot/test mode, stopping after %s poll(s).", self._config.max_polls)
        else:
            self._logger.info("Run mode: continuous monitoring until interrupted.")
        self._logger.info(
            "Cost guardrails: requesting up to %s post(s) per account every %s second(s).",
            self._config.max_results,
            self._config.poll_seconds,
        )
        self._logger.info(
            "Worst-case request volume: %s timeline request(s) per poll cycle.",
            len(self._config.usernames),
        )
        self._logger.info(
            "Filters: exclude_replies=%s exclude_reposts=%s",
            self._config.exclude_replies,
            self._config.exclude_reposts,
        )
        self._logger.info(
            "Notifications: discord=%s dry_run=%s",
            "enabled" if self._config.discord_webhook_url else "disabled",
            self._config.dry_run,
        )

    def _ensure_account_state(self, state: MonitorState, username: str) -> None:
        account = state.accounts.get(username)
        if account is None:
            account = AccountState(username=username)
            state.accounts[username] = account

        if not account.user_id or account.username != username:
            self._logger.info("No cached user_id for @%s. A user lookup is required.", username)
            account.user_id = self._x.get_user_id(username)
            account.username = username
            save_state(self._config.state_file, state)
            self._logger.info("State cache updated at %s.", self._config.state_file)
        else:
            self._logger.info("Using cached user_id=%s for @%s.", account.user_id, username)

    def _format_accounts(self) -> str:
        return ", ".join(f"@{username}" for username in self._config.usernames)
