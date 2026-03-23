"""File-based drill storage. No database.

drills_default.json — factory drills (read-only, source of truth for reset)
.drills_user.json   — user overrides (modified params, user_count, custom drills, user folders)
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
    """Assign stable IDs to factory folders. Custom folders (id>=90000) keep their IDs."""
    factory_count = 0
    for folder in tree.get("folders", []):
        if folder.get("id", 0) < 90000:
            factory_count += 1
            folder["id"] = factory_count * 1000
        for di, drill in enumerate(folder.get("drills", [])):
            if not drill.get("id"):
                drill["id"] = folder["id"] + di + 1
            drill["folder_id"] = folder["id"]
    return tree


def get_tree() -> dict:
    """Load defaults, apply user overrides, append user folders, return full tree."""
    tree = _load_defaults()
    user = _load_user()
    overrides = user.get("overrides", {})

    for folder in tree.get("folders", []):
        folder["readonly"] = True
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

    # User-created folders
    for uf in sorted(user.get("custom_folders", []), key=lambda f: f.get("sort_order", 0)):
        tree["folders"].append({**uf, "readonly": False})

    _assign_ids(tree)

    # Unfiled custom drills (not assigned to any user folder)
    unfiled = user.get("custom_drills", [])

    return {"folders": tree["folders"], "unfiled": unfiled}


def get_drill(drill_id: int) -> dict | None:
    tree = get_tree()
    for folder in tree.get("folders", []):
        for drill in folder.get("drills", []):
            if drill.get("id") == drill_id:
                drill["_folder"] = folder["name"]
                return drill
    for drill in tree.get("unfiled", []):
        if drill.get("id") == drill_id:
            drill["_folder"] = None
            return drill
    return None


def save_override(drill_id: int, data: dict) -> bool:
    """Save user override for a factory drill."""
    tree = get_tree()
    for folder in tree.get("folders", []):
        if not folder.get("readonly"):
            continue
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
    drill = get_drill(drill_id)
    if not drill:
        return
    if drill.get("_folder") is None:
        return  # unfiled custom drill — no override needed, it's stored directly
    key = _drill_key(drill["_folder"], drill["name"])
    user = _load_user()
    overrides = user.setdefault("overrides", {})
    ov = overrides.setdefault(key, {})
    ov["user_count"] = count
    _save_user(user)


def reset_drill(drill_id: int) -> bool:
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
    user = _load_user()
    user["overrides"] = {}
    _save_user(user)


# ── Custom folders ────────────────────────────────────────────────────────────

def create_folder(name: str) -> dict:
    user = _load_user()
    folders = user.setdefault("custom_folders", [])
    new_id = max((f["id"] for f in folders), default=90000) + 1
    sort_order = max((f.get("sort_order", 0) for f in folders), default=-1) + 1
    folder = {"id": new_id, "name": name, "sort_order": sort_order, "drills": []}
    folders.append(folder)
    _save_user(user)
    return folder


def rename_folder(folder_id: int, name: str) -> bool:
    user = _load_user()
    for f in user.get("custom_folders", []):
        if f["id"] == folder_id:
            f["name"] = name
            _save_user(user)
            return True
    return False


def delete_folder(folder_id: int) -> bool:
    user = _load_user()
    folders = user.get("custom_folders", [])
    for i, f in enumerate(folders):
        if f["id"] == folder_id:
            user.setdefault("custom_drills", []).extend(f.get("drills", []))
            del folders[i]
            _save_user(user)
            return True
    return False


def reorder_folders(order: list) -> None:
    """order = [{id, sort_order}, ...]"""
    user = _load_user()
    sort_map = {item["id"]: item["sort_order"] for item in order}
    for f in user.get("custom_folders", []):
        if f["id"] in sort_map:
            f["sort_order"] = sort_map[f["id"]]
    user.get("custom_folders", []).sort(key=lambda f: f.get("sort_order", 0))
    _save_user(user)


def reorder_drills(items: list) -> None:
    """items = [{id, sort_order, folder_id}, ...]. Only moves custom drills."""
    user = _load_user()
    custom_drills = user.setdefault("custom_drills", [])
    folder_map = {f["id"]: f for f in user.get("custom_folders", [])}

    for item in items:
        drill_id = item["id"]
        folder_id = item.get("folder_id")
        sort_order = item.get("sort_order", 9999)

        drill = None
        source = None
        for d in custom_drills:
            if d.get("id") == drill_id:
                drill = d; source = custom_drills; break
        if not drill:
            for f in folder_map.values():
                for d in f.get("drills", []):
                    if d.get("id") == drill_id:
                        drill = d; source = f["drills"]; break
                if drill:
                    break
        if not drill:
            continue

        source.remove(drill)
        drill["sort_order"] = sort_order
        if folder_id is None:
            custom_drills.append(drill)
        elif folder_id in folder_map:
            folder_map[folder_id].setdefault("drills", []).append(drill)

    custom_drills.sort(key=lambda d: d.get("sort_order", 9999))
    for f in folder_map.values():
        f.get("drills", []).sort(key=lambda d: d.get("sort_order", 9999))

    user["custom_drills"] = custom_drills
    _save_user(user)


# ── Custom drills (unfiled) ───────────────────────────────────────────────────

def update_custom_drill(drill_id: int, data: dict) -> bool:
    user = _load_user()
    # Search unfiled
    for drill in user.get("custom_drills", []):
        if drill.get("id") == drill_id:
            for k, v in data.items():
                if k != "id":
                    drill[k] = v
            _save_user(user)
            return True
    # Search user folders
    for f in user.get("custom_folders", []):
        for drill in f.get("drills", []):
            if drill.get("id") == drill_id:
                for k, v in data.items():
                    if k != "id":
                        drill[k] = v
                _save_user(user)
                return True
    return False


def create_custom_drill(data: dict) -> int:
    user = _load_user()
    # Collect all existing IDs
    all_ids = [d.get("id", 0) for d in user.get("custom_drills", [])]
    for f in user.get("custom_folders", []):
        all_ids += [d.get("id", 0) for d in f.get("drills", [])]
    data["id"] = max(all_ids, default=99000) + 1
    data["readonly"] = False
    data["modified"] = False
    user.setdefault("custom_drills", []).append(data)
    _save_user(user)
    return data["id"]


def delete_custom_drill(drill_id: int):
    user = _load_user()
    user["custom_drills"] = [d for d in user.get("custom_drills", []) if d.get("id") != drill_id]
    for f in user.get("custom_folders", []):
        f["drills"] = [d for d in f.get("drills", []) if d.get("id") != drill_id]
    _save_user(user)
