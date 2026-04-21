"""Unit tests for serves storage (defaults + overrides + custom groups/serves)."""

import json
import serves


# ── Tree loading + ID assignment ─────────────────────────────────────────────

def test_get_tree_loads_factory(tmp_serves_files):
    tree = serves.get_tree()
    assert len(tree["groups"]) == 2
    assert tree["groups"][0]["name"] == "Pendulum"
    assert tree["groups"][0]["readonly"] is True


def test_ids_are_assigned_deterministically(tmp_serves_files):
    tree = serves.get_tree()
    pendulum = tree["groups"][0]
    assert pendulum["id"] == 1000
    assert pendulum["serves"][0]["id"] == 1001
    assert pendulum["serves"][1]["id"] == 1002
    backhand = tree["groups"][1]
    assert backhand["id"] == 2000
    assert backhand["serves"][0]["id"] == 2001


def test_get_serve_by_id(tmp_serves_files):
    sv = serves.get_serve(1001)
    assert sv is not None
    assert sv["name"] == "Pendulum Short BH"
    assert sv["technique"] == "pendulum"
    assert len(sv["responses"]) == 2


def test_get_serve_nonexistent_returns_none(tmp_serves_files):
    assert serves.get_serve(99999) is None


# ── Duration override ────────────────────────────────────────────────────────

def test_save_duration_override_sets_modified_flag(tmp_serves_files):
    assert serves.save_duration_override(1001, 600) is True
    sv = serves.get_serve(1001)
    assert sv["duration_sec"] == 600
    assert sv["modified"] is True


def test_override_persists_across_loads(tmp_serves_files):
    serves.save_duration_override(1001, 450)
    user = json.loads(tmp_serves_files["user"].read_text())
    assert "Pendulum/Pendulum Short BH" in user["overrides"]
    assert user["overrides"]["Pendulum/Pendulum Short BH"]["duration_sec"] == 450


def test_reset_duration_removes_override(tmp_serves_files):
    serves.save_duration_override(1001, 500)
    serves.reset_duration(1001)
    sv = serves.get_serve(1001)
    assert sv["duration_sec"] == 300
    assert sv["modified"] is False


def test_reset_all_clears_all_overrides(tmp_serves_files):
    serves.save_duration_override(1001, 500)
    serves.save_duration_override(1002, 400)
    serves.reset_all()
    assert serves.get_serve(1001)["modified"] is False
    assert serves.get_serve(1002)["modified"] is False


def test_save_override_for_nonexistent_id_returns_false(tmp_serves_files):
    assert serves.save_duration_override(99999, 300) is False


# ── Custom groups ────────────────────────────────────────────────────────────

def test_create_custom_group(tmp_serves_files):
    group = serves.create_group("My Serves")
    assert group["id"] >= 90001
    assert group["name"] == "My Serves"
    tree = serves.get_tree()
    custom = [g for g in tree["groups"] if not g["readonly"]]
    assert len(custom) == 1
    assert custom[0]["name"] == "My Serves"


def test_rename_custom_group(tmp_serves_files):
    g = serves.create_group("Old")
    assert serves.rename_group(g["id"], "New") is True
    tree = serves.get_tree()
    assert any(grp["name"] == "New" for grp in tree["groups"])


def test_delete_custom_group(tmp_serves_files):
    g = serves.create_group("Temp")
    assert serves.delete_group(g["id"]) is True
    tree = serves.get_tree()
    assert not any(grp["id"] == g["id"] for grp in tree["groups"])


# ── Custom serves ────────────────────────────────────────────────────────────

def test_create_custom_serve(tmp_serves_files):
    g = serves.create_group("Custom")
    payload = {
        "group_id": g["id"],
        "name": "My Serve",
        "description": "Test",
        "technique": "pendulum",
        "spin_type": "sidespin",
        "spin_strength": 3,
        "length": "short",
        "placement": {"x": 0.3, "y": 0.8},
        "duration_sec": 300,
        "responses": [],
    }
    sid = serves.create_custom_serve(payload)
    assert sid >= 99001
    sv = serves.get_serve(sid)
    assert sv is not None
    assert sv["name"] == "My Serve"
    assert sv["readonly"] is False


def test_create_serve_invalid_group_raises(tmp_serves_files):
    import pytest
    with pytest.raises(ValueError):
        serves.create_custom_serve({"group_id": 99999, "name": "X"})


def test_update_custom_serve(tmp_serves_files):
    g = serves.create_group("G")
    sid = serves.create_custom_serve({"group_id": g["id"], "name": "Orig", "duration_sec": 100})
    assert serves.update_custom_serve(sid, {"name": "Updated", "duration_sec": 200}) is True
    sv = serves.get_serve(sid)
    assert sv["name"] == "Updated"
    assert sv["duration_sec"] == 200


def test_delete_custom_serve(tmp_serves_files):
    g = serves.create_group("G")
    sid = serves.create_custom_serve({"group_id": g["id"], "name": "Temp"})
    serves.delete_custom_serve(sid)
    assert serves.get_serve(sid) is None


def test_factory_serve_cannot_be_deleted_via_custom_path(tmp_serves_files):
    # delete_custom_serve should not affect factory serves
    serves.delete_custom_serve(1001)
    assert serves.get_serve(1001) is not None


# ── Reorder ──────────────────────────────────────────────────────────────────

def test_reorder_groups_updates_sort_order(tmp_serves_files):
    g1 = serves.create_group("A")
    g2 = serves.create_group("B")
    serves.reorder_groups([{"id": g1["id"], "sort_order": 1}, {"id": g2["id"], "sort_order": 0}])
    user = json.loads(tmp_serves_files["user"].read_text())
    order = {g["id"]: g["sort_order"] for g in user["custom_groups"]}
    assert order[g1["id"]] == 1
    assert order[g2["id"]] == 0


def test_reorder_serves_moves_between_groups(tmp_serves_files):
    g1 = serves.create_group("G1")
    g2 = serves.create_group("G2")
    sid = serves.create_custom_serve({"group_id": g1["id"], "name": "Mobile"})
    serves.reorder_serves([{"id": sid, "sort_order": 0, "group_id": g2["id"]}])
    sv = serves.get_serve(sid)
    assert sv["group_id"] == g2["id"]
