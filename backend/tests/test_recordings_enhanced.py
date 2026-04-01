"""Tests for enhanced recording features: drill_id/exercise_id, compare, cascade delete, info, ZIP."""

import io
import zipfile
import pytest

import db
import recordings


@pytest.fixture()
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(recordings, "RECORDINGS_DIR", tmp_path / "recordings")
    db.init()
    return tmp_path


def _create_player(name="Test"):
    return db.create_player(name)


def _create_recording_file(tmp_path, player_id, filename):
    """Create a fake recording file on disk."""
    rec_dir = tmp_path / "recordings" / str(player_id)
    rec_dir.mkdir(parents=True, exist_ok=True)
    filepath = rec_dir / filename
    filepath.write_bytes(b"fake video data " * 100)
    return filepath


# ── drill_id/exercise_id in metadata ──────────────────────────────────────

def test_save_recording_meta_with_drill_id(setup_db):
    db.save_recording_meta(1, 101, "Training A", 0, "FH Topspin",
                           "1/rec.mp4", 60, 5000, drill_id=7)
    recs = db.get_recordings_meta(player_id=1)
    assert len(recs) == 1
    assert recs[0]["drill_id"] == 7
    assert recs[0]["exercise_id"] is None


def test_save_recording_meta_with_exercise_id(setup_db):
    db.save_recording_meta(1, 101, "Training A", 1, "Jogging",
                           "1/rec2.mp4", 30, 3000, exercise_id=42)
    recs = db.get_recordings_meta(player_id=1)
    assert len(recs) == 1
    assert recs[0]["exercise_id"] == 42
    assert recs[0]["drill_id"] is None


def test_save_recording_meta_without_ids(setup_db):
    """Backward compat — no drill_id/exercise_id."""
    db.save_recording_meta(1, 101, "Training A", 0, "Step",
                           "1/rec3.mp4", 60, 5000)
    recs = db.get_recordings_meta(player_id=1)
    assert recs[0]["drill_id"] is None
    assert recs[0]["exercise_id"] is None


# ── Compare by drill_id/exercise_id ───────────────────────────────────────

def test_compare_by_drill_id(setup_db):
    db.save_recording_meta(1, 101, "Training A", 0, "FH", "1/a.mp4", 60, 5000, drill_id=7)
    db.save_recording_meta(2, 102, "Training B", 2, "FH", "2/b.mp4", 60, 5000, drill_id=7)
    db.save_recording_meta(1, 103, "Training C", 0, "BH", "1/c.mp4", 60, 5000, drill_id=8)

    results = db.get_comparable_recordings(drill_id=7)
    assert len(results) == 2
    filenames = {r["filename"] for r in results}
    assert "1/a.mp4" in filenames
    assert "2/b.mp4" in filenames


def test_compare_by_exercise_id(setup_db):
    db.save_recording_meta(1, 101, "T1", 1, "Jog", "1/e1.mp4", 30, 3000, exercise_id=42)
    db.save_recording_meta(2, 101, "T1", 1, "Jog", "2/e2.mp4", 30, 3000, exercise_id=42)
    db.save_recording_meta(1, 101, "T1", 2, "Arms", "1/e3.mp4", 30, 3000, exercise_id=43)

    results = db.get_comparable_recordings(exercise_id=42)
    assert len(results) == 2


def test_compare_exclude_filename(setup_db):
    db.save_recording_meta(1, 101, "T1", 0, "FH", "1/a.mp4", 60, 5000, drill_id=7)
    db.save_recording_meta(2, 102, "T2", 0, "FH", "2/b.mp4", 60, 5000, drill_id=7)

    results = db.get_comparable_recordings(drill_id=7, exclude_filename="1/a.mp4")
    assert len(results) == 1
    assert results[0]["filename"] == "2/b.mp4"


def test_compare_fallback_training_step(setup_db):
    """Old recordings without drill_id — fallback to training_id+step_idx."""
    db.save_recording_meta(1, 101, "T1", 0, "FH", "1/old.mp4", 60, 5000)
    db.save_recording_meta(2, 101, "T1", 0, "FH", "2/old2.mp4", 60, 5000)

    results = db.get_comparable_recordings(training_id=101, step_idx=0)
    assert len(results) == 2


# ── Recording stats ───────────────────────────────────────────────────────

def test_recordings_stats_by_player(setup_db):
    db.save_recording_meta(1, 101, "T1", 0, "FH", "1/a.mp4", 60, 5000, drill_id=7)
    db.save_recording_meta(1, 101, "T1", 1, "BH", "1/b.mp4", 60, 3000, drill_id=8)
    db.save_recording_meta(2, 101, "T1", 0, "FH", "2/c.mp4", 60, 4000, drill_id=7)

    stats = db.get_recordings_stats(player_id=1)
    assert stats["count"] == 2
    assert stats["total_size"] == 8000
    assert set(stats["filenames"]) == {"1/a.mp4", "1/b.mp4"}


def test_recordings_stats_empty(setup_db):
    stats = db.get_recordings_stats(player_id=999)
    assert stats["count"] == 0
    assert stats["total_size"] == 0


# ── Cascade delete player ────────────────────────────────────────────────

def test_delete_player_cascade(setup_db):
    tmp_path = setup_db
    p = _create_player("Alice")
    pid = p["id"]

    # Create history, recordings, favorites, landings
    hid = db.record_training_run(101, pid, 120, "completed", 3, 3)
    db.save_recording_meta(pid, 101, "T1", 0, "FH", f"{pid}/a.mp4", 60, 5000, drill_id=7)
    db.save_recording_meta(pid, 101, "T1", 1, "BH", f"{pid}/b.mp4", 60, 3000, drill_id=8)
    db.add_favorite(pid, "drill", 7)
    db.save_ball_landing(pid, 7, 0.5, 0.5)

    # Create files on disk
    _create_recording_file(tmp_path, pid, "a.mp4")
    _create_recording_file(tmp_path, pid, "b.mp4")

    rec_files, voice_files = db.delete_player_cascade(pid)
    assert len(rec_files) == 2
    assert f"{pid}/a.mp4" in rec_files

    # Verify all data removed
    assert db.get_player(pid) is None
    assert db.get_training_history(player_id=pid) == []
    assert db.get_recordings_meta(player_id=pid) == []
    assert db.get_favorites(pid) == []
    assert db.get_ball_landings(7, player_id=pid) == []


def test_delete_player_cascade_no_data(setup_db):
    p = _create_player("Bob")
    rec_files, voice_files = db.delete_player_cascade(p["id"])
    assert rec_files == []
    assert voice_files == []
    assert db.get_player(p["id"]) is None


# ── Cascade delete history ────────────────────────────────────────────────

def test_delete_history_cascade(setup_db):
    tmp_path = setup_db
    p = _create_player("Charlie")
    pid = p["id"]

    hid = db.record_training_run(101, pid, 60, "completed", 1, 1)
    h = db.get_history_entry(hid)
    # Save recording matching session time
    db.save_recording_meta(pid, 101, "T1", 0, "FH", f"{pid}/c.mp4", 60, 5000, drill_id=7)

    _create_recording_file(tmp_path, pid, "c.mp4")

    filenames = db.delete_history_cascade(hid)
    assert len(filenames) == 1
    assert db.get_history_entry(hid) is None


def test_delete_history_cascade_nonexistent(setup_db):
    filenames = db.delete_history_cascade(9999)
    assert filenames == []


# ── ZIP creation ──────────────────────────────────────────────────────────

def test_create_zip(setup_db):
    tmp_path = setup_db
    _create_recording_file(tmp_path, 1, "test1.mp4")
    _create_recording_file(tmp_path, 1, "test2.mp4")

    buf = recordings.create_zip(["1/test1.mp4", "1/test2.mp4"])
    assert isinstance(buf, io.BytesIO)

    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert "1_test1.mp4" in names
        assert "1_test2.mp4" in names


def test_create_zip_missing_file(setup_db):
    """ZIP should skip missing files."""
    tmp_path = setup_db
    _create_recording_file(tmp_path, 1, "exists.mp4")

    buf = recordings.create_zip(["1/exists.mp4", "1/missing.mp4"])
    with zipfile.ZipFile(buf) as zf:
        assert len(zf.namelist()) == 1


# ── Delete files helper ──────────────────────────────────────────────────

def test_delete_files(setup_db):
    tmp_path = setup_db
    f1 = _create_recording_file(tmp_path, 1, "del1.mp4")
    f2 = _create_recording_file(tmp_path, 1, "del2.mp4")
    assert f1.exists()

    recordings.delete_files(["1/del1.mp4", "1/del2.mp4"])
    assert not f1.exists()
    assert not f2.exists()


def test_delete_files_missing(setup_db):
    """Should not raise on missing files."""
    recordings.delete_files(["1/nope.mp4"])
