"""Training scenario runner + file-based storage."""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional

import audio
import drills

logger = logging.getLogger(__name__)
TRAININGS_FILE = Path(__file__).parent / ".trainings.json"

# ── Storage ──────────────────────────────────────────────────────────────────

def _load() -> list:
    try:
        return json.loads(TRAININGS_FILE.read_text())
    except Exception:
        return []


def _save(data: list):
    TRAININGS_FILE.write_text(json.dumps(data, indent=2))


def get_trainings() -> list:
    trainings = _load()
    for i, t in enumerate(trainings):
        t.setdefault("id", i + 1)
    return trainings


def get_training(training_id: int) -> dict | None:
    for t in get_trainings():
        if t["id"] == training_id:
            return t
    return None


def save_training(data: dict) -> int:
    trainings = _load()
    if "id" in data and any(t.get("id") == data["id"] for t in trainings):
        trainings = [data if t.get("id") == data["id"] else t for t in trainings]
    else:
        data["id"] = max((t.get("id", 0) for t in trainings), default=0) + 1
        trainings.append(data)
    _save(trainings)
    return data["id"]


def delete_training(training_id: int):
    trainings = _load()
    _save([t for t in trainings if t.get("id") != training_id])


# ── Runner ───────────────────────────────────────────────────────────────────

class TrainingRunner:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stopped = False
        self._paused = False
        self._robot = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, scenario: dict, robot, broadcast: Callable):
        if self.running:
            self.stop()
        self._stopped = False
        self._paused = False
        self._robot = robot
        self._broadcast = broadcast
        self._task = asyncio.create_task(self._run(scenario, robot, broadcast))

    def stop(self):
        self._stopped = True
        self._paused = False
        if self._task and not self._task.done():
            self._task.cancel()
        if self._robot:
            self._robot.stop_drill()
            asyncio.ensure_future(self._robot.stop())

    def pause(self):
        self._paused = True
        if self._robot:
            self._robot.stop_drill()
            asyncio.ensure_future(self._robot.stop())

    def resume(self):
        self._paused = False

    async def _wait_unpaused(self):
        while self._paused and not self._stopped:
            await asyncio.sleep(0.5)

    async def _run(self, scenario: dict, robot, broadcast: Callable):
        steps = scenario.get("steps", [])
        countdown_sec = scenario.get("countdown_sec", 20)
        total_steps = len(steps)
        start_time = time.monotonic()

        try:
            # ── Countdown ────────────────────────────────────────
            first_drill = self._resolve_drill(steps[0]) if steps else None

            audio.play("training_starting")
            await asyncio.sleep(2)  # daj czas na "Training starting"

            broadcast("training_info", {
                "name": scenario.get("name", ""),
                "total_steps": total_steps,
                "phase": "countdown",
            })

            for sec in range(countdown_sec, 0, -1):
                if self._stopped: return
                await self._wait_unpaused()
                broadcast("training_countdown", {"sec": sec, "total": countdown_sec})
                # rozgrzewka 5s przed startem
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
                if self._stopped: return
                await self._wait_unpaused()

                drill = self._resolve_drill(step)
                if not drill:
                    logger.warning("Drill %s not found, skipping", step.get("drill_id"))
                    continue

                drill_name = step.get("drill_name") or drill.get("name", "?")
                count = step.get("count", 60)
                percent = step.get("percent", 100)
                pause_sec = step.get("pause_after_sec", 30)

                # Oblicz szacowany czas do końca
                remaining_balls = sum(s.get("count", 60) for s in steps[step_idx:])
                avg_wait = 1.5  # ~1.5s per ball
                est_remaining = int(remaining_balls * avg_wait + sum(s.get("pause_after_sec", 30) for s in steps[step_idx+1:]))

                # START DRILL
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

                # RUN DRILL — intercept events
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

                try:
                    await asyncio.wait_for(drill_done.wait(), timeout=max(300, count * 30))
                except asyncio.TimeoutError:
                    logger.warning("Drill timeout")

                robot._emit = original_emit

                if self._stopped: return

                # END DRILL
                audio.play("drill_finished")
                await robot.stop()
                broadcast("training_step_done", {
                    "step": step_idx + 1, "total": total_steps,
                    "drill_name": drill_name,
                })
                await asyncio.sleep(1)

                # PAUSE
                if step_idx < total_steps - 1 and pause_sec > 0:
                    next_step = steps[step_idx + 1]
                    next_drill = self._resolve_drill(next_step)
                    next_name = next_step.get("drill_name") or (next_drill.get("name", "?") if next_drill else "?")

                    for sec in range(pause_sec, 0, -1):
                        if self._stopped: return
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
            elapsed = int(time.monotonic() - start_time)
            audio.play("training_complete")
            broadcast("training_ended", {"elapsed_sec": elapsed})

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Training runner error: %s", e)
            broadcast("training_ended", {"error": str(e)})
        finally:
            try:
                await robot.stop()
            except Exception:
                pass

    def _resolve_drill(self, step: dict) -> dict | None:
        drill_id = step.get("drill_id")
        if drill_id:
            return drills.get_drill(drill_id)
        return None
