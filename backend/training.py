"""Training scenario runner + file-based storage."""

import asyncio
import json
import logging
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

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, scenario: dict, robot, broadcast: Callable):
        if self.running:
            self.stop(robot)
        self._stopped = False
        self._task = asyncio.create_task(self._run(scenario, robot, broadcast))

    def stop(self, robot):
        self._stopped = True
        if self._task and not self._task.done():
            self._task.cancel()
        robot.stop_drill()
        asyncio.create_task(robot.stop())

    async def _run(self, scenario: dict, robot, broadcast: Callable):
        steps = scenario.get("steps", [])
        countdown_sec = scenario.get("countdown_sec", 20)
        total_steps = len(steps)

        try:
            # ── Countdown ────────────────────────────────────────
            first_drill = self._resolve_drill(steps[0]) if steps else None
            if first_drill and countdown_sec >= 5:
                # rozgrzewka silników — set_ball 5s przed startem
                warmup_at = max(0, countdown_sec - 5)
                for sec in range(countdown_sec, 0, -1):
                    if self._stopped:
                        return
                    broadcast("training_countdown", {"sec": sec, "total": countdown_sec})
                    if sec == countdown_sec - warmup_at:
                        # start silników
                        b = first_drill["balls"][0]
                        await robot.set_ball(
                            b["top_speed"], b["bot_speed"],
                            b["oscillation"], b["height"], b["rotation"],
                            b.get("wait_ms", 1000))
                    if sec <= 5:
                        audio.play("beep" if sec > 3 else "beep_high")
                    await asyncio.sleep(1)

            # ── Steps ────────────────────────────────────────────
            for step_idx, step in enumerate(steps):
                if self._stopped:
                    return

                drill = self._resolve_drill(step)
                if not drill:
                    logger.warning("Drill %s not found, skipping", step.get("drill_id"))
                    continue

                drill_name = step.get("drill_name") or drill.get("name", "?")
                count = step.get("count", 60)
                percent = step.get("percent", 100)
                pause_sec = step.get("pause_after_sec", 30)

                # START
                broadcast("training_step", {
                    "step": step_idx + 1, "total": total_steps,
                    "drill_name": drill_name, "phase": "drill",
                    "count": count, "percent": percent,
                })
                audio.play("start")
                await asyncio.sleep(1.5)  # daj czas na "Start" voice

                # RUN DRILL
                drill_done = asyncio.Event()

                original_emit = robot._emit
                def _intercept_emit(event_type, data):
                    original_emit(event_type, data)
                    if event_type == "drill_progress":
                        broadcast("training_drill_progress", {
                            **data,
                            "step": step_idx + 1, "total_steps": total_steps,
                            "drill_name": drill_name,
                        })
                    elif event_type == "drill_ended":
                        drill_done.set()

                robot._emit = _intercept_emit
                await robot.run_drill(drill["balls"], repeat=0, count=count, percent=percent)

                try:
                    await asyncio.wait_for(drill_done.wait(), timeout=count * 30)
                except asyncio.TimeoutError:
                    logger.warning("Drill timeout after %ds", count * 30)

                robot._emit = original_emit

                if self._stopped:
                    return

                # END
                audio.play("end")
                await robot.stop()
                await asyncio.sleep(1)

                # PAUSE (jeśli nie ostatni step)
                if step_idx < total_steps - 1 and pause_sec > 0:
                    next_drill = self._resolve_drill(steps[step_idx + 1])
                    warmup_at = max(0, pause_sec - 5)

                    for sec in range(pause_sec, 0, -1):
                        if self._stopped:
                            return
                        broadcast("training_pause", {
                            "sec": sec, "total": pause_sec,
                            "step": step_idx + 1, "total_steps": total_steps,
                            "next_drill": steps[step_idx + 1].get("drill_name", ""),
                        })
                        # rozgrzewka silników 5s przed końcem pauzy
                        if sec == 5 and next_drill:
                            b = next_drill["balls"][0]
                            await robot.set_ball(
                                b["top_speed"], b["bot_speed"],
                                b["oscillation"], b["height"], b["rotation"],
                                b.get("wait_ms", 1000))
                        if sec <= 3:
                            audio.play("beep_high")
                        await asyncio.sleep(1)

            # ── Done ─────────────────────────────────────────────
            audio.play("training_ended")
            broadcast("training_ended", {})

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Training runner error: %s", e)
            broadcast("training_ended", {"error": str(e)})
        finally:
            await robot.stop()

    def _resolve_drill(self, step: dict) -> dict | None:
        drill_id = step.get("drill_id")
        if drill_id:
            return drills.get_drill(drill_id)
        return None
