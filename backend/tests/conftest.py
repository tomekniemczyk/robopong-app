"""Shared fixtures for robopong backend tests."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import db
import drills
import exercises
import presets
import recordings
import serves
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


SAMPLE_SERVES = {
    "groups": [
        {
            "name": "Pendulum",
            "icon": "🎾",
            "description": "Pendulum serves",
            "serves": [
                {
                    "name": "Pendulum Short BH",
                    "description": "Short sidespin",
                    "technique": "pendulum",
                    "spin_type": "sidespin",
                    "spin_strength": 3,
                    "length": "short",
                    "placement": {"x": 0.3, "y": 0.8},
                    "duration_sec": 300,
                    "responses": [
                        {"name": "Push long", "description": "", "balls": [{"top_speed": 30, "bot_speed": 100, "oscillation": 140, "height": 110, "rotation": 150, "wait_ms": 6000}]},
                        {"name": "Flick", "description": "", "balls": [{"top_speed": 130, "bot_speed": 20, "oscillation": 160, "height": 130, "rotation": 150, "wait_ms": 5500}]}
                    ]
                },
                {
                    "name": "Pendulum Long FH",
                    "description": "Long topspin",
                    "technique": "pendulum",
                    "spin_type": "topspin",
                    "spin_strength": 2,
                    "length": "long",
                    "placement": {"x": 0.75, "y": 0.95},
                    "duration_sec": 240,
                    "responses": [
                        {"name": "Block", "description": "", "balls": [{"top_speed": 90, "bot_speed": 30, "oscillation": 150, "height": 125, "rotation": 150, "wait_ms": 5000}]}
                    ]
                }
            ]
        },
        {
            "name": "Backhand",
            "icon": "↩",
            "description": "Backhand serves",
            "serves": [
                {
                    "name": "Backhand Short",
                    "description": "Short BH",
                    "technique": "backhand",
                    "spin_type": "sidespin",
                    "spin_strength": 3,
                    "length": "short",
                    "placement": {"x": 0.5, "y": 0.78},
                    "duration_sec": 300,
                    "responses": []
                }
            ]
        }
    ]
}


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


# ── Serves fixtures ──────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_serves_files(tmp_path, monkeypatch):
    """Patch serves.py file paths to tmp_path with sample data."""
    defaults_file = tmp_path / "serves_default.json"
    user_file = tmp_path / ".serves_user.json"
    defaults_file.write_text(json.dumps(SAMPLE_SERVES))
    monkeypatch.setattr(serves, "DEFAULTS_FILE", defaults_file)
    monkeypatch.setattr(serves, "USER_FILE", user_file)
    return {"defaults": defaults_file, "user": user_file}


# ── Training fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_training_files(tmp_path, monkeypatch):
    """Patch training + db to tmp_path (no defaults)."""
    monkeypatch.setattr(db, "DB", tmp_path / "test_training.db")
    monkeypatch.setattr(training, "DEFAULTS_FILE", tmp_path / "trainings_default.json")
    db.init()
    return {"db": tmp_path / "test_training.db"}


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
    monkeypatch.setattr(serves, "DEFAULTS_FILE", tmp_path / "serves_default.json")
    monkeypatch.setattr(serves, "USER_FILE", tmp_path / ".serves_user.json")
    monkeypatch.setattr(training, "DEFAULTS_FILE", tmp_path / "trainings_default.json")
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", tmp_path / "recordings")

    # Write sample defaults
    (tmp_path / "drills_default.json").write_text(json.dumps(SAMPLE_DEFAULTS))
    (tmp_path / "exercises_default.json").write_text(json.dumps(SAMPLE_EXERCISES))
    (tmp_path / "serves_default.json").write_text(json.dumps(SAMPLE_SERVES))

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
