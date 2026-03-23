import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
import drills
import exercises
import training
import presets
from models import Ball, ScenarioIn, FolderIn, FolderUpdate, DrillIn, ReorderItem, DrillReorderItem
from robot import Robot


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-5s %(name)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

VERBOSE = True  # globalny przełącznik logowania — False żeby wyciszyć

def _log(msg: str, *args):
    if VERBOSE:
        logger.info(msg, *args)

def _dbg(msg: str, *args):
    if VERBOSE:
        logger.debug(msg, *args)


class _WsLogHandler(logging.Handler):
    """Broadcastuje logi przez WebSocket do przeglądarki."""

    def emit(self, record: logging.LogRecord):
        try:
            broadcast("server_log", {
                "ts": time.strftime("%H:%M:%S", time.localtime(record.created)),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            })
        except Exception:
            pass


def _install_ws_log_handler():
    handler = _WsLogHandler()
    handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(handler)


FRONTEND = Path(__file__).parent.parent / "frontend"

robot: Robot


class Role:
    CONTROLLER = "controller"
    OBSERVER   = "observer"
    PENDING    = "pending"


@dataclass
class Session:
    ws:          WebSocket
    id:          str = field(default_factory=lambda: uuid.uuid4().hex[:6])
    role:        str = Role.OBSERVER
    ip:          str = ""
    user_agent:  str = ""
    connected_at: float = field(default_factory=time.time)


sessions: Dict[WebSocket, Session] = {}


def broadcast(event_type: str, data: dict):
    msg = json.dumps({"type": event_type, **data})
    dead = []
    for ws in list(sessions):
        try:
            asyncio.create_task(ws.send_text(msg))
        except Exception:
            dead.append(ws)
    for ws in dead:
        sessions.pop(ws, None)


async def _send(ws: WebSocket, event_type: str, data: dict):
    try:
        await ws.send_text(json.dumps({"type": event_type, **data}))
    except Exception:
        pass


def _get_controller() -> "Session | None":
    return next((s for s in sessions.values() if s.role == Role.CONTROLLER), None)


def _promote_first_observer():
    if not any(s.role == Role.CONTROLLER for s in sessions.values()):
        first = next(
            (s for s in sessions.values() if s.role in (Role.OBSERVER, Role.PENDING)),
            None,
        )
        if first:
            first.role = Role.CONTROLLER
            asyncio.create_task(
                _send(first.ws, "session_role", {"role": first.role, "session_id": first.id})
            )


def _broadcast_sessions():
    lst = [{"id": s.id, "role": s.role, "ip": s.ip, "ua": s.user_agent, "since": s.connected_at}
           for s in sessions.values()]
    broadcast("sessions", {"sessions": lst})


LAST_ADDR_FILE = Path(__file__).parent / ".last_device"
CAL_FILE       = Path(__file__).parent / ".calibration.json"

# Domyślne wartości kalibracji z MSI (FillRobot: Top=80, Bot=0, h/osc/rot=128)
# Używamy bot=80 (nie 0) bo kalibracja wymaga obu silników do oceny lotu piłki.
# Zakres prędkości zmieniony na -249..249 — SpeedCAL target w MSI = Top=170 (raw 682).
DEFAULT_CAL = {"top_speed": 161, "bot_speed": 0, "oscillation": 150, "height": 183, "rotation": 150, "wait_ms": 1000}


def _load_cal(addr: str = "") -> dict:
    try:
        raw = json.loads(CAL_FILE.read_text())
        # Stary format płaski → automatyczna migracja
        if "top_speed" in raw:
            return raw
        return raw.get(addr) or raw.get("_default_") or DEFAULT_CAL.copy()
    except Exception:
        return DEFAULT_CAL.copy()


def _save_cal(data: dict, addr: str = ""):
    try:
        try:
            raw = json.loads(CAL_FILE.read_text())
            if "top_speed" in raw:
                raw = {"_default_": raw}  # migracja
        except Exception:
            raw = {}
        key = addr or "_default_"
        raw[key] = data
        raw["_default_"] = data   # zawsze aktualizuj domyślny przy zapisie
        CAL_FILE.write_text(json.dumps(raw))
    except Exception:
        pass


def _load_last_addr() -> str:
    try:
        return LAST_ADDR_FILE.read_text().strip()
    except Exception:
        return ""


def _save_last_addr(addr: str):
    try:
        LAST_ADDR_FILE.write_text(addr)
    except Exception:
        pass


async def _do_connect(addr: str) -> bool:
    if addr.startswith("USB:"):
        ok = await robot.connect_usb(addr[4:])
    else:
        ok = await robot.connect(addr)
    return ok


async def _reconnect_loop():
    while True:
        await asyncio.sleep(15)
        if sessions and not robot.is_connected:
            last = _load_last_addr()
            if last:
                logger.info("Reconnecting to %s...", last)
                await _do_connect(last)


async def _standby_loop():
    global _last_activity
    while True:
        await asyncio.sleep(30)
        if (robot.is_connected
                and _last_activity > 0
                and time.monotonic() - _last_activity > STANDBY_SECS):
            logger.info("Standby — idle for %d min", STANDBY_SECS // 60)
            await robot.stop()
            _last_activity = 0.0
            broadcast("info", {"message": "🌙 Robot w trybie standby (5 min bezczynności)"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global robot, DEFAULT_CAL
    _install_ws_log_handler()
    db.init()
    presets.init_presets()
    default = presets.get_default_preset()
    if default:
        DEFAULT_CAL = {k: default[k] for k in ("top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms")}
    robot = Robot(on_event=broadcast)
    last = _load_last_addr()
    if last:
        logger.info("Connecting to last device %s...", last)
        asyncio.create_task(_do_connect(last))
    asyncio.create_task(_reconnect_loop())
    asyncio.create_task(_standby_loop())
    yield
    if robot.is_connected:
        await robot.disconnect()


app = FastAPI(title="robopong-app", lifespan=lifespan)

_DEPLOY_TIME = time.strftime("%Y-%m-%d %H:%M:%S")

@app.get("/api/deploy-time")
def deploy_time():
    return {"deploy_time": _DEPLOY_TIME}


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ip = (ws.headers.get("x-forwarded-for") or ws.client.host or "") if ws.client else ""
    ua = ws.headers.get("user-agent", "")
    sess = Session(ws=ws, ip=ip, user_agent=ua)
    if not any(s.role == Role.CONTROLLER for s in sessions.values()):
        sess.role = Role.CONTROLLER
    sessions[ws] = sess
    _log("Browser connected — session %s (%s), total: %d", sess.id, sess.role, len(sessions))
    _broadcast_sessions()

    transport = robot.transport_type or "ble"
    await ws.send_text(json.dumps({
        "type":       "status",
        "connected":  robot.is_connected,
        "firmware":   robot.firmware,
        "device":     robot.device,
        "transport":  transport,
        "session_id": sess.id,
        "role":       sess.role,
    }))
    try:
        while True:
            raw = await ws.receive_text()
            await _handle(json.loads(raw), ws)
    except (WebSocketDisconnect, Exception):
        gone = sessions.pop(ws, None)
        _log("Browser disconnected — session %s, remaining: %d", gone.id if gone else "?", len(sessions))
        _promote_first_observer()
        _broadcast_sessions()


ROBOT_ACTIONS  = {"set_ball", "throw", "run_scenario", "run_drill", "run_training", "begin_calibration"}
STANDBY_SECS   = 5 * 60
_last_activity: float = 0.0
_training_runner = training.TrainingRunner()


async def _handle(msg: dict, ws: WebSocket):
    action = msg.get("action", "")
    sess = sessions.get(ws)
    sid = sess.id if sess else "?"
    _dbg("Received from %s: %s", sid, action)

    if action in ROBOT_ACTIONS:
        if not sess or sess.role != Role.CONTROLLER:
            _log("Blocked '%s' — session %s is not the controller", action, sid)
            await _send(ws, "error", {"message": "Nie jesteś kontrolerem robota"})
            return
        global _last_activity
        _last_activity = time.monotonic()

    if action == "scan":
        _log("Scanning BLE (%ds)...", msg.get("timeout", 8))
        devices = await robot.scan(msg.get("timeout", 8))
        _log("Scan complete — found %d devices", len(devices))
        await ws.send_text(json.dumps({"type": "scan_result", "devices": devices}))

    elif action == "connect":
        addr = msg["address"]
        _log("Connecting BLE to %s...", addr)
        ok = await robot.connect(addr)
        if ok:
            _log("Connected to %s (firmware: %d)", addr, robot.firmware)
            _save_last_addr(addr)
            _last_activity = time.monotonic()
            cal = _load_cal(addr)
            cal = _load_cal(addr)
            _log("Calibration loaded for %s: %s", addr, cal)
            broadcast("calibration_loaded", {"cal": cal})
        else:
            _log("Connection failed for %s", addr)
            await _send(ws, "error", {"message": "Nie można połączyć z robotem"})

    elif action == "disconnect":
        _save_last_addr("")
        await robot.disconnect()

    elif action == "usb_scan":
        ports = robot.usb_ports()
        await ws.send_text(json.dumps({"type": "usb_ports", "ports": ports}))

    elif action == "usb_connect":
        _log("Connecting USB to %s...", msg["port"])
        ok = await robot.connect_usb(msg["port"])
        if ok:
            addr = f"USB:{msg['port']}"
            _log("Connected USB: %s", addr)
            _save_last_addr(addr)
            _last_activity = time.monotonic()
            cal = _load_cal(addr)
            _log("Calibration loaded for %s: %s", addr, cal)
            broadcast("calibration_loaded", {"cal": cal})

    elif action == "usb_disconnect":
        _save_last_addr("")
        await robot.disconnect()

    elif action == "set_ball":
        b = msg["ball"]
        _log("Set ball: top=%s bot=%s osc=%s height=%s rot=%s wait=%sms",
             b["top_speed"], b["bot_speed"], b["oscillation"], b["height"], b["rotation"], b.get("wait_ms", 1500))
        await robot.set_ball(
            b["top_speed"], b["bot_speed"],
            b["oscillation"], b["height"],
            b["rotation"], b.get("wait_ms", 1500),
        )

    elif action == "throw":
        _log("Throw")
        await robot.throw()

    elif action == "stop":
        _log("Motors stop")
        await robot.stop()

    elif action == "begin_calibration":
        _log("Begin calibration — V (reset head)")
        await robot.write_raw("V")
        await asyncio.sleep(0.5)
        await robot.write_raw("V")

    elif action == "run_scenario":
        s = db.get_scenario(msg["id"])
        if not s:
            await _send(ws, "error", {"message": "Nie znaleziono scenariusza"})
            return
        repeat = s.get("repeat", 1)
        _log("Drill start: \"%s\" — %d balls, repeat: %s", s.get("name", "?"), len(s["balls"]), "infinite" if repeat == 0 else repeat)
        asyncio.create_task(robot.run_drill(s["balls"], s.get("repeat", 1)))

    elif action == "run_drill":
        d = drills.get_drill(msg["id"])
        if not d:
            await _send(ws, "error", {"message": "Nie znaleziono drilla"})
            return
        percent = msg.get("percent", 100)
        count = msg.get("count", 0) or d.get("user_count") or 0
        repeat = d.get("repeat", 0)
        _log("Drill start: \"%s\" — %d balls, repeat=%s, percent=%d, count=%d",
             d.get("name", "?"), len(d["balls"]),
             "inf" if repeat == 0 else repeat, percent, count)
        asyncio.create_task(robot.run_drill(d["balls"], repeat, count=count, percent=percent))

    elif action == "stop_drill":
        _log("Drill stop")
        robot.stop_drill()

    elif action == "run_training":
        t = training.get_training(msg["id"])
        if not t:
            await _send(ws, "error", {"message": "Nie znaleziono treningu"})
            return
        _log("Training start: \"%s\" — %d steps", t.get("name", "?"), len(t.get("steps", [])))
        _training_runner.start(t, robot, broadcast)

    elif action == "run_exercise_solo":
        ex = exercises.get_exercise(msg["exercise_id"])
        if not ex:
            await _send(ws, "error", {"message": "Nie znaleziono ćwiczenia"})
            return
        duration = msg.get("duration_sec") or ex.get("duration_sec", 60)
        _log("Exercise solo: \"%s\" %ds", ex.get("name", "?"), duration)
        mini = {
            "name": ex.get("name", "Ćwiczenie"),
            "countdown_sec": 3,
            "steps": [{"exercise_id": ex["id"], "exercise_name": ex.get("name", ""),
                        "duration_sec": duration, "pause_after_sec": 0}],
        }
        _training_runner.start(mini, robot, broadcast)

    elif action == "stop_training":
        _log("Training stop")
        _training_runner.stop()

    elif action == "pause_training":
        _log("Training pause")
        _training_runner.pause()
        broadcast("training_paused", {})

    elif action == "skip_training":
        _log("Training skip")
        _training_runner.skip()
        broadcast("training_skipped", {})

    elif action == "resume_training":
        _log("Training resume")
        _training_runner.resume()
        broadcast("training_resumed", {})

    elif action == "reset_ble":
        asyncio.create_task(robot.reset_ble())

    elif action == "set_simulation":
        enabled = msg.get("enabled", False)
        if enabled:
            robot.enable_simulation()
        else:
            robot.disable_simulation()
        _log("Simulation mode: %s", enabled)
        if enabled and sess:
            sess.role = Role.CONTROLLER
            await _send(ws, "session_role", {"role": Role.CONTROLLER, "session_id": sess.id})
            _broadcast_sessions()

    # ── Zarządzanie sesjami ──────────────────────────────────────────────────

    elif action == "request_takeover":
        _log("Takeover requested by session %s", sid)
        ctrl = _get_controller()
        if not ctrl:
            # nikt nie kontroluje — od razu przejmij
            if sess:
                sess.role = Role.CONTROLLER
                _broadcast_sessions()
                await _send(ws, "session_role", {"role": Role.CONTROLLER, "session_id": sess.id})
            return
        if any(s.role == Role.PENDING for s in sessions.values()):
            await _send(ws, "error", {"message": "Inny użytkownik już czeka na przejęcie"})
            return
        if sess:
            sess.role = Role.PENDING
            _broadcast_sessions()
            await _send(ctrl.ws, "takeover_request", {"requester_id": sess.id})

    elif action == "cancel_takeover":
        if sess and sess.role == Role.PENDING:
            sess.role = Role.OBSERVER
            _broadcast_sessions()

    elif action == "respond_takeover":
        accepted = msg.get("accepted", False)
        _log("Takeover %s by session %s", "accepted" if accepted else "rejected", sid)
        pending = next((s for s in sessions.values() if s.role == Role.PENDING), None)
        if not pending or not sess or sess.role != Role.CONTROLLER:
            return
        if accepted:
            sess.role = Role.OBSERVER
            pending.role = Role.CONTROLLER
            await _send(sess.ws, "session_role", {"role": Role.OBSERVER, "session_id": sess.id})
            await _send(pending.ws, "takeover_response", {"accepted": True, "role": Role.CONTROLLER})
        else:
            pending.role = Role.OBSERVER
            await _send(pending.ws, "takeover_response", {"accepted": False})
        _broadcast_sessions()

    elif action == "release_control":
        if sess and sess.role == Role.CONTROLLER:
            sess.role = Role.OBSERVER
            _promote_first_observer()
            _broadcast_sessions()


# ── REST — kalibracja ─────────────────────────────────────────────────────────

@app.get("/api/calibration")
def get_calibration():
    addr = _load_last_addr() if robot.is_connected else ""
    return _load_cal(addr)


@app.put("/api/calibration")
def save_calibration(body: dict):
    allowed = {"top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms"}
    cal = {k: v for k, v in body.items() if k in allowed}
    addr = _load_last_addr() if robot.is_connected else ""
    _log("Calibration saved for %s: %s", addr or "default", cal)
    _save_cal(cal, addr)
    return cal


# ── REST — presety kalibracji ─────────────────────────────────────────────────

@app.get("/api/presets")
def list_presets():
    return presets.get_presets()


@app.post("/api/presets", status_code=201)
def create_preset(body: dict):
    allowed = {"top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms"}
    data = {k: v for k, v in body.items() if k in allowed}
    new_id = presets.save_preset(body["name"], data, body.get("is_default", False))
    return {"id": new_id, "name": body["name"], **data, "is_default": body.get("is_default", False)}


@app.put("/api/presets/{preset_id}")
def update_preset_endpoint(preset_id: int, body: dict):
    allowed = {"top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms"}
    data = {k: v for k, v in body.items() if k in allowed}
    presets.update_preset(preset_id, body.get("name", ""), data, body.get("is_default", False))
    _log("UPDATE PRESET id=%d name=%s data=%s", preset_id, body.get("name"), data)
    return {"ok": True}


@app.put("/api/presets/{preset_id}/default", status_code=204)
def set_default_preset(preset_id: int):
    presets.set_default(preset_id)


@app.delete("/api/presets/{preset_id}", status_code=204)
def remove_preset(preset_id: int):
    presets.delete_preset(preset_id)


# ── REST — scenariusze ─────────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios():
    return db.get_scenarios()


@app.get("/api/scenarios/{id}")
def get_scenario(id: int):
    s = db.get_scenario(id)
    if not s:
        raise HTTPException(404)
    return s


@app.post("/api/scenarios", status_code=201)
def create_scenario(body: ScenarioIn):
    new_id = db.save_scenario(body.name, body.description, [b.model_dump() for b in body.balls], body.repeat)
    return db.get_scenario(new_id)


@app.put("/api/scenarios/{id}")
def update_scenario(id: int, body: ScenarioIn):
    if not db.get_scenario(id):
        raise HTTPException(404)
    db.update_scenario(id, body.name, body.description, [b.model_dump() for b in body.balls], body.repeat)
    return db.get_scenario(id)


@app.delete("/api/scenarios/{id}", status_code=204)
def delete_scenario(id: int):
    if not db.get_scenario(id):
        raise HTTPException(404)
    db.delete_scenario(id)


# ── REST — drille (plikowe) ───────────────────────────────────────────────────

@app.get("/api/drills/tree")
def get_drill_tree():
    return drills.get_tree()


@app.get("/api/drills/{drill_id}")
def get_drill_endpoint(drill_id: int):
    d = drills.get_drill(drill_id)
    if not d:
        raise HTTPException(404)
    return d


@app.post("/api/drills", status_code=201)
def create_drill_endpoint(body: dict):
    new_id = drills.create_custom_drill(body)
    return drills.get_drill(new_id)


@app.put("/api/drills/{drill_id}")
def update_drill_endpoint(drill_id: int, body: dict):
    _log("UPDATE DRILL id=%d", drill_id)
    if not drills.save_override(drill_id, body):
        drills.update_custom_drill(drill_id, body)
    return drills.get_drill(drill_id)


@app.delete("/api/drills/{drill_id}", status_code=204)
def delete_drill_endpoint(drill_id: int):
    drills.delete_custom_drill(drill_id)


@app.put("/api/drills/{drill_id}/count")
def set_drill_count(drill_id: int, body: dict):
    drills.set_user_count(drill_id, body.get("count"))
    return {"ok": True}


@app.put("/api/drills/{drill_id}/reset")
def reset_drill_endpoint(drill_id: int):
    drills.reset_drill(drill_id)
    _log("RESET DRILL id=%d", drill_id)
    return {"ok": True}


@app.post("/api/drills/reset-all")
def reset_all_drills():
    drills.reset_all()
    _log("RESET ALL DRILLS")
    return {"ok": True}


# ── REST — ćwiczenia fizyczne ─────────────────────────────────────────────────

@app.get("/api/exercises")
def list_exercises():
    return exercises.get_exercises()


@app.put("/api/exercises/{eid}/duration")
def set_exercise_duration(eid: int, body: dict):
    exercises.save_override(eid, body["duration_sec"])
    return {"ok": True}


@app.post("/api/exercises/reset-all")
def reset_all_exercises():
    exercises.reset_all()
    return {"ok": True}


# ── REST — treningi ───────────────────────────────────────────────────────────

@app.get("/api/trainings")
def list_trainings():
    return training.get_trainings()


@app.get("/api/trainings/{tid}")
def get_training_endpoint(tid: int):
    t = training.get_training(tid)
    if not t:
        raise HTTPException(404)
    return t


@app.post("/api/trainings", status_code=201)
def create_training(body: dict):
    tid = training.save_training(body)
    return training.get_training(tid)


@app.put("/api/trainings/{tid}")
def update_training(tid: int, body: dict):
    body["id"] = tid
    training.save_training(body)
    return training.get_training(tid)


@app.delete("/api/trainings/{tid}", status_code=204)
def delete_training_endpoint(tid: int):
    training.delete_training(tid)


# ── Frontend ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/{full_path:path}")
def spa(full_path: str = ""):
    return FileResponse(FRONTEND / "index.html")
