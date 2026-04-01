"""Tests for enhanced history: total_balls, reference protection, skip recording discard."""

import pytest
import db
import training
import recordings


@pytest.fixture()
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", tmp_path / "recordings")
    db.init()
    return tmp_path


# ── total_balls in training history ───────────────────────────────────────

def test_record_run_with_total_balls(setup_db):
    p = db.create_player("Alice")
    hid = db.record_training_run(101, p["id"], 120, "completed", 3, 3, total_balls=180)
    h = db.get_history_entry(hid)
    assert h["total_balls"] == 180


def test_record_run_without_total_balls(setup_db):
    p = db.create_player("Bob")
    hid = db.record_training_run(101, p["id"], 60, "stopped", 1, 3)
    h = db.get_history_entry(hid)
    assert h["total_balls"] is None


def test_total_balls_in_history_list(setup_db):
    p = db.create_player("Charlie")
    db.record_training_run(101, p["id"], 120, "completed", 3, 3, total_balls=180)
    db.record_training_run(102, p["id"], 60, "completed", 2, 2, total_balls=100)
    rows = db.get_training_history(player_id=p["id"])
    assert len(rows) == 2
    balls = {r["total_balls"] for r in rows}
    assert balls == {180, 100}


def test_total_balls_in_player_stats(setup_db):
    p = db.create_player("Dave")
    db.record_training_run(101, p["id"], 120, "completed", 3, 3, total_balls=180)
    db.record_training_run(102, p["id"], 60, "completed", 2, 2, total_balls=120)
    stats = db.get_player_stats(p["id"])
    assert stats["total_balls"] == 300


def test_total_balls_stats_with_null(setup_db):
    """Old entries without total_balls should not break stats."""
    p = db.create_player("Eve")
    db.record_training_run(101, p["id"], 120, "completed", 3, 3)  # no total_balls
    db.record_training_run(102, p["id"], 60, "completed", 2, 2, total_balls=100)
    stats = db.get_player_stats(p["id"])
    assert stats["total_balls"] == 100


# ── TrainingRunner._count_balls ───────────────────────────────────────────

def test_count_balls_method():
    runner = training.TrainingRunner()
    runner._steps_completed = 3
    runner._steps_skipped = [1]
    steps = [
        {"drill_id": 1, "count": 60},
        {"drill_id": 2, "count": 40},  # skipped
        {"drill_id": 3, "count": 80},
        {"drill_id": 4, "count": 100},  # not reached
    ]
    assert runner._count_balls(steps) == 140  # 60 + 80 (skip 40, not reach 100)


def test_count_balls_with_exercises():
    runner = training.TrainingRunner()
    runner._steps_completed = 3
    runner._steps_skipped = []
    steps = [
        {"drill_id": 1, "count": 60},
        {"exercise_id": 42, "duration_sec": 60},  # exercise, no balls
        {"drill_id": 3, "count": 80},
    ]
    assert runner._count_balls(steps) == 140


def test_count_balls_solo_drill():
    runner = training.TrainingRunner()
    runner._steps_completed = 1
    runner._steps_skipped = []
    steps = [{"drill_id": 7, "count": 30}]
    assert runner._count_balls(steps) == 30


def test_count_balls_nothing_completed():
    runner = training.TrainingRunner()
    runner._steps_completed = 0
    runner._steps_skipped = []
    assert runner._count_balls([{"drill_id": 1, "count": 60}]) == 0


# ── Reference protection ─────────────────────────────────────────────────

def test_get_trainings_referencing_drill(setup_db, monkeypatch):
    monkeypatch.setattr(training, "DEFAULTS_FILE", setup_db / "trainings_default.json")
    (setup_db / "trainings_default.json").write_text('{"folders":[]}')
    # Create a training with a drill reference
    tid = db.save_user_training({
        "name": "My Training",
        "steps": [{"drill_id": 99, "drill_name": "Test", "count": 60, "percent": 100, "pause_after_sec": 30}]
    })
    refs = training.get_trainings_referencing_drill(99)
    assert "My Training" in refs


def test_get_trainings_referencing_drill_none(setup_db, monkeypatch):
    monkeypatch.setattr(training, "DEFAULTS_FILE", setup_db / "trainings_default.json")
    (setup_db / "trainings_default.json").write_text('{"folders":[]}')
    refs = training.get_trainings_referencing_drill(999)
    assert refs == []


def test_get_trainings_referencing_exercise(setup_db, monkeypatch):
    monkeypatch.setattr(training, "DEFAULTS_FILE", setup_db / "trainings_default.json")
    (setup_db / "trainings_default.json").write_text('{"folders":[]}')
    db.save_user_training({
        "name": "Ex Training",
        "steps": [{"exercise_id": 42, "exercise_name": "Jog", "duration_sec": 60, "pause_after_sec": 15}]
    })
    refs = training.get_trainings_referencing_exercise(42)
    assert "Ex Training" in refs


# ── Skip recording discard ────────────────────────────────────────────────

def test_recorder_discards_short_recording(setup_db, monkeypatch):
    """Recording < 3 seconds should be discarded, not saved to DB."""
    from datetime import datetime, timedelta
    from unittest.mock import MagicMock

    rec = recordings.Recorder()
    # Simulate a very short recording
    rec._proc = MagicMock()
    rec._proc.poll.return_value = 0  # already finished

    rec_dir = setup_db / "recordings" / "1"
    rec_dir.mkdir(parents=True)
    fake_file = rec_dir / "short.mp4"
    fake_file.write_bytes(b"x" * 100)

    rec._current_file = fake_file
    rec._start_time = datetime.now() - timedelta(seconds=1)  # 1 second ago
    rec._current_meta = {
        "player_id": 1, "training_id": 101, "training_name": "T",
        "step_idx": 0, "step_name": "S", "filename": "1/short.mp4",
    }
    rec._log_file = None

    result = rec.stop()
    assert result is None  # discarded
    assert not fake_file.exists()  # file deleted
    assert db.get_recordings_meta(player_id=1) == []  # not saved to DB
