"""File-based serves library.

serves_default.json — factory serves grouped by technique (read-only)
.serves_user.json   — user overrides (duration_sec), custom groups, custom serves
"""

import json
from pathlib import Path

DEFAULTS_FILE = Path(__file__).parent / "serves_default.json"
USER_FILE     = Path(__file__).parent / ".serves_user.json"


def _load_defaults() -> dict:
    return json.loads(DEFAULTS_FILE.read_text()) if DEFAULTS_FILE.exists() else {"groups": []}


def _load_user() -> dict:
    try:
        return json.loads(USER_FILE.read_text())
    except Exception:
        return {}


def _save_user(data: dict):
    USER_FILE.write_text(json.dumps(data, indent=2))


def _serve_key(group_name: str, serve_name: str) -> str:
    return f"{group_name}/{serve_name}"


def _assign_ids(tree: dict) -> dict:
    """Assign stable IDs to factory groups/serves. Custom (id>=90000) keep theirs."""
    factory_count = 0
    for group in tree.get("groups", []):
        if group.get("id", 0) < 90000:
            factory_count += 1
            group["id"] = factory_count * 1000
        for si, serve in enumerate(group.get("serves", [])):
            if not serve.get("id"):
                serve["id"] = group["id"] + si + 1
            serve["group_id"] = group["id"]
            serve["group_name"] = group["name"]
    return tree


def get_tree() -> dict:
    """Full tree with overrides + custom groups/serves merged."""
    tree = _load_defaults()
    user = _load_user()
    overrides = user.get("overrides", {})

    for group in tree.get("groups", []):
        group["readonly"] = True
        for serve in group.get("serves", []):
            serve["readonly"] = True
            key = _serve_key(group["name"], serve["name"])
            if key in overrides and "duration_sec" in overrides[key]:
                serve["duration_sec"] = overrides[key]["duration_sec"]
                serve["modified"] = True
            else:
                serve["modified"] = False

    for ug in sorted(user.get("custom_groups", []), key=lambda g: g.get("sort_order", 0)):
        ug = {**ug, "readonly": False}
        for sv in ug.get("serves", []):
            sv.setdefault("readonly", False)
            sv.setdefault("modified", False)
        tree["groups"].append(ug)

    _assign_ids(tree)
    return tree


def get_serve(serve_id: int) -> dict | None:
    tree = get_tree()
    for group in tree.get("groups", []):
        for serve in group.get("serves", []):
            if serve.get("id") == serve_id:
                return serve
    return None


def save_duration_override(serve_id: int, duration_sec: int) -> bool:
    tree = get_tree()
    for group in tree.get("groups", []):
        for serve in group.get("serves", []):
            if serve.get("id") == serve_id:
                key = _serve_key(group["name"], serve["name"])
                user = _load_user()
                overrides = user.setdefault("overrides", {})
                overrides.setdefault(key, {})["duration_sec"] = duration_sec
                _save_user(user)
                return True
    return False


def reset_duration(serve_id: int) -> bool:
    tree = get_tree()
    for group in tree.get("groups", []):
        for serve in group.get("serves", []):
            if serve.get("id") == serve_id:
                key = _serve_key(group["name"], serve["name"])
                user = _load_user()
                if key in user.get("overrides", {}):
                    del user["overrides"][key]
                    _save_user(user)
                return True
    return False


def reset_all():
    user = _load_user()
    user["overrides"] = {}
    _save_user(user)


# ── Custom groups ────────────────────────────────────────────────────────────

def create_group(name: str) -> dict:
    user = _load_user()
    groups = user.setdefault("custom_groups", [])
    new_id = max((g["id"] for g in groups), default=90000) + 1
    sort_order = max((g.get("sort_order", 0) for g in groups), default=-1) + 1
    group = {"id": new_id, "name": name, "sort_order": sort_order, "serves": []}
    groups.append(group)
    _save_user(user)
    return group


def rename_group(group_id: int, name: str) -> bool:
    user = _load_user()
    for g in user.get("custom_groups", []):
        if g["id"] == group_id:
            g["name"] = name
            _save_user(user)
            return True
    return False


def delete_group(group_id: int) -> bool:
    user = _load_user()
    groups = user.get("custom_groups", [])
    for i, g in enumerate(groups):
        if g["id"] == group_id:
            del groups[i]
            _save_user(user)
            return True
    return False


def reorder_groups(order: list) -> None:
    """order = [{id, sort_order}, ...] — only custom groups."""
    user = _load_user()
    sort_map = {item["id"]: item["sort_order"] for item in order}
    for g in user.get("custom_groups", []):
        if g["id"] in sort_map:
            g["sort_order"] = sort_map[g["id"]]
    user.get("custom_groups", []).sort(key=lambda g: g.get("sort_order", 0))
    _save_user(user)


# ── Custom serves ────────────────────────────────────────────────────────────

def create_custom_serve(data: dict) -> int:
    user = _load_user()
    all_ids = []
    for g in user.get("custom_groups", []):
        all_ids += [s.get("id", 0) for s in g.get("serves", [])]
    data["id"] = max(all_ids, default=99000) + 1
    data["readonly"] = False
    data["modified"] = False
    group_id = data.get("group_id")
    for g in user.get("custom_groups", []):
        if g["id"] == group_id:
            g.setdefault("serves", []).append(data)
            _save_user(user)
            return data["id"]
    raise ValueError(f"Custom group {group_id} not found")


def update_custom_serve(serve_id: int, data: dict) -> bool:
    user = _load_user()
    for g in user.get("custom_groups", []):
        for serve in g.get("serves", []):
            if serve.get("id") == serve_id:
                for k, v in data.items():
                    if k != "id":
                        serve[k] = v
                _save_user(user)
                return True
    return False


def delete_custom_serve(serve_id: int):
    user = _load_user()
    for g in user.get("custom_groups", []):
        g["serves"] = [s for s in g.get("serves", []) if s.get("id") != serve_id]
    _save_user(user)


def reorder_serves(items: list) -> None:
    """items = [{id, sort_order, group_id}, ...] — only custom serves."""
    user = _load_user()
    group_map = {g["id"]: g for g in user.get("custom_groups", [])}

    for item in items:
        serve_id = item["id"]
        target_group_id = item.get("group_id")
        sort_order = item.get("sort_order", 9999)

        serve = None
        source = None
        for g in group_map.values():
            for s in g.get("serves", []):
                if s.get("id") == serve_id:
                    serve = s
                    source = g["serves"]
                    break
            if serve:
                break
        if not serve:
            continue

        source.remove(serve)
        serve["sort_order"] = sort_order
        if target_group_id in group_map:
            group_map[target_group_id].setdefault("serves", []).append(serve)

    for g in group_map.values():
        g.get("serves", []).sort(key=lambda s: s.get("sort_order", 9999))

    _save_user(user)
