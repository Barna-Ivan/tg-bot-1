import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telegram import User

BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"


def _load_users() -> dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open(encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict[str, Any]) -> None:
    with USERS_FILE.open("w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


def get_display_name(user: User) -> str:
    if user.username:
        return f"@{user.username}"
    parts = [user.first_name, user.last_name]
    name = " ".join(part for part in parts if part)
    return name or "Unknown"


def record_user(user: User) -> None:
    if user.is_bot:
        return

    users = _load_users()
    user_id = str(user.id)
    users[user_id] = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "display_name": get_display_name(user),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }
    _save_users(users)
