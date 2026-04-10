# System Architecture

## Overview
AcePad follows a layered monolithic architecture with a Python FastAPI backend serving both a REST API and WebSocket connections. The frontend is a Vue 3 single-page application served as static files. The system communicates with the Robopong 3050XL robot via BLE (Bluetooth Low Energy) and USB FTDI protocols.

## Architecture Pattern
**Pattern**: Layered monolithic with hybrid REST + WebSocket communication

The backend is organized in clear layers:
1. **Transport Layer** — Hardware abstraction (BLE, USB, Simulation)
2. **Robot Layer** — Connection orchestration, health monitoring, command execution
3. **API Layer** — REST endpoints + WebSocket handler
4. **Storage Layer** — SQLite + file-based JSON hybrid
5. **Domain Layer** — Drills, exercises, trainings, players, recordings

## System Structure

### Transport Layer
- **Location**: `backend/transport.py` (364 lines)
- **Purpose**: Abstract hardware communication behind a common interface
- **Key Classes**: `RobotTransport` (ABC), `BLETransport`, `USBTransport`, `SimulationTransport`
- **Protocol**: Binary commands over MLDP (BLE) or FTDI serial (USB), `\r` / `\r\n` terminators

### Robot Orchestration
- **Location**: `backend/robot.py` (418 lines)
- **Purpose**: Connection lifecycle, handshake sequence (Z→H→F→I→J02), health monitor (ping every 10s), drill loop execution
- **Key Class**: `Robot` (singleton, initialized in FastAPI lifespan)
- **Events**: Emits status updates via callback system

### API Layer
- **Location**: `backend/main.py` (1152 lines)
- **Purpose**: 40+ REST endpoints, WebSocket handler (`/ws`), session management (CONTROLLER/OBSERVER/PENDING), static file serving
- **Session Model**: Multi-user with role-based access — one controller, multiple observers, takeover protocol

### Training Engine
- **Location**: `backend/training.py` (532 lines)
- **Purpose**: Training state machine (start/stop/pause/resume/skip), countdown timers, step progression, percent override, integration with Recorder
- **Key Class**: `TrainingRunner`

### Storage Layer
- **Location**: `backend/db.py` (927 lines), `backend/presets.py` (74 lines)
- **Purpose**: SQLite CRUD for 11 tables (players, history, recordings, etc.) + separate presets database
- **Hybrid Storage**: SQLite for relational data, JSON files for defaults + user overrides

### Recording System
- **Location**: `backend/recordings.py` (197 lines)
- **Purpose**: ffmpeg subprocess management — captures MJPEG stream from motion camera, converts to H.264 MP4, auto-deletes recordings < 30s

### Frontend
- **Location**: `frontend/index.html` (5314 lines)
- **Purpose**: Single-file Vue 3 SPA with tab-based navigation, 100+ reactive refs, hybrid REST + WebSocket communication
- **i18n**: 5 languages (PL/EN/DE/FR/ZH) via `t()` and `tc()` functions

## Data Flow

```
User (Browser)
    ↕ HTTP/WebSocket
FastAPI (main.py)
    ↕ Python calls
Robot (robot.py) ←→ Transport (BLE/USB/Sim)
    ↕                    ↕
DB/Storage          Robopong 3050XL
```

**REST flow**: Browser → FastAPI endpoint → db/drills/training module → JSON response
**WebSocket flow**: Browser → WS message → main.py handler → Robot command → WS broadcast to all clients
**Robot control**: WS action → Robot.throw/set_ball → Transport.send → Binary protocol → Robot hardware

## External Integrations

| Integration | Protocol | Purpose |
|-------------|----------|---------|
| Robopong 3050XL | BLE MLDP / USB FTDI | Robot control (binary commands) |
| motion camera | HTTP MJPEG (port 8081) | Video stream for recordings |
| ffmpeg | Subprocess | MJPEG → MP4 conversion |
| aplay | Subprocess | WAV audio playback |
| GitHub Actions | HTTPS | CI/CD pipeline |

## Database Schema
- **robopong.db**: 11 tables — scenarios, players, user_trainings, training_history, recordings_meta, voice_notes, ball_landings, ball_exploration, favorites, drill_folders, drills
- **presets.db**: Robot calibration presets (separate database)
- **Schema defined in**: `backend/db.py` (CREATE TABLE statements in `init_db()`)

## Configuration
- `.calibration.json` — Per-device calibration (keyed by BLE address)
- `.last_device` — Last connected device for auto-reconnect
- `*_default.json` — Factory defaults (drills, exercises, trainings)
- `.*_user.json` — User overrides layered on top of defaults
- Environment: dev (port 8000) vs prod (port 8001) via start.sh / deploy.sh

## Deployment Architecture
- **Server**: Raspberry Pi (10.0.0.45)
- **Process**: Uvicorn ASGI server (single process)
- **Deploy**: `deploy.sh` polls GitHub every 15s, deploys on CI pass
- **No containers**: Direct Python venv on Raspberry Pi OS

---
*Based on codebase analysis performed 2026-04-10*
