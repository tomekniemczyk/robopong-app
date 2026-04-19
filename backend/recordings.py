"""Camera recording per drill/exercise step.

Uses ffmpeg to capture MJPEG stream from uStreamer (port 8081) into MP4 files.
Each drill/exercise step gets its own recording file.
"""

import io
import logging
import re
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

import db

logger = logging.getLogger(__name__)

RECORDINGS_DIR = Path(__file__).parent / "recordings"
# uStreamer MJPEG endpoint (port 8081). Path /stream returns multipart
# JPEG frames; root / returns HTML index — ffmpeg needs the stream path.
MOTION_STREAM = "http://localhost:8081/stream"


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
              step_idx: int, step_name: str,
              drill_id: int | None = None, exercise_id: int | None = None,
              training_history_id: int | None = None,
              max_duration_sec: int = 600):
        if self.recording:
            self.stop()

        player_dir = _ensure_dir(player_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _safe_filename(step_name)
        filename = f"{ts}_s{step_idx:02d}_{safe_name}.mp4"
        filepath = player_dir / filename

        self._is_ondemand = False
        self._custom_name = ""
        self._start_ffmpeg(filepath, player_id, filename, max_duration_sec, {
            "player_id": player_id,
            "training_id": training_id,
            "training_name": training_name,
            "step_idx": step_idx,
            "step_name": step_name,
            "drill_id": drill_id,
            "exercise_id": exercise_id,
            "training_history_id": training_history_id,
        })

    def start_ondemand(self, player_id: int, custom_name: str, duration_sec: int):
        if self.recording:
            self.stop()

        player_dir = _ensure_dir(player_id)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = _safe_filename(custom_name)
        filename = f"{ts}_{safe_name}.mp4"
        filepath = player_dir / filename

        self._is_ondemand = True
        self._custom_name = custom_name
        self._start_ffmpeg(filepath, player_id, filename, duration_sec, {
            "player_id": player_id,
            "training_id": None,
            "training_name": "On-demand",
            "step_idx": 0,
            "step_name": custom_name,
            "drill_id": None,
            "exercise_id": None,
            "training_history_id": None,
        })

    def _start_ffmpeg(self, filepath: Path, player_id: int, filename: str,
                      max_duration_sec: int, meta: dict):
        try:
            log_path = filepath.with_suffix(".log")
            self._log_file = open(log_path, "w")
            self._proc = subprocess.Popen(
                [
                    "ffmpeg", "-y",
                    "-i", MOTION_STREAM,
                    "-vf", "setpts=N/15/TB,fps=15",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-crf", "18",
                    "-movflags", "+faststart",
                    "-t", str(max_duration_sec),
                    str(filepath),
                ],
                stdin=subprocess.PIPE,
                stdout=self._log_file,
                stderr=self._log_file,
            )
            self._current_file = filepath
            self._start_time = datetime.now()
            self._current_meta = {
                **meta,
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

    def stop(self, skipped: bool = False) -> dict | None:
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
            is_od = getattr(self, '_is_ondemand', False)
            min_duration = 1 if is_od else (30 if skipped else 3)
            if duration < min_duration:
                logger.info("Recording discarded (%.1fs < %ds%s): %s",
                            duration, min_duration, ", skipped" if skipped else "", self._current_file)
                self._current_file.unlink(missing_ok=True)
                log = self._current_file.with_suffix(".log")
                log.unlink(missing_ok=True)
            else:
                self._current_meta["duration_sec"] = int(duration)
                self._current_meta["size_bytes"] = self._current_file.stat().st_size
                meta = self._current_meta

                db.save_recording_meta(
                    meta["player_id"], meta["training_id"], meta["training_name"],
                    meta["step_idx"], meta["step_name"], meta["filename"],
                    meta["duration_sec"], meta["size_bytes"],
                    drill_id=meta.get("drill_id"), exercise_id=meta.get("exercise_id"),
                    training_history_id=meta.get("training_history_id"),
                    is_ondemand=1 if is_od else 0,
                    custom_name=getattr(self, '_custom_name', ''),
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

def get_recordings(player_id: int | None = None, is_ondemand: int | None = None) -> list:
    return db.get_recordings_meta(player_id=player_id, is_ondemand=is_ondemand)


def get_recording_path(filename: str) -> Path | None:
    path = RECORDINGS_DIR / filename
    if path.exists() and path.is_relative_to(RECORDINGS_DIR):
        return path
    return None


def delete_recording(filename: str) -> bool:
    path = RECORDINGS_DIR / filename
    if path.exists() and path.is_relative_to(RECORDINGS_DIR):
        path.unlink()
        log = path.with_suffix(".log")
        if log.exists():
            log.unlink()
    db.delete_recording_meta(filename)
    return True


def delete_files(filenames: list[str]):
    """Delete recording files from disk (meta already removed by db cascade)."""
    for fn in filenames:
        path = RECORDINGS_DIR / fn
        if path.exists() and path.is_relative_to(RECORDINGS_DIR):
            path.unlink()
            log = path.with_suffix(".log")
            if log.exists():
                log.unlink()


def create_zip(filenames: list[str]) -> io.BytesIO:
    """Create a ZIP archive of recording files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as zf:
        for fn in filenames:
            path = RECORDINGS_DIR / fn
            if path.exists() and path.is_relative_to(RECORDINGS_DIR):
                zf.write(path, fn.replace('/', '_'))
    buf.seek(0)
    return buf
