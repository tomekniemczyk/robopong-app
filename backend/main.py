import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import audio
import db
import drills
import exercises
import training
import players
import recordings
import presets
from models import ScenarioIn
from robot import Robot


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-5s %(name)s  %(message)s", datefmt="%H:%M:%S")
logging.getLogger("bleak").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

VERBOSE = True  # globalny przełącznik logowania — False żeby wyciszyć

def _log(msg: str, *args):
    if VERBOSE:
        logger.info(msg, *args)

def _dbg(msg: str, *args):
    if VERBOSE:
        logger.debug(msg, *args)


def _apply_player_handedness(robot_inst, player_id):
    """Set robot.left_handed based on player profile."""
    if player_id:
        p = players.get_player(player_id)
        robot_inst.left_handed = (p.get("handedness") == "left") if p else False
    else:
        robot_inst.left_handed = False


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


def _load_cal(addr: str = "") -> tuple:
    """Zwraca (cal_dict, was_saved) — was_saved=True jeśli użytkownik zapisał kalibrację dla tego urządzenia."""
    try:
        raw = json.loads(CAL_FILE.read_text())
        # Stary format płaski → automatyczna migracja
        if "top_speed" in raw:
            logger.debug("CAL _load_cal(%s): stary format płaski → was_saved=True", addr)
            return raw, True
        specific = raw.get(addr)
        if specific:
            logger.debug("CAL _load_cal(%s): znaleziono wpis specyficzny dla urządzenia → was_saved=True", addr)
            return specific, True
        fallback = raw.get("_default_")
        if fallback:
            # _default_ istnieje = użytkownik zapisał kalibrację (nawet bez adresu) → was_saved=True
            logger.debug("CAL _load_cal(%s): brak wpisu per-device, fallback _default_ → was_saved=True", addr)
            return fallback, True
        logger.debug("CAL _load_cal(%s): plik istnieje ale brak danych → DEFAULT_CAL, was_saved=False", addr)
        return DEFAULT_CAL.copy(), False
    except Exception as ex:
        logger.debug("CAL _load_cal(%s): brak pliku lub błąd (%s) → DEFAULT_CAL, was_saved=False", addr, ex)
        return DEFAULT_CAL.copy(), False


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
    """Łączy z robotem i broadcastuje calibration_loaded po udanym połączeniu."""
    if addr.startswith("USB:"):
        ok = await robot.connect_usb(addr[4:])
    else:
        ok = await robot.connect(addr)
    if ok:
        cal, was_saved = _load_cal(addr)
        logger.info("CAL _do_connect(%s): połączono — was_saved=%s, top=%s bot=%s osc=%s h=%s rot=%s",
                    addr, was_saved, cal.get("top_speed"), cal.get("bot_speed"),
                    cal.get("oscillation"), cal.get("height"), cal.get("rotation"))
        broadcast("calibration_loaded", {"cal": cal, "calibrated": was_saved, "addr": addr})
    else:
        logger.warning("CAL _do_connect(%s): połączenie nieudane", addr)
    return ok


async def _reconnect_loop():
    while True:
        await asyncio.sleep(15)
        if sessions and not robot.is_connected and not (robot._reconnect and not robot._reconnect.done()):
            last = _load_last_addr()
            if last:
                logger.info("CAL _reconnect_loop: robot rozłączony, próba reconnect → %s", last)
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
    # Wyślij calibration_loaded PRZED status — żeby frontend wiedział o kalibracji
    # zanim watcher watch(connected) sprawdzi isCalibrated i ewentualnie zrobi redirect
    if robot.is_connected and robot.device:
        cal, was_saved = _load_cal(robot.device)
        _log("WS init: wysyłam calibration_loaded przed status — addr=%s was_saved=%s", robot.device, was_saved)
        await ws.send_text(json.dumps({
            "type": "calibration_loaded",
            "cal": cal, "calibrated": was_saved, "addr": robot.device,
        }))
    await ws.send_text(json.dumps({
        "type":       "status",
        "connected":  robot.is_connected,
        "firmware":   robot.firmware,
        "device":     robot.device,
        "transport":  transport,
        "session_id": sess.id,
        "role":       sess.role,
    }))
    robot_q = asyncio.Queue()

    async def _robot_worker():
        """Process robot commands — drain queue, execute only the latest."""
        while True:
            msg_item = await robot_q.get()
            # Drain: skip to latest command
            while not robot_q.empty():
                msg_item = robot_q.get_nowait()
            try:
                await _handle(msg_item, ws)
            except Exception as e:
                logger.error("Robot cmd error: %s", e)

    worker = asyncio.create_task(_robot_worker())
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action", "")
            if action in ROBOT_ACTIONS:
                robot_q.put_nowait(msg)
            else:
                await _handle(msg, ws)
    except (WebSocketDisconnect, Exception):
        worker.cancel()
        gone = sessions.pop(ws, None)
        _log("Browser disconnected — session %s, remaining: %d", gone.id if gone else "?", len(sessions))
        if gone and gone.role == Role.CONTROLLER:
            if _training_runner.running:
                _training_runner.stop()
            asyncio.ensure_future(robot.stop())
        _promote_first_observer()
        _broadcast_sessions()


ROBOT_ACTIONS  = {"set_ball", "throw", "throw_ball", "run_scenario", "run_drill", "run_training", "begin_calibration", "run_drill_solo", "run_exercise_solo", "run_step_solo", "stop_training", "pause_training", "resume_training", "skip_training"}
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
            cal, was_saved = _load_cal(addr)
            _log("CAL connect BLE %s: was_saved=%s top=%s bot=%s osc=%s h=%s rot=%s",
                 addr, was_saved, cal.get("top_speed"), cal.get("bot_speed"),
                 cal.get("oscillation"), cal.get("height"), cal.get("rotation"))
            broadcast("calibration_loaded", {"cal": cal, "calibrated": was_saved, "addr": addr})
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
            cal, was_saved = _load_cal(addr)
            _log("CAL connect USB %s: was_saved=%s top=%s bot=%s osc=%s h=%s rot=%s",
                 addr, was_saved, cal.get("top_speed"), cal.get("bot_speed"),
                 cal.get("oscillation"), cal.get("height"), cal.get("rotation"))
            broadcast("calibration_loaded", {"cal": cal, "calibrated": was_saved, "addr": addr})

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

    elif action == "throw_ball":
        b = msg["ball"]
        count = msg.get("count", 1)
        _log("Throw ball: top=%s bot=%s osc=%s h=%s rot=%s wait=%sms count=%d",
             b["top_speed"], b["bot_speed"], b["oscillation"], b["height"], b["rotation"], b.get("wait_ms", 1500), count)
        if count > 1:
            await robot.run_drill([b], repeat=0, count=count, percent=100)
        else:
            await robot.set_ball(
                b["top_speed"], b["bot_speed"],
                b["oscillation"], b["height"],
                b["rotation"], b.get("wait_ms", 1500),
            )
            await asyncio.sleep(0.3)
            await robot.throw()

    elif action == "stop":
        _log("Motors stop")
        await robot.stop()

    elif action == "begin_calibration":
        _log("Begin calibration — V (reset head)")
        await robot.reset_head()
        await asyncio.sleep(0.5)
        await robot.reset_head()

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
        player_id = msg.get("player_id")
        _apply_player_handedness(robot, player_id)
        record = msg.get("record", False)
        record_type = msg.get("record_type", "all")
        start_from = msg.get("start_from_step", 0)
        _log("Training start: \"%s\" — %d steps, player=%s, record=%s (%s), from_step=%s",
             t.get("name", "?"), len(t.get("steps", [])), player_id, record, record_type, start_from)
        _training_runner.start(t, robot, broadcast, player_id=player_id, record=record, record_type=record_type, start_from_step=start_from)

    elif action == "run_drill_solo":
        d = drills.get_drill(msg["drill_id"])
        if not d:
            await _send(ws, "error", {"message": "Nie znaleziono drilla"})
            return
        player_id = msg.get("player_id")
        _apply_player_handedness(robot, player_id)
        record = msg.get("record", False)
        count = msg.get("count") or d.get("user_count") or 60
        percent = msg.get("percent", 100)
        _log("Drill solo: \"%s\" count=%d percent=%d player=%s record=%s", d.get("name", "?"), count, percent, player_id, record)
        mini = {
            "name": d.get("name", "Drill"),
            "countdown_sec": 3,
            "steps": [{"drill_id": d["id"], "drill_name": d.get("name", ""),
                        "count": count, "percent": percent, "pause_after_sec": 0}],
        }
        _training_runner.start(mini, robot, broadcast, player_id=player_id,
                               record=record, solo_drill_id=d["id"])

    elif action == "run_exercise_solo":
        ex = exercises.get_exercise(msg["exercise_id"])
        if not ex:
            await _send(ws, "error", {"message": "Nie znaleziono ćwiczenia"})
            return
        player_id = msg.get("player_id")
        _apply_player_handedness(robot, player_id)
        record = msg.get("record", False)
        duration = msg.get("duration_sec") or ex.get("duration_sec", 60)
        _log("Exercise solo: \"%s\" %ds player=%s record=%s", ex.get("name", "?"), duration, player_id, record)
        mini = {
            "name": ex.get("name", "Ćwiczenie"),
            "countdown_sec": 3,
            "steps": [{"exercise_id": ex["id"], "exercise_name": ex.get("name", ""),
                        "duration_sec": duration, "pause_after_sec": 0}],
        }
        _training_runner.start(mini, robot, broadcast, player_id=player_id,
                               record=record, solo_exercise_id=ex["id"])

    elif action == "run_step_solo":
        step = msg.get("step", {})
        record = msg.get("record", False)
        player_id = msg.get("player_id")
        _apply_player_handedness(robot, player_id)
        training_name = msg.get("training_name", "Solo")
        step_name = step.get("drill_name") or step.get("exercise_name") or "Step"
        _log("Step solo: \"%s\", record=%s, player=%s", step_name, record, player_id)
        mini = {
            "name": training_name,
            "countdown_sec": 5,
            "steps": [{**step, "pause_after_sec": 0}],
        }
        _training_runner.start(mini, robot, broadcast, player_id=player_id, record=record)

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

    elif action == "training_note":
        step_idx = msg.get("step", 0)
        note = msg.get("note", "").strip()
        if note and _training_runner.running:
            _training_runner.add_note(step_idx, note)
            _log("Training note step %d: %s", step_idx, note[:50])

    elif action == "set_next_percent":
        pct = msg.get("percent", 100)
        if _training_runner.running:
            _training_runner.set_next_percent(pct)
            _log("Next step percent override: %d%%", pct)
            broadcast("training_percent_changed", {"percent": pct})

    elif action == "reset_ble":
        asyncio.create_task(robot.reset_ble())

    elif action == "set_simulation":
        enabled = msg.get("enabled", False)
        ctrl = _get_controller()
        if enabled and ctrl and ctrl is not sess:
            await _send(ws, "error", {"message": "Inny użytkownik kontroluje robota"})
            return
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
    cal, _ = _load_cal(addr)
    return cal


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


@app.post("/api/drills/folders", status_code=201)
def create_folder(body: dict):
    return drills.create_folder(body.get("name", "Nowy folder"))


@app.put("/api/drills/folders/reorder")
def reorder_folders(body: list):
    drills.reorder_folders(body)


@app.put("/api/drills/folders/{folder_id}")
def rename_folder(folder_id: int, body: dict):
    if not drills.rename_folder(folder_id, body.get("name", "")):
        raise HTTPException(404)


@app.delete("/api/drills/folders/{folder_id}", status_code=204)
def delete_folder(folder_id: int):
    tree = drills.get_tree()
    folder = next((f for f in tree.get("folders", []) if f.get("id") == folder_id), None)
    if folder and folder.get("readonly"):
        raise HTTPException(403, "Cannot delete readonly folder")
    drills.delete_folder(folder_id)


@app.put("/api/drills/reorder")
def reorder_drills(body: list):
    drills.reorder_drills(body)


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
    d = drills.get_drill(drill_id)
    if d and d.get("readonly"):
        raise HTTPException(403, "Cannot delete readonly drill")
    refs = training.get_trainings_referencing_drill(drill_id)
    if refs:
        raise HTTPException(409, f"Drill używany w treningach: {', '.join(refs)}")
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


@app.get("/api/drills/export")
def export_drills():
    return drills.get_tree()


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
    try:
        training.save_training(body)
    except ValueError:
        raise HTTPException(403, "Cannot modify readonly training")
    return training.get_training(tid)


@app.delete("/api/trainings/{tid}", status_code=204)
def delete_training_endpoint(tid: int):
    try:
        training.delete_training(tid)
    except ValueError:
        raise HTTPException(403, "Cannot delete readonly training")


@app.post("/api/trainings/{tid}/duplicate", status_code=201)
def duplicate_training_endpoint(tid: int):
    copy = training.duplicate_training(tid)
    if not copy:
        raise HTTPException(404)
    return copy


# ── Training History ─────────────────────────────────────────────────────────

@app.get("/api/training-history")
def list_training_history(training_id: int | None = None, player_id: int | None = None,
                          limit: int | None = None, offset: int = 0):
    return training.get_history(training_id=training_id, player_id=player_id,
                                limit=limit, offset=offset)


@app.get("/api/training-history/{hid}")
def get_history_entry(hid: int):
    entry = db.get_history_entry(hid)
    if not entry:
        raise HTTPException(404)
    # Attach recordings for this session
    recs = recordings.get_recordings(player_id=entry.get("player_id"))
    entry["recordings"] = [r for r in recs if r.get("training_id") == entry.get("training_id")]
    return entry


@app.put("/api/training-history/{hid}/comment")
def update_history_comment(hid: int, body: dict):
    comment = body.get("comment", "").strip()
    training.update_session_comment(hid, comment)
    return {"ok": True}


@app.delete("/api/training-history/{hid}", status_code=204)
def delete_history_entry(hid: int):
    filenames = db.delete_history_cascade(hid)
    recordings.delete_files(filenames)


# ── Players ──────────────────────────────────────────────────────────────────

@app.get("/api/players")
def list_players():
    return players.get_players()


@app.get("/api/players/{pid}")
def get_player(pid: int):
    p = players.get_player(pid)
    if not p:
        raise HTTPException(404)
    return p


@app.post("/api/players", status_code=201)
def create_player(body: dict):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Name required")
    try:
        return players.create_player(name, body.get("handedness", "right"), body.get("lang", "pl"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.put("/api/players/{pid}")
def update_player(pid: int, body: dict):
    try:
        p = players.update_player(pid, name=body.get("name"), handedness=body.get("handedness"), lang=body.get("lang"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not p:
        raise HTTPException(404)
    return p


@app.delete("/api/players/{pid}", status_code=204)
def delete_player_endpoint(pid: int):
    rec_files, voice_files = db.delete_player_cascade(pid)
    recordings.delete_files(rec_files)
    recordings.delete_files(voice_files)


@app.get("/api/players/{pid}/stats")
def get_player_stats(pid: int):
    return db.get_player_stats(pid)


@app.get("/api/players/{pid}/history")
def get_player_history(pid: int):
    return training.get_history(player_id=pid)


@app.get("/api/players/{pid}/recordings")
def get_player_recordings(pid: int):
    return recordings.get_recordings(player_id=pid)


@app.get("/api/players/{pid}/favorites")
def get_player_favorites(pid: int):
    return db.get_favorites(pid)


@app.post("/api/players/{pid}/favorites", status_code=201)
def add_player_favorite(pid: int, body: dict):
    item_type = body.get("item_type", "")
    item_id = body.get("item_id")
    if item_type not in ("training", "drill", "exercise") or item_id is None:
        raise HTTPException(400, "item_type and item_id required")
    return db.add_favorite(pid, item_type, item_id)


@app.delete("/api/players/{pid}/favorites", status_code=204)
def remove_player_favorite(pid: int, item_type: str = "", item_id: int = 0):
    db.remove_favorite(pid, item_type, item_id)


# ── Recordings ───────────────────────────────────────────────────────────────

@app.get("/api/recordings")
def list_recordings(player_id: int | None = None):
    return recordings.get_recordings(player_id=player_id)


@app.get("/api/recordings/compare")
def get_comparable_recordings(training_id: int | None = None, step_idx: int | None = None,
                              drill_id: int | None = None, exercise_id: int | None = None,
                              exclude_filename: str | None = None):
    return db.get_comparable_recordings(
        training_id=training_id, step_idx=step_idx,
        drill_id=drill_id, exercise_id=exercise_id,
        exclude_filename=exclude_filename)


@app.get("/api/recordings/info")
def get_recordings_info(player_id: int | None = None, history_id: int | None = None):
    return db.get_recordings_stats(player_id=player_id, history_id=history_id)


@app.get("/api/recordings/download-zip")
def download_recordings_zip(player_id: int | None = None, history_id: int | None = None):
    stats = db.get_recordings_stats(player_id=player_id, history_id=history_id)
    if not stats["filenames"]:
        raise HTTPException(404, "No recordings")
    buf = recordings.create_zip(stats["filenames"])
    name = f"recordings_player{player_id}.zip" if player_id else f"recordings_session{history_id}.zip"
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.get("/api/recordings/{player_id}/{filename}")
def get_recording(player_id: int, filename: str):
    path = recordings.get_recording_path(f"{player_id}/{filename}")
    if not path:
        raise HTTPException(404)
    return FileResponse(path, media_type="video/mp4", filename=filename)


@app.delete("/api/recordings/{player_id}/{filename}", status_code=204)
def delete_recording(player_id: int, filename: str):
    if not recordings.delete_recording(f"{player_id}/{filename}"):
        raise HTTPException(404)


# ── Voice notes ───────────────────────────────────────────────────────────────

VOICE_DIR = Path(__file__).parent / "recordings"


@app.post("/api/voice-notes", status_code=201)
async def upload_voice_note(
    file: UploadFile,
    player_id: int = Form(...),
    step_idx: int = Form(0),
    training_history_id: int | None = Form(None),
    duration_ms: int = Form(0),
):
    player_dir = VOICE_DIR / str(player_id)
    player_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voice_s{step_idx:02d}_{ts}.webm"
    filepath = player_dir / filename
    content = await file.read()
    filepath.write_bytes(content)
    nid = db.save_voice_note(
        player_id=player_id,
        filename=f"{player_id}/{filename}",
        step_idx=step_idx,
        training_history_id=training_history_id,
        duration_ms=duration_ms or len(content) // 8,  # rough estimate if not provided
    )
    return db.get_voice_note(nid)


@app.get("/api/voice-notes")
def list_voice_notes(player_id: int | None = None, training_history_id: int | None = None):
    return db.get_voice_notes(player_id=player_id, training_history_id=training_history_id)


@app.get("/api/voice-notes/{nid}/audio")
def get_voice_note_audio(nid: int):
    note = db.get_voice_note(nid)
    if not note:
        raise HTTPException(404)
    path = VOICE_DIR / note["filename"]
    if not path.exists() or not path.is_relative_to(VOICE_DIR):
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/webm")


@app.delete("/api/voice-notes/{nid}", status_code=204)
def delete_voice_note(nid: int):
    note = db.get_voice_note(nid)
    if not note:
        raise HTTPException(404)
    path = VOICE_DIR / note["filename"]
    if path.exists() and path.is_relative_to(VOICE_DIR):
        path.unlink()
    db.delete_voice_note(nid)


# ── Ball landings ───────────────────────────────────────────────────────────────

@app.post("/api/ball-landings", status_code=201)
def add_ball_landing(body: dict):
    player_id = body.get("player_id")
    drill_id = body.get("drill_id")
    x = body.get("x")
    y = body.get("y")
    if player_id is None or drill_id is None or x is None or y is None:
        raise HTTPException(400, "player_id, drill_id, x, y required")
    lid = db.save_ball_landing(int(player_id), int(drill_id), float(x), float(y))
    return {"id": lid}


@app.get("/api/ball-landings")
def list_ball_landings(drill_id: int, player_id: int | None = None):
    return db.get_ball_landings(drill_id, player_id)


@app.delete("/api/ball-landings/{lid}", status_code=204)
def delete_ball_landing_endpoint(lid: int):
    db.delete_ball_landing(lid)


# ── Volume ─────────────────────────────────────────────────────────────────────

@app.get("/api/volume")
def get_volume():
    return {"volume": audio.get_volume()}


@app.put("/api/volume")
def set_volume(body: dict):
    vol = audio.set_volume(int(body.get("volume", 50)))
    return {"volume": vol}


@app.post("/api/volume/test")
def test_volume():
    audio.play("beep_high")
    return {"ok": True}


# ── Ball exploration ──────────────────────────────────────────────────────────

@app.post("/api/ball-exploration", status_code=201)
def create_ball_exploration(body: dict):
    eid = db.save_ball_exploration(body)
    return {"id": eid}


@app.get("/api/ball-exploration")
def list_ball_explorations(player_id: int | None = None, limit: int = 50):
    return db.get_ball_explorations(player_id=player_id, limit=limit)


@app.delete("/api/ball-exploration/{eid}", status_code=204)
def delete_ball_exploration_endpoint(eid: int):
    db.delete_ball_exploration(eid)


# ── Frontend ───────────────────────────────────────────────────────────────────

@app.middleware("http")
async def no_cache_dynamic_assets(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css")) and "/static/" in path:
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

_exercises_dir = FRONTEND / "static" / "exercises"
if _exercises_dir.exists():
    app.mount("/static/exercises", StaticFiles(directory=str(_exercises_dir)), name="exercises")
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/{full_path:path}")
def spa(full_path: str = ""):
    return FileResponse(FRONTEND / "index.html")
