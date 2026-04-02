"""Tests for training.py STORAGE functions (not the runner)."""

import json
import training


# ── get_trainings ────────────────────────────────────────────────────────────

def test_get_trainings_empty(tmp_training_files):
    assert training.get_trainings() == []


def test_get_trainings_populated(tmp_training_files):
    training.save_training({"name": "Morning", "steps": []})
    training.save_training({"name": "Evening", "steps": []})
    result = training.get_trainings()
    assert len(result) == 2
    names = {t["name"] for t in result}
    assert names == {"Morning", "Evening"}


def test_get_trainings_assigns_ids(tmp_training_files):
    training.save_training({"name": "T1", "steps": []})
    result = training.get_trainings()
    assert result[0]["id"] == 1


# ── save_training ────────────────────────────────────────────────────────────

def test_save_training_create(tmp_training_files):
    tid = training.save_training({"name": "New", "steps": [{"drill_id": 1}]})
    assert tid >= 1
    t = training.get_training(tid)
    assert t["name"] == "New"
    assert t["steps"][0]["drill_id"] == 1
    assert "drill_name" in t["steps"][0]


def test_save_training_update(tmp_training_files):
    tid = training.save_training({"name": "V1", "steps": []})
    training.save_training({"id": tid, "name": "V2", "steps": [{"drill_id": 5}]})
    t = training.get_training(tid)
    assert t["name"] == "V2"
    assert t["steps"][0]["drill_id"] == 5
    assert "drill_name" in t["steps"][0]


def test_save_training_update_does_not_duplicate(tmp_training_files):
    tid = training.save_training({"name": "Once", "steps": []})
    training.save_training({"id": tid, "name": "Updated", "steps": []})
    assert len(training.get_trainings()) == 1


# ── get_training ─────────────────────────────────────────────────────────────

def test_get_training_found(tmp_training_files):
    tid = training.save_training({"name": "Find me", "steps": []})
    t = training.get_training(tid)
    assert t is not None
    assert t["name"] == "Find me"


def test_get_training_not_found(tmp_training_files):
    assert training.get_training(9999) is None


# ── delete_training ──────────────────────────────────────────────────────────

def test_delete_training(tmp_training_files):
    tid = training.save_training({"name": "Del", "steps": []})
    training.delete_training(tid)
    assert training.get_training(tid) is None


def test_delete_training_nonexistent(tmp_training_files):
    # Should not raise
    training.delete_training(9999)
    assert training.get_trainings() == []


def test_delete_training_preserves_others(tmp_training_files):
    t1 = training.save_training({"name": "Keep", "steps": []})
    t2 = training.save_training({"name": "Remove", "steps": []})
    training.delete_training(t2)
    result = training.get_trainings()
    assert len(result) == 1
    assert result[0]["name"] == "Keep"
