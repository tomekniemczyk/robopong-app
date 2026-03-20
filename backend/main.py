import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import db
from models import Ball, ScenarioIn
from robot import Robot


logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

FRONTEND = Path(__file__).parent.parent / "frontend"

robot: Robot
clients: Set[WebSocket] = set()


def broadcast(event_type: str, data: dict):
    msg = json.dumps({"type": event_type, **data})
    dead = set()
    for ws in clients:
        try:
            asyncio.create_task(ws.send_text(msg))
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)


LAST_ADDR_FILE  = Path(__file__).parent / ".last_device"
CAL_FILE        = Path(__file__).parent / ".calibration.json"

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global robot
    db.init()
    robot = Robot(on_event=broadcast)
    last = _load_last_addr()
    if last:
        logger.info("auto-connect przy starcie → %s", last)
        asyncio.create_task(robot.connect(last))
    yield
    if robot.is_connected:
        await robot.disconnect()


app = FastAPI(title="robopong-app", lifespan=lifespan)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    await ws.send_text(json.dumps({
        "type":      "status",
        "connected": robot.is_connected,
        "firmware":  robot.firmware,
        "device":    robot.device,
    }))
    try:
        while True:
            raw = await ws.receive_text()
            await _handle(json.loads(raw), ws)
    except (WebSocketDisconnect, Exception):
        clients.discard(ws)


async def _handle(msg: dict, ws: WebSocket):
    action = msg.get("action", "")

    if action == "scan":
        devices = await robot.scan(msg.get("timeout", 8))
        await ws.send_text(json.dumps({"type": "scan_result", "devices": devices}))

    elif action == "connect":
        ok = await robot.connect(msg["address"])
        if ok:
            _save_last_addr(msg["address"])
        else:
            await ws.send_text(json.dumps({"type": "error", "message": "Nie można połączyć z robotem"}))

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
            await ws.send_text(json.dumps({"type": "error", "message": "Nie znaleziono scenariusza"}))
            return
        asyncio.create_task(robot.run_drill(s["balls"], s.get("repeat", 1)))

    elif action == "stop_drill":
        robot.stop_drill()


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
