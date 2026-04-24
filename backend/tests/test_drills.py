"""Tests for drills.py module functions."""

import json
import drills


# ── get_tree ─────────────────────────────────────────────────────────────────

def test_get_tree_returns_folders(tmp_drills_files):
    tree = drills.get_tree()
    assert "folders" in tree
    assert len(tree["folders"]) == 1
    assert tree["folders"][0]["name"] == "Introductory"


def test_get_tree_assigns_ids(tmp_drills_files):
    tree = drills.get_tree()
    folder = tree["folders"][0]
    assert folder["id"] == 1000
    assert folder["drills"][0]["id"] == 1001
    assert folder["drills"][1]["id"] == 1002


def test_get_tree_marks_factory_readonly(tmp_drills_files):
    tree = drills.get_tree()
    assert tree["folders"][0]["readonly"] is True


def test_get_tree_empty_defaults(tmp_drills_files):
    tmp_drills_files["defaults"].write_text(json.dumps({"folders": []}))
    tree = drills.get_tree()
    assert tree["folders"] == []


def test_get_tree_with_user_overrides(tmp_drills_files):
    user_data = {"overrides": {"Introductory/Forehand Warmup": {
        "balls": [{"top_speed": 200, "bot_speed": 0, "oscillation": 150,
                   "height": 150, "rotation": 150, "wait_ms": 1000}],
        "repeat": 5,
        "delay_s": 1.0,
        "user_count": 42,
    }}}
    tmp_drills_files["user"].write_text(json.dumps(user_data))
    tree = drills.get_tree()
    drill = tree["folders"][0]["drills"][0]
    assert drill["balls"][0]["top_speed"] == 200
    assert drill["repeat"] == 5
    assert drill["user_count"] == 42
    assert drill["modified"] is True


def test_get_tree_unmodified_drill_defaults(tmp_drills_files):
    tree = drills.get_tree()
    drill = tree["folders"][0]["drills"][0]
    assert drill["user_count"] is None
    assert drill["modified"] is False


# ── get_drill ────────────────────────────────────────────────────────────────

def test_get_drill_found(tmp_drills_files):
    tree = drills.get_tree()
    drill_id = tree["folders"][0]["drills"][0]["id"]
    drill = drills.get_drill(drill_id)
    assert drill is not None
    assert drill["name"] == "Forehand Warmup"


def test_get_drill_not_found(tmp_drills_files):
    assert drills.get_drill(99999) is None


# ── save_override ────────────────────────────────────────────────────────────

def test_save_override_persists(tmp_drills_files):
    tree = drills.get_tree()
    drill_id = tree["folders"][0]["drills"][0]["id"]
    new_balls = [{"top_speed": 200, "bot_speed": 10, "oscillation": 140,
                  "height": 120, "rotation": 160, "wait_ms": 1500}]
    result = drills.save_override(drill_id, {"balls": new_balls, "repeat": 3})
    assert result is True
    drill = drills.get_drill(drill_id)
    assert drill["balls"] == new_balls
    assert drill["repeat"] == 3
    assert drill["modified"] is True


def test_save_override_nonexistent_returns_false(tmp_drills_files):
    assert drills.save_override(99999, {"balls": []}) is False


# ── set_user_count ───────────────────────────────────────────────────────────

def test_set_user_count(tmp_drills_files):
    tree = drills.get_tree()
    drill_id = tree["folders"][0]["drills"][0]["id"]
    drills.set_user_count(drill_id, 100)
    drill = drills.get_drill(drill_id)
    assert drill["user_count"] == 100


def test_set_user_count_nonexistent(tmp_drills_files):
    # Should not raise
    drills.set_user_count(99999, 50)


# ── reset_drill ──────────────────────────────────────────────────────────────

def test_reset_drill(tmp_drills_files):
    tree = drills.get_tree()
    drill_id = tree["folders"][0]["drills"][0]["id"]
    drills.save_override(drill_id, {"balls": [], "repeat": 5})
    result = drills.reset_drill(drill_id)
    assert result is True
    drill = drills.get_drill(drill_id)
    assert drill["modified"] is False


def test_reset_drill_nonexistent(tmp_drills_files):
    assert drills.reset_drill(99999) is False


# ── reset_all ────────────────────────────────────────────────────────────────

def test_reset_all(tmp_drills_files):
    tree = drills.get_tree()
    d1 = tree["folders"][0]["drills"][0]["id"]
    d2 = tree["folders"][0]["drills"][1]["id"]
    drills.save_override(d1, {"repeat": 10})
    drills.save_override(d2, {"repeat": 20})
    drills.reset_all()
    assert drills.get_drill(d1)["modified"] is False
    assert drills.get_drill(d2)["modified"] is False


# ── create_folder ────────────────────────────────────────────────────────────

def test_create_folder(tmp_drills_files):
    folder = drills.create_folder("My Folder")
    assert folder["name"] == "My Folder"
    assert folder["id"] >= 90000
    assert folder["drills"] == []


def test_create_folder_appears_in_tree(tmp_drills_files):
    drills.create_folder("Custom")
    tree = drills.get_tree()
    names = [f["name"] for f in tree["folders"]]
    assert "Custom" in names


def test_create_multiple_folders_unique_ids(tmp_drills_files):
    f1 = drills.create_folder("A")
    f2 = drills.create_folder("B")
    assert f1["id"] != f2["id"]


# ── rename_folder ────────────────────────────────────────────────────────────

def test_rename_folder(tmp_drills_files):
    folder = drills.create_folder("Old Name")
    result = drills.rename_folder(folder["id"], "New Name")
    assert result is True
    tree = drills.get_tree()
    custom = [f for f in tree["folders"] if f["id"] == folder["id"]]
    assert custom[0]["name"] == "New Name"


def test_rename_folder_not_found(tmp_drills_files):
    assert drills.rename_folder(99999, "X") is False


# ── delete_folder ────────────────────────────────────────────────────────────

def test_delete_folder(tmp_drills_files):
    folder = drills.create_folder("ToDelete")
    result = drills.delete_folder(folder["id"])
    assert result is True
    tree = drills.get_tree()
    ids = [f["id"] for f in tree["folders"]]
    assert folder["id"] not in ids


def test_delete_folder_not_found(tmp_drills_files):
    assert drills.delete_folder(99999) is False


# ── create_custom_drill ──────────────────────────────────────────────────────

def test_create_custom_drill(tmp_drills_files):
    data = {"name": "My Drill", "balls": [
        {"top_speed": 80, "bot_speed": 0, "oscillation": 150,
         "height": 150, "rotation": 150, "wait_ms": 1000}
    ], "repeat": 0}
    drill_id = drills.create_custom_drill(data)
    assert drill_id >= 99001
    drill = drills.get_drill(drill_id)
    assert drill is not None
    assert drill["name"] == "My Drill"


def test_create_custom_drill_with_parent_ref(tmp_drills_files):
    data = {
        "name": "Forhend (mod)",
        "balls": [{"top_speed": 100, "bot_speed": 0, "oscillation": 150,
                   "height": 170, "rotation": 150, "wait_ms": 1500}],
        "repeat": 0,
        "parent_id": 1234,
        "parent_name": "Forhend topspin",
    }
    drill_id = drills.create_custom_drill(data)
    drill = drills.get_drill(drill_id)
    assert drill["parent_id"] == 1234
    assert drill["parent_name"] == "Forhend topspin"


# ── update_custom_drill ──────────────────────────────────────────────────────

def test_update_custom_drill(tmp_drills_files):
    drill_id = drills.create_custom_drill({"name": "Old", "balls": [], "repeat": 0})
    result = drills.update_custom_drill(drill_id, {"name": "Updated"})
    assert result is True
    drill = drills.get_drill(drill_id)
    assert drill["name"] == "Updated"


def test_update_custom_drill_not_found(tmp_drills_files):
    assert drills.update_custom_drill(99999, {"name": "X"}) is False


# ── delete_custom_drill ──────────────────────────────────────────────────────

def test_delete_custom_drill(tmp_drills_files):
    drill_id = drills.create_custom_drill({"name": "Del", "balls": [], "repeat": 0})
    drills.delete_custom_drill(drill_id)
    assert drills.get_drill(drill_id) is None


# ── reorder_folders ──────────────────────────────────────────────────────────

def test_reorder_folders(tmp_drills_files):
    f1 = drills.create_folder("First")
    f2 = drills.create_folder("Second")
    drills.reorder_folders([
        {"id": f1["id"], "sort_order": 10},
        {"id": f2["id"], "sort_order": 1},
    ])
    tree = drills.get_tree()
    custom = [f for f in tree["folders"] if f["id"] >= 90000]
    assert custom[0]["name"] == "Second"
    assert custom[1]["name"] == "First"


# ── reorder_drills ───────────────────────────────────────────────────────────

def test_reorder_drills_move_to_folder(tmp_drills_files):
    folder = drills.create_folder("Target")
    drill_id = drills.create_custom_drill({"name": "Moveable", "balls": [], "repeat": 0})
    drills.reorder_drills([{"id": drill_id, "sort_order": 0, "folder_id": folder["id"]}])
    tree = drills.get_tree()
    target = [f for f in tree["folders"] if f["id"] == folder["id"]][0]
    drill_ids = [d["id"] for d in target.get("drills", [])]
    assert drill_id in drill_ids
