"""Tests for exercises.py module functions."""

import json
import exercises


# ── get_exercises ────────────────────────────────────────────────────────────

def test_get_exercises_returns_categories(tmp_exercises_files):
    data = exercises.get_exercises()
    assert "categories" in data
    assert len(data["categories"]) == 2
    assert data["categories"][0]["name"] == "Warmup"
    assert data["categories"][1]["name"] == "Footwork"


def test_get_exercises_assigns_ids(tmp_exercises_files):
    data = exercises.get_exercises()
    warmup = data["categories"][0]
    assert warmup["id"] == 100
    assert warmup["exercises"][0]["id"] == 101
    assert warmup["exercises"][1]["id"] == 102
    footwork = data["categories"][1]
    assert footwork["id"] == 200
    assert footwork["exercises"][0]["id"] == 201


def test_get_exercises_sets_category_on_exercises(tmp_exercises_files):
    data = exercises.get_exercises()
    ex = data["categories"][0]["exercises"][0]
    assert ex["category"] == "Warmup"


def test_get_exercises_empty_defaults(tmp_exercises_files):
    tmp_exercises_files["defaults"].write_text(json.dumps({"categories": []}))
    data = exercises.get_exercises()
    assert data["categories"] == []


def test_get_exercises_with_user_overrides(tmp_exercises_files):
    user_data = {"overrides": {"Warmup/Jogging in Place": {"duration_sec": 120}}}
    tmp_exercises_files["user"].write_text(json.dumps(user_data))
    data = exercises.get_exercises()
    jogging = data["categories"][0]["exercises"][0]
    assert jogging["duration_sec"] == 120
    assert jogging["modified"] is True


def test_get_exercises_unmodified_default(tmp_exercises_files):
    data = exercises.get_exercises()
    jogging = data["categories"][0]["exercises"][0]
    assert jogging["duration_sec"] == 60
    assert jogging["modified"] is False


# ── get_exercise ─────────────────────────────────────────────────────────────

def test_get_exercise_found(tmp_exercises_files):
    data = exercises.get_exercises()
    eid = data["categories"][0]["exercises"][0]["id"]
    ex = exercises.get_exercise(eid)
    assert ex is not None
    assert ex["name"] == "Jogging in Place"


def test_get_exercise_not_found(tmp_exercises_files):
    assert exercises.get_exercise(99999) is None


# ── save_override ────────────────────────────────────────────────────────────

def test_save_override_persists(tmp_exercises_files):
    data = exercises.get_exercises()
    eid = data["categories"][0]["exercises"][0]["id"]
    exercises.save_override(eid, 90)
    ex = exercises.get_exercise(eid)
    assert ex["duration_sec"] == 90
    assert ex["modified"] is True


def test_save_override_nonexistent(tmp_exercises_files):
    # Should not raise
    exercises.save_override(99999, 120)


# ── reset_all ────────────────────────────────────────────────────────────────

def test_reset_all(tmp_exercises_files):
    data = exercises.get_exercises()
    eid = data["categories"][0]["exercises"][0]["id"]
    exercises.save_override(eid, 999)
    exercises.reset_all()
    ex = exercises.get_exercise(eid)
    assert ex["duration_sec"] == 60
    assert ex["modified"] is False
