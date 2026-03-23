"""File-based drill storage. No database.

drills_default.json — factory drills (read-only, source of truth for reset)
.drills_user.json   — user overrides (modified params, user_count, custom drills)
"""

import json
from pathlib import Path

DEFAULTS_FILE = Path(__file__).parent / "drills_default.json"
USER_FILE     = Path(__file__).parent / ".drills_user.json"


def _load_defaults() -> dict:
    return json.loads(DEFAULTS_FILE.read_text()) if DEFAULTS_FILE.exists() else {"folders": []}


def _load_user() -> dict:
    try:
        return json.loads(USER_FILE.read_text())
    except Exception:
        return {}


def _save_user(data: dict):
    USER_FILE.write_text(json.dumps(data, indent=2))


def _drill_key(folder_name: str, drill_name: str) -> str:
    return f"{folder_name}/{drill_name}"


def _assign_ids(tree: dict) -> dict:
    """Assign stable IDs: folder_idx*1000 + drill_idx. Custom drills keep their stored IDs."""
    for fi, folder in enumerate(tree.get("folders", [])):
        folder["id"] = (fi + 1) * 1000
        for di, drill in enumerate(folder.get("drills", [])):
            if not drill.get("id"):  # factory drills have no pre-assigned ID
                drill["id"] = folder["id"] + di + 1
            drill["folder_id"] = folder["id"]
    return tree


def get_tree() -> dict:
    """Load defaults, apply user overrides, return full tree."""
    tree = _load_defaults()
    user = _load_user()
    overrides = user.get("overrides", {})

    for folder in tree.get("folders", []):
        for drill in folder.get("drills", []):
            key = _drill_key(folder["name"], drill["name"])
            if key in overrides:
                ov = overrides[key]
                if "balls" in ov:
                    drill["balls"] = ov["balls"]
                if "repeat" in ov:
                    drill["repeat"] = ov["repeat"]
                if "delay_s" in ov:
                    drill["delay_s"] = ov["delay_s"]
                drill["user_count"] = ov.get("user_count")
                drill["modified"] = True
            else:
                drill["user_count"] = None
                drill["modified"] = False

    # custom drills (user-created)
    custom = user.get("custom_drills", [])
    if custom:
        tree.setdefault("folders", []).append({
            "name": "Custom",
            "description": "Drille użytkownika",
            "sort_order": 99,
            "readonly": False,
            "drills": custom,
        })

    return _assign_ids(tree)


def get_drill(drill_id: int) -> dict | None:
    tree = get_tree()
    for folder in tree.get("folders", []):
        for drill in folder.get("drills", []):
            if drill.get("id") == drill_id:
                drill["_folder"] = folder["name"]
                return drill
    return None


def save_override(drill_id: int, data: dict):
    """Save user override for a factory drill."""
    tree = get_tree()
    for folder in tree.get("folders", []):
        for drill in folder.get("drills", []):
            if drill.get("id") == drill_id:
                key = _drill_key(folder["name"], drill["name"])
                user = _load_user()
                overrides = user.setdefault("overrides", {})
                overrides[key] = {
                    "balls": data.get("balls", drill["balls"]),
                    "repeat": data.get("repeat", drill.get("repeat", 0)),
                    "delay_s": data.get("delay_s", drill.get("delay_s", 0)),
                    "user_count": data.get("user_count"),
                }
                _save_user(user)
                return True
    return False


def set_user_count(drill_id: int, count: int | None):
    """Set user count override for a drill."""
    drill = get_drill(drill_id)
    if not drill:
        return
    key = _drill_key(drill["_folder"], drill["name"])
    user = _load_user()
    overrides = user.setdefault("overrides", {})
    ov = overrides.setdefault(key, {})
    ov["user_count"] = count
    _save_user(user)


def reset_drill(drill_id: int) -> bool:
    """Remove user override, revert to factory."""
    tree_defaults = _load_defaults()
    tree = get_tree()
    for folder in tree.get("folders", []):
        for drill in folder.get("drills", []):
            if drill.get("id") == drill_id:
                key = _drill_key(folder["name"], drill["name"])
                user = _load_user()
                overrides = user.get("overrides", {})
                if key in overrides:
                    del overrides[key]
                    _save_user(user)
                return True
    return False


def reset_all():
    """Delete all user overrides (keep custom drills)."""
    user = _load_user()
    user["overrides"] = {}
    _save_user(user)


def update_custom_drill(drill_id: int, data: dict) -> bool:
    user = _load_user()
    custom = user.get("custom_drills", [])
    for drill in custom:
        if drill.get("id") == drill_id:
            for k, v in data.items():
                if k != "id":
                    drill[k] = v
            _save_user(user)
            return True
    return False


def create_custom_drill(data: dict):
    """Add a user-created drill."""
    user = _load_user()
    custom = user.setdefault("custom_drills", [])
    data["id"] = max((d.get("id", 0) for d in custom), default=99000) + 1
    data["readonly"] = False
    data["modified"] = False
    custom.append(data)
    _save_user(user)
    return data["id"]


def delete_custom_drill(drill_id: int):
    user = _load_user()
    custom = user.get("custom_drills", [])
    user["custom_drills"] = [d for d in custom if d.get("id") != drill_id]
    _save_user(user)
