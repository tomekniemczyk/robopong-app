"""Shared fixtures for robopong backend tests."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import db
import drills
import exercises
import presets
import training


SAMPLE_DEFAULTS = {
    "folders": [
        {
            "name": "Introductory",
            "description": "Beginner drills",
            "sort_order": 0,
            "readonly": True,
            "drills": [
                {
                    "name": "Forehand Warmup",
                    "description": "FH warmup",
                    "youtube_id": "",
                    "delay_s": 0.0,
                    "balls": [{"top_speed": 120, "bot_speed": 0, "oscillation": 164,
                               "height": 116, "rotation": 150, "wait_ms": 2100}],
                    "repeat": 0,
                    "sort_order": 0,
                    "readonly": True,
                },
                {
                    "name": "Backhand Warmup",
                    "description": "BH warmup",
                    "youtube_id": "",
                    "delay_s": 0.0,
                    "balls": [{"top_speed": 120, "bot_speed": 0, "oscillation": 136,
                               "height": 116, "rotation": 150, "wait_ms": 2100}],
                    "repeat": 0,
                    "sort_order": 1,
                    "readonly": True,
                },
            ],
        }
    ]
}


SAMPLE_EXERCISES = {
    "categories": [
        {
            "name": "Warmup",
            "icon": "\U0001f525",
            "exercises": [
                {"name": "Jogging in Place", "duration_sec": 60, "description": "Jog"},
                {"name": "Arm Circles", "duration_sec": 30, "description": "Arms"},
            ],
        },
        {
            "name": "Footwork",
            "icon": "\U0001f45f",
            "exercises": [
                {"name": "Side Shuffle", "duration_sec": 60, "description": "Shuffle"},
            ],
        },
    ]
}


BALL = {"top_speed": 50, "bot_speed": 50, "oscillation": 128,
        "height": 128, "rotation": 128, "wait_ms": 1500}


# ── Drills fixtures ──────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_drills_files(tmp_path, monkeypatch):
    """Patch drills.py file paths to tmp_path with sample data."""
    defaults_file = tmp_path / "drills_default.json"
    user_file = tmp_path / ".drills_user.json"
    defaults_file.write_text(json.dumps(SAMPLE_DEFAULTS))
    monkeypatch.setattr(drills, "DEFAULTS_FILE", defaults_file)
    monkeypatch.setattr(drills, "USER_FILE", user_file)
    return {"defaults": defaults_file, "user": user_file}


# ── Exercises fixtures ───────────────────────────────────────────────────────

@pytest.fixture()
def tmp_exercises_files(tmp_path, monkeypatch):
    """Patch exercises.py file paths to tmp_path with sample data."""
    defaults_file = tmp_path / "exercises_default.json"
    user_file = tmp_path / ".exercises_user.json"
    defaults_file.write_text(json.dumps(SAMPLE_EXERCISES))
    monkeypatch.setattr(exercises, "DEFAULTS_FILE", defaults_file)
    monkeypatch.setattr(exercises, "USER_FILE", user_file)
    return {"defaults": defaults_file, "user": user_file}


# ── Training fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_training_files(tmp_path, monkeypatch):
    """Patch training.py file path to tmp_path."""
    trainings_file = tmp_path / ".trainings.json"
    monkeypatch.setattr(training, "TRAININGS_FILE", trainings_file)
    return {"file": trainings_file}


# ── Full client fixture (for API integration tests) ─────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with all storage isolated to tmp_path."""
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(presets, "DB", tmp_path / "presets.db")
    monkeypatch.setattr(drills, "DEFAULTS_FILE", tmp_path / "drills_default.json")
    monkeypatch.setattr(drills, "USER_FILE", tmp_path / ".drills_user.json")
    monkeypatch.setattr(exercises, "DEFAULTS_FILE", tmp_path / "exercises_default.json")
    monkeypatch.setattr(exercises, "USER_FILE", tmp_path / ".exercises_user.json")
    monkeypatch.setattr(training, "TRAININGS_FILE", tmp_path / ".trainings.json")

    # Write sample defaults
    (tmp_path / "drills_default.json").write_text(json.dumps(SAMPLE_DEFAULTS))
    (tmp_path / "exercises_default.json").write_text(json.dumps(SAMPLE_EXERCISES))

    mock_robot = MagicMock()
    mock_robot.is_connected = False
    mock_robot.firmware = ""
    mock_robot.device = ""
    mock_robot.transport_type = ""

    with patch("main.Robot", return_value=mock_robot), \
         patch("main._load_last_addr", return_value=""):
        import main
        from starlette.testclient import TestClient
        with TestClient(main.app) as c:
            yield c
