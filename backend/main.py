import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import db
from models import Ball, ScenarioIn
from robot import Robot

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global robot
    db.init()
    robot = Robot(on_event=broadcast)
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
        if not ok:
            await ws.send_text(json.dumps({"type": "error", "message": "Nie można połączyć z robotem"}))

    elif action == "disconnect":
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


# ── Camera stream ──────────────────────────────────────────────────────────────

def _mjpeg_frames():
    if not _CV2:
        return
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
    finally:
        cap.release()


@app.get("/api/camera")
def camera_stream():
    if not _CV2:
        raise HTTPException(503, "opencv-python not installed")
    return StreamingResponse(_mjpeg_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/camera/available")
def camera_available():
    if not _CV2:
        return {"available": False}
    cap = cv2.VideoCapture(0)
    ok = cap.isOpened()
    cap.release()
    return {"available": ok}


# ── Frontend ───────────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/{full_path:path}")
def spa(full_path: str = ""):
    return FileResponse(FRONTEND / "index.html")
