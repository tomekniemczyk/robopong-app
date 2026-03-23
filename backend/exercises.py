"""Physical exercises — file-based, no robot communication."""

import json
from pathlib import Path

DEFAULTS_FILE = Path(__file__).parent / "exercises_default.json"
USER_FILE     = Path(__file__).parent / ".exercises_user.json"


def _load_defaults() -> dict:
    return json.loads(DEFAULTS_FILE.read_text()) if DEFAULTS_FILE.exists() else {"categories": []}


def _load_user() -> dict:
    try:
        return json.loads(USER_FILE.read_text())
    except Exception:
        return {}


def _save_user(data: dict):
    USER_FILE.write_text(json.dumps(data, indent=2))


def _assign_ids(data: dict) -> dict:
    for ci, cat in enumerate(data.get("categories", [])):
        cat["id"] = (ci + 1) * 100
        for ei, ex in enumerate(cat.get("exercises", [])):
            ex["id"] = cat["id"] + ei + 1
            ex["category"] = cat["name"]
            ex["category_icon"] = cat.get("icon", "")
    return data


def get_exercises() -> dict:
    data = _load_defaults()
    user = _load_user()
    overrides = user.get("overrides", {})
    for cat in data.get("categories", []):
        for ex in cat.get("exercises", []):
            key = f"{cat['name']}/{ex['name']}"
            if key in overrides:
                ex["duration_sec"] = overrides[key].get("duration_sec", ex["duration_sec"])
                ex["modified"] = True
            else:
                ex["modified"] = False
    custom = user.get("custom_exercises", [])
    if custom:
        data.setdefault("categories", []).append({
            "name": "Custom", "icon": "✏", "exercises": custom
        })
    return _assign_ids(data)


def get_exercise(exercise_id: int) -> dict | None:
    data = get_exercises()
    for cat in data.get("categories", []):
        for ex in cat.get("exercises", []):
            if ex.get("id") == exercise_id:
                return ex
    return None


def save_override(exercise_id: int, duration_sec: int):
    data = get_exercises()
    for cat in data.get("categories", []):
        for ex in cat.get("exercises", []):
            if ex.get("id") == exercise_id:
                key = f"{cat['name']}/{ex['name']}"
                user = _load_user()
                overrides = user.setdefault("overrides", {})
                overrides[key] = {"duration_sec": duration_sec}
                _save_user(user)
                return


def reset_all():
    user = _load_user()
    user["overrides"] = {}
    _save_user(user)
