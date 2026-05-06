import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MonitorState:
    last_seen_id: str | None = None
    user_id: str | None = None
    username: str | None = None


def load_state(path: Path) -> MonitorState:
    if not path.exists():
        return MonitorState()

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return MonitorState(
        last_seen_id=data.get("last_seen_id"),
        user_id=data.get("user_id"),
        username=data.get("username"),
    )


def save_state(path: Path, state: MonitorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_seen_id": state.last_seen_id,
        "user_id": state.user_id,
        "username": state.username,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
