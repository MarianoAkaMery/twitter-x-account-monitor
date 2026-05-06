import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AccountState:
    last_seen_id: str | None = None
    user_id: str | None = None
    username: str | None = None


@dataclass
class MonitorState:
    accounts: dict[str, AccountState]


def load_state(path: Path) -> MonitorState:
    if not path.exists():
        return MonitorState(accounts={})

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))

    if "accounts" in data and isinstance(data["accounts"], dict):
        return MonitorState(
            accounts={
                username: AccountState(
                    last_seen_id=account.get("last_seen_id"),
                    user_id=account.get("user_id"),
                    username=account.get("username") or username,
                )
                for username, account in data["accounts"].items()
                if isinstance(account, dict)
            }
        )

    # Backward compatibility for the original single-account state file.
    username = data.get("username")
    if username:
        return MonitorState(
            accounts={
                username: AccountState(
                    last_seen_id=data.get("last_seen_id"),
                    user_id=data.get("user_id"),
                    username=username,
                )
            }
        )

    return MonitorState(accounts={})


def save_state(path: Path, state: MonitorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "accounts": {
            username: {
                "last_seen_id": account.last_seen_id,
                "user_id": account.user_id,
                "username": account.username,
            }
            for username, account in sorted(state.accounts.items())
        }
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
