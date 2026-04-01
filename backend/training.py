"""Training scenario runner + SQLite storage with defaults and history."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional

import audio
import db
import drills
import exercises
import recordings

logger = logging.getLogger(__name__)

DEFAULTS_FILE = Path(__file__).parent / "trainings_default.json"

# ── Default trainings ────────────────────────────────────────────────────────

def _load_defaults() -> list:
    try:
        data = json.loads(DEFAULTS_FILE.read_text())
    except Exception:
        return []
    result = []
    for fi, folder in enumerate(data.get("folders", [])):
        folder_id = (fi + 1) * 100
        for ti, training in enumerate(folder.get("trainings", [])):
            training["id"] = folder_id + ti + 1
            training["folder"] = folder["name"]
            training["folder_icon"] = folder.get("icon", "")
            training["readonly"] = True
            result.append(training)
    return result


# ── Training CRUD (defaults + user) ──────────────────────────────────────────

def get_trainings() -> list:
    defaults = _load_defaults()
    user = db.get_user_trainings()
    for t in user:
        t.setdefault("readonly", False)
    return defaults + user


def get_training(training_id: int) -> dict | None:
    for t in get_trainings():
        if t["id"] == training_id:
            return t
    return None


def save_training(data: dict) -> int:
    existing = get_training(data.get("id", -1))
    if existing and existing.get("readonly"):
        raise ValueError("Cannot modify readonly training")
    return db.save_user_training(data)


def duplicate_training(training_id: int) -> dict | None:
    src = get_training(training_id)
    if not src:
        return None
    copy = {k: v for k, v in src.items() if k not in ("id", "readonly", "folder", "folder_icon")}
    copy["name"] = f"{src['name']} (kopia)"
    tid = db.save_user_training(copy)
    return db.get_user_training(tid)


def delete_training(training_id: int):
    existing = get_training(training_id)
    if existing and existing.get("readonly"):
        raise ValueError("Cannot delete readonly training")
    db.delete_user_training(training_id)


# ── History ──────────────────────────────────────────────────────────────────

def record_run(training_id, player_id: int | None, elapsed_sec: int,
               status: str, steps_completed: int, steps_total: int,
               steps_skipped: list[int] | None = None,
               step_notes: list[dict] | None = None,
               solo_drill_id: int | None = None,
               solo_exercise_id: int | None = None) -> int:
    return db.record_training_run(training_id, player_id, elapsed_sec, status,
                                  steps_completed, steps_total, steps_skipped, step_notes,
                                  solo_drill_id=solo_drill_id, solo_exercise_id=solo_exercise_id)


def get_history(training_id: int | None = None, player_id: int | None = None,
                limit: int | None = None, offset: int = 0) -> list:
    return db.get_training_history(training_id=training_id, player_id=player_id,
                                   limit=limit, offset=offset)


def update_session_comment(history_id: int, comment: str):
    db.update_session_comment(history_id, comment)


# ── Runner ───────────────────────────────────────────────────────────────────

class TrainingRunner:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stopped = False
        self._paused = False
        self._skip = False
        self._robot = None
        self._recorder = recordings.Recorder()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, scenario: dict, robot, broadcast: Callable,
              player_id: int | None = None, record: bool = False,
              record_type: str = "all",
              start_from_step: int = 0,
              solo_drill_id: int | None = None,
              solo_exercise_id: int | None = None):
        if self.running:
            self.stop()
        self._stopped = False
        self._paused = False
        self._skip = False
        self._robot = robot
        self._broadcast = broadcast
        self._player_id = player_id
        self._record = record and player_id is not None
        self._record_type = record_type
        self._steps_completed = start_from_step
        self._steps_skipped = []
        self._step_notes = []
        self._percent_override = None
        self._start_from_step = start_from_step
        self._scenario = scenario
        self._solo_drill_id = solo_drill_id
        self._solo_exercise_id = solo_exercise_id
        self._task = asyncio.create_task(self._run(scenario, robot, broadcast))

    def stop(self):
        self._stopped = True
        self._paused = False
        self._skip = False
        if self._recorder.recording:
            self._recorder.stop()
        if self._task and not self._task.done():
            self._task.cancel()
        if self._robot:
            self._robot.stop_drill()
            asyncio.ensure_future(self._robot.stop())
        audio.play("training_stopped")

    def pause(self):
        self._paused = True
        if self._robot:
            self._robot.stop_drill()
            asyncio.ensure_future(self._robot.stop())
        audio.play("training_paused")

    def resume(self):
        self._paused = False
        audio.play("training_resumed")

    def skip(self):
        self._skip = True

    def add_note(self, step_idx: int, note: str):
        self._step_notes.append({"step": step_idx, "note": note})

    def set_next_percent(self, percent: int):
        self._percent_override = max(50, min(150, percent))

    def _consume_skip(self) -> bool:
        if self._skip:
            self._skip = False
            return True
        return False

    async def _wait_unpaused(self):
        while self._paused and not self._stopped:
            await asyncio.sleep(0.5)

    def _start_recording(self, scenario: dict, step_idx: int, step_name: str,
                         drill_id: int | None = None, exercise_id: int | None = None):
        if self._record and self._player_id:
            self._recorder.start(
                self._player_id,
                scenario.get("id", 0),
                scenario.get("name", ""),
                step_idx,
                step_name,
                drill_id=drill_id,
                exercise_id=exercise_id,
            )

    def _stop_recording(self):
        if self._recorder.recording:
            self._recorder.stop()

    async def _run(self, scenario: dict, robot, broadcast: Callable):
        steps = scenario.get("steps", [])
        countdown_sec = scenario.get("countdown_sec", 5)
        total_steps = len(steps)
        start_time = time.monotonic()

        try:
            # ── Countdown ────────────────────────────────────────
            first_step_idx = self._start_from_step
            first_drill = self._resolve_drill(steps[first_step_idx]) if steps and first_step_idx < len(steps) else None

            audio.play("training_starting")
            await asyncio.sleep(2)

            broadcast("training_info", {
                "name": scenario.get("name", ""),
                "total_steps": total_steps,
                "phase": "countdown",
            })

            for sec in range(countdown_sec, 0, -1):
                if self._stopped: return
                await self._wait_unpaused()
                broadcast("training_countdown", {"sec": sec, "total": countdown_sec})
                if sec == 5 and first_drill:
                    b = first_drill["balls"][0]
                    await robot.set_ball(b["top_speed"], b["bot_speed"],
                                        b["oscillation"], b["height"], b["rotation"],
                                        b.get("wait_ms", 1000))
                if sec <= 5:
                    audio.play("beep" if sec > 3 else "beep_high")
                await asyncio.sleep(1)

            # ── Steps ────────────────────────────────────────────
            for step_idx, step in enumerate(steps):
                if step_idx < first_step_idx:
                    continue
                if self._stopped: return
                await self._wait_unpaused()

                is_exercise = bool(step.get("exercise_id"))
                if is_exercise:
                    await self._run_exercise_step(step_idx, step, steps, total_steps, broadcast, scenario)
                    self._steps_completed = step_idx + 1
                    continue

                drill = self._resolve_drill(step)
                if not drill:
                    logger.warning("Drill %s not found, skipping", step.get("drill_id"))
                    continue

                drill_name = step.get("drill_name") or drill.get("name", "?")
                count = step.get("count", 60)
                percent = self._percent_override or step.get("percent", 100)
                self._percent_override = None
                pause_sec = step.get("pause_after_sec", 30)

                remaining_balls = sum(s.get("count", 60) for s in steps[step_idx:] if not s.get("exercise_id"))
                avg_wait = 1.5
                est_remaining = int(remaining_balls * avg_wait + sum(s.get("pause_after_sec", 30) for s in steps[step_idx+1:]))

                self._start_recording(scenario, step_idx, drill_name,
                                     drill_id=step.get("drill_id"))

                broadcast("training_step", {
                    "step": step_idx + 1, "total": total_steps,
                    "drill_name": drill_name, "phase": "drill",
                    "count": count, "percent": percent,
                    "balls": drill["balls"],
                    "completed_steps": step_idx,
                    "est_remaining_sec": est_remaining,
                })
                audio.play("drill_starting")
                await asyncio.sleep(1.5)

                if self._stopped: return

                drill_done = asyncio.Event()
                original_emit = robot._emit

                def _make_interceptor(si, dn):
                    def _intercept(event_type, data):
                        original_emit(event_type, data)
                        if event_type == "drill_progress":
                            broadcast("training_drill_progress", {
                                **data, "step": si + 1, "total_steps": total_steps,
                                "drill_name": dn, "est_remaining_sec": est_remaining,
                            })
                        elif event_type == "drill_ended":
                            drill_done.set()
                    return _intercept

                robot._emit = _make_interceptor(step_idx, drill_name)
                await robot.run_drill(drill["balls"], repeat=0, count=count, percent=percent)

                timeout = max(300, count * 30)
                elapsed = 0.0
                while not drill_done.is_set() and not self._stopped and not self._skip:
                    await asyncio.sleep(0.2)
                    elapsed += 0.2
                    if elapsed > timeout:
                        logger.warning("Drill timeout")
                        break
                skipped = self._consume_skip()
                if skipped:
                    robot.stop_drill()
                    await robot.stop()
                    self._steps_skipped.append(step_idx)

                robot._emit = original_emit
                self._stop_recording()

                if self._stopped: return

                audio.play("drill_finished")
                await robot.stop()
                broadcast("training_step_done", {
                    "step": step_idx + 1, "total": total_steps,
                    "drill_name": drill_name,
                })
                self._steps_completed = step_idx + 1
                await asyncio.sleep(1)

                if step_idx < total_steps - 1 and pause_sec > 0 and not skipped:
                    next_step = steps[step_idx + 1]
                    next_drill = self._resolve_drill(next_step)
                    next_name = next_step.get("drill_name") or next_step.get("exercise_name") or (next_drill.get("name", "?") if next_drill else "?")

                    for sec in range(pause_sec, 0, -1):
                        if self._stopped: return
                        if self._consume_skip(): break
                        await self._wait_unpaused()
                        broadcast("training_pause", {
                            "sec": sec, "total": pause_sec,
                            "step": step_idx + 1, "total_steps": total_steps,
                            "next_drill": next_name,
                        })
                        if sec == 5 and next_drill:
                            b = next_drill["balls"][0]
                            await robot.set_ball(b["top_speed"], b["bot_speed"],
                                                b["oscillation"], b["height"], b["rotation"],
                                                b.get("wait_ms", 1000))
                        if sec <= 3:
                            audio.play("beep_high")
                        await asyncio.sleep(1)

            # ── Done ─────────────────────────────────────────────
            elapsed_sec = int(time.monotonic() - start_time)
            audio.play("training_complete")
            history_id = record_run(
                scenario.get("id"), self._player_id, elapsed_sec,
                "completed", self._steps_completed, total_steps,
                self._steps_skipped, self._step_notes,
                solo_drill_id=self._solo_drill_id, solo_exercise_id=self._solo_exercise_id,
            )
            broadcast("training_ended", {"elapsed_sec": elapsed_sec, "history_id": history_id})

        except asyncio.CancelledError:
            elapsed_sec = int(time.monotonic() - start_time)
            history_id = record_run(
                scenario.get("id"), self._player_id, elapsed_sec,
                "stopped", self._steps_completed, total_steps,
                self._steps_skipped, self._step_notes,
                solo_drill_id=self._solo_drill_id, solo_exercise_id=self._solo_exercise_id,
            )
            broadcast("training_ended", {"elapsed_sec": elapsed_sec, "history_id": history_id, "status": "stopped"})
        except Exception as e:
            logger.error("Training runner error: %s", e)
            elapsed_sec = int(time.monotonic() - start_time)
            broadcast("training_ended", {"error": str(e)})
            record_run(
                scenario.get("id"), self._player_id, elapsed_sec,
                "error", self._steps_completed, total_steps,
                self._steps_skipped, self._step_notes,
                solo_drill_id=self._solo_drill_id, solo_exercise_id=self._solo_exercise_id,
            )
        finally:
            self._stop_recording()
            try:
                await robot.stop()
            except Exception:
                pass

    async def _run_exercise_step(self, step_idx, step, steps, total_steps, broadcast, scenario):
        ex = exercises.get_exercise(step["exercise_id"])
        if not ex:
            logger.warning("Exercise %s not found, skipping", step.get("exercise_id"))
            return
        name = step.get("exercise_name") or ex.get("name", "?")
        duration = step.get("duration_sec") or ex.get("duration_sec", 60)
        pause_sec = step.get("pause_after_sec", 30)

        self._start_recording(scenario, step_idx, name,
                             exercise_id=step.get("exercise_id"))

        broadcast("training_step", {
            "step": step_idx + 1, "total": total_steps,
            "drill_name": f"🏋 {name}", "phase": "exercise",
            "exercise": ex, "duration_sec": duration,
            "completed_steps": step_idx,
        })
        audio.play("beep")

        skipped = False
        for sec in range(duration, 0, -1):
            if self._stopped: return
            if self._consume_skip():
                self._steps_skipped.append(step_idx)
                skipped = True
                break
            await self._wait_unpaused()
            broadcast("training_exercise_progress", {
                "step": step_idx + 1, "total_steps": total_steps,
                "exercise_name": name, "sec": sec, "total_sec": duration,
                "exercise_id": ex.get("id"),
                "description": ex.get("description", ""),
            })
            if sec <= 3:
                audio.play("beep_high")
            await asyncio.sleep(1)

        self._stop_recording()

        audio.play("drill_finished")
        broadcast("training_step_done", {
            "step": step_idx + 1, "total": total_steps,
            "drill_name": f"🏋 {name}",
        })

        if step_idx < total_steps - 1 and pause_sec > 0 and not skipped:
            for sec in range(pause_sec, 0, -1):
                if self._stopped: return
                if self._consume_skip(): break
                await self._wait_unpaused()
                broadcast("training_pause", {
                    "sec": sec, "total": pause_sec,
                    "step": step_idx + 1, "total_steps": total_steps,
                    "next_drill": steps[step_idx + 1].get("drill_name") or steps[step_idx + 1].get("exercise_name", ""),
                })
                if sec <= 3:
                    audio.play("beep_high")
                await asyncio.sleep(1)

    def _resolve_drill(self, step: dict) -> dict | None:
        drill_id = step.get("drill_id")
        if drill_id:
            return drills.get_drill(drill_id)
        return None
