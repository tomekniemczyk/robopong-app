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
import presets
from models import Ball, ScenarioIn
from robot import Robot


logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

FRONTEND = Path(__file__).parent.parent / "frontend"

robot: Robot


class Role:
    CONTROLLER = "controller"
    OBSERVER   = "observer"
    PENDING    = "pending"


@dataclass
class Session:
    ws:   WebSocket
    id:   str = field(default_factory=lambda: uuid.uuid4().hex[:6])
    role: str = Role.OBSERVER


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
    lst = [{"id": s.id, "role": s.role} for s in sessions.values()]
    broadcast("sessions", {"sessions": lst})


LAST_ADDR_FILE = Path(__file__).parent / ".last_device"
CAL_FILE       = Path(__file__).parent / ".calibration.json"

DEFAULT_CAL = {"top_speed": 50, "bot_speed": 50, "oscillation": 128, "height": 128, "rotation": 128, "wait_ms": 1500}


def _load_cal() -> dict:
    try:
        return json.loads(CAL_FILE.read_text())
    except Exception:
        return DEFAULT_CAL.copy()


def _save_cal(data: dict):
    try:
        CAL_FILE.write_text(json.dumps(data))
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
        return await robot.connect_usb(addr[4:])
    return await robot.connect(addr)


async def _reconnect_loop():
    while True:
        await asyncio.sleep(15)
        if sessions and not robot.is_connected:
            last = _load_last_addr()
            if last:
                logger.info("auto-reconnect → %s", last)
                await _do_connect(last)


async def _standby_loop():
    global _last_activity
    while True:
        await asyncio.sleep(30)
        if (robot.is_connected
                and _last_activity > 0
                and time.monotonic() - _last_activity > STANDBY_SECS):
            logger.info("standby — brak aktywności przez %ds", STANDBY_SECS)
            await robot.stop()
            _last_activity = 0.0
            broadcast("info", {"message": "🌙 Robot w trybie standby (5 min bezczynności)"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global robot, DEFAULT_CAL
    db.init()
    presets.init_presets()
    default = presets.get_default_preset()
    if default:
        DEFAULT_CAL = {k: default[k] for k in ("top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms")}
    robot = Robot(on_event=broadcast)
    last = _load_last_addr()
    if last:
        logger.info("auto-connect przy starcie → %s", last)
        asyncio.create_task(_do_connect(last))
    asyncio.create_task(_reconnect_loop())
    asyncio.create_task(_standby_loop())
    yield
    if robot.is_connected:
        await robot.disconnect()


app = FastAPI(title="robopong-app", lifespan=lifespan)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    sess = Session(ws=ws)
    if not any(s.role == Role.CONTROLLER for s in sessions.values()):
        sess.role = Role.CONTROLLER
    sessions[ws] = sess
    _broadcast_sessions()

    transport = "usb" if (hasattr(robot, "_usb") and getattr(robot._usb, "is_connected", False)) else "ble"
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
        sessions.pop(ws, None)
        _promote_first_observer()
        _broadcast_sessions()


ROBOT_ACTIONS  = {"set_ball", "throw", "stop", "run_scenario", "stop_drill"}
STANDBY_SECS   = 5 * 60
_last_activity: float = 0.0


async def _handle(msg: dict, ws: WebSocket):
    action = msg.get("action", "")
    sess = sessions.get(ws)

    if action in ROBOT_ACTIONS:
        if not sess or sess.role != Role.CONTROLLER:
            await _send(ws, "error", {"message": "Nie jesteś kontrolerem robota"})
            return
        global _last_activity
        _last_activity = time.monotonic()

    if action == "scan":
        devices = await robot.scan(msg.get("timeout", 8))
        await ws.send_text(json.dumps({"type": "scan_result", "devices": devices}))

    elif action == "connect":
        ok = await robot.connect(msg["address"])
        if ok:
            _save_last_addr(msg["address"])
            _last_activity = time.monotonic()
        else:
            await _send(ws, "error", {"message": "Nie można połączyć z robotem"})

    elif action == "disconnect":
        _save_last_addr("")
        await robot.disconnect()

    elif action == "usb_scan":
        ports = robot.usb_ports()
        await ws.send_text(json.dumps({"type": "usb_ports", "ports": ports}))

    elif action == "usb_connect":
        ok = await robot.connect_usb(msg["port"])
        if ok:
            _save_last_addr(f"USB:{msg['port']}")
            _last_activity = time.monotonic()

    elif action == "usb_disconnect":
        _save_last_addr("")
        await robot.disconnect()

    elif action == "set_ball":
        b = msg["ball"]
        await robot.set_ball(
            b["top_speed"], b["bot_speed"],
            b["oscillation"], b["height"],
            b["rotation"], b.get("wait_ms", 1500),
        )

    elif action == "throw":
        await robot.throw()

    elif action == "stop":
        await robot.stop()

    elif action == "run_scenario":
        s = db.get_scenario(msg["id"])
        if not s:
            await _send(ws, "error", {"message": "Nie znaleziono scenariusza"})
            return
        asyncio.create_task(robot.run_drill(s["balls"], s.get("repeat", 1)))

    elif action == "stop_drill":
        robot.stop_drill()

    elif action == "reset_ble":
        asyncio.create_task(robot.reset_ble())

    # ── Zarządzanie sesjami ──────────────────────────────────────────────────

    elif action == "request_takeover":
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
    return _load_cal()


@app.put("/api/calibration")
def save_calibration(body: dict):
    allowed = {"top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms"}
    cal = {k: v for k, v in body.items() if k in allowed}
    _save_cal(cal)
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


# ── Frontend ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/{full_path:path}")
def spa(full_path: str = ""):
    return FileResponse(FRONTEND / "index.html")
