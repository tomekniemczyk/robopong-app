"""Camera recording per drill/exercise step.

Uses ffmpeg to capture from motion MJPEG stream (port 8081) into MP4 files.
Each drill/exercise step gets its own recording file.
"""

import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

import db

logger = logging.getLogger(__name__)

RECORDINGS_DIR = Path(__file__).parent / "recordings"
MOTION_STREAM = "http://localhost:8081"


def _ensure_dir(player_id: int):
    d = RECORDINGS_DIR / str(player_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(name: str) -> str:
    return re.sub(r'[^\w\-]', '_', name)[:50]


class Recorder:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._log_file = None
        self._current_file: Path | None = None
        self._current_meta: dict | None = None
        self._start_time: datetime | None = None

    @property
    def recording(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, player_id: int, training_id: int, training_name: str,
              step_idx: int, step_name: str):
        if self.recording:
            self.stop()

        player_dir = _ensure_dir(player_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _safe_filename(step_name)
        filename = f"{ts}_s{step_idx:02d}_{safe_name}.mp4"
        filepath = player_dir / filename

        try:
            log_path = filepath.with_suffix(".log")
            self._log_file = open(log_path, "w")
            self._proc = subprocess.Popen(
                [
                    "ffmpeg", "-y",
                    "-use_wallclock_as_timestamps", "1",
                    "-i", MOTION_STREAM,
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "18",
                    "-vsync", "vfr",
                    "-r", "15",
                    "-t", "600",  # max 10 min safety
                    str(filepath),
                ],
                stdin=subprocess.PIPE,
                stdout=self._log_file,
                stderr=self._log_file,
            )
            self._current_file = filepath
            self._start_time = datetime.now()
            self._current_meta = {
                "player_id": player_id,
                "training_id": training_id,
                "training_name": training_name,
                "step_idx": step_idx,
                "step_name": step_name,
                "filename": f"{player_id}/{filename}",
                "started_at": self._start_time.isoformat(),
            }
            logger.info("Recording started: %s", filepath)
        except FileNotFoundError:
            logger.warning("ffmpeg not found — recording disabled")
            self._proc = None
        except Exception as e:
            logger.error("Failed to start recording: %s", e)
            self._proc = None

    def stop(self) -> dict | None:
        if not self._proc:
            return None

        meta = None
        try:
            if self._proc.poll() is None:
                self._proc.stdin.write(b"q")
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()

        if self._current_file and self._current_file.exists():
            duration = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            self._current_meta["duration_sec"] = int(duration)
            self._current_meta["size_bytes"] = self._current_file.stat().st_size
            meta = self._current_meta

            db.save_recording_meta(
                meta["player_id"], meta["training_id"], meta["training_name"],
                meta["step_idx"], meta["step_name"], meta["filename"],
                meta["duration_sec"], meta["size_bytes"],
            )
            logger.info("Recording saved: %s (%.0fs)", self._current_file, duration)
        else:
            logger.warning("Recording file not found after stop")

        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
        self._proc = None
        self._log_file = None
        self._current_file = None
        self._current_meta = None
        self._start_time = None
        return meta


# ── Query API ────────────────────────────────────────────────────────────────

def get_recordings(player_id: int | None = None) -> list:
    return db.get_recordings_meta(player_id=player_id)


def get_recording_path(filename: str) -> Path | None:
    path = RECORDINGS_DIR / filename
    if path.exists() and path.is_relative_to(RECORDINGS_DIR):
        return path
    return None


def delete_recording(filename: str) -> bool:
    path = RECORDINGS_DIR / filename
    if path.exists() and path.is_relative_to(RECORDINGS_DIR):
        path.unlink()
    db.delete_recording_meta(filename)
    return True
