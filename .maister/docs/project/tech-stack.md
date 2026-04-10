# Technology Stack

## Overview
AcePad uses a Python backend with FastAPI serving both REST API and WebSocket connections, communicating with the Robopong 3050XL via BLE and USB FTDI. The frontend is a Vue 3 single-page application served directly via CDN (no build step).

## Languages

### Python (3.11+)
- **Usage**: Backend (12 modules, ~5400 lines)
- **Rationale**: Excellent async support (asyncio), rich ecosystem for BLE (Bleak) and USB (pyserial), fast API development with FastAPI
- **Key Features Used**: async/await, type hints, dataclasses, f-strings

### JavaScript (ES6+)
- **Usage**: Frontend (~5300 lines in single-file SPA)
- **Rationale**: Vue 3 CDN approach — no build tooling required, rapid iteration on constrained hardware (Raspberry Pi)

## Frameworks

### Backend
- **FastAPI** (>=0.110.0) — REST API + WebSocket endpoints, async-native, Pydantic validation
- **Uvicorn** (>=0.27.0) — ASGI server for production deployment
- **Pydantic** (>=2.6.0) — Data validation for all API inputs (Ball, ScenarioIn, DrillIn, TrainingStep)

### Frontend
- **Vue 3** (CDN) — Reactive SPA framework, no build step, Composition API with `setup()`
- **No router** — Tab-based navigation via `page` ref with `v-show`

### Communication
- **Bleak** (>=0.22.0) — Cross-platform BLE client for Robopong MLDP protocol
- **pyserial** (>=3.5) — USB FTDI communication with RN4870 module

### Testing
- **pytest** — 196 tests across 17 files (integration + unit)
- **unittest.mock** — Hardware mocking (Robot, BLE, USB)
- **Starlette TestClient** — API integration testing

## Database

### SQLite 3
- **Type**: Embedded relational database
- **Files**: `robopong.db` (11 tables), `presets.db` (calibration presets)
- **Rationale**: Zero-configuration, file-based, perfect for single-server IoT deployment on Raspberry Pi
- **Tables**: scenarios, players, user_trainings, training_history, recordings_meta, voice_notes, ball_landings, ball_exploration, favorites, drill_folders, drills

### File-based JSON
- **Usage**: Factory defaults + user overrides (drills, exercises, trainings, calibration)
- **Rationale**: Human-readable defaults, easy to ship and update, user data layered on top

## Build Tools & Package Management
- **pip** + **venv** — Python package management and virtual environment
- **No frontend build** — Vue 3 loaded via CDN, CSS served as static files

## Infrastructure

### Hosting
- **Raspberry Pi** (10.0.0.45:8001) — Production server
- **Uvicorn** — ASGI server (port 8000 dev, 8001 prod)

### CI/CD
- **GitHub Actions** — Python 3.11, pytest on push/PR
- **deploy.sh** — Custom polling script (15s interval), deploys on CI pass

### Camera
- **motion** (port 8081) — MJPEG video stream
- **ffmpeg** — MJPEG to H.264 MP4 conversion for recordings

### Audio
- **aplay** — WAV playback for training events (sounds/ directory)

## Development Tools

### Type Checking
- **Pydantic** — Runtime validation for API models
- **Python type hints** — Used extensively in function signatures

### Linting & Formatting
- No automated linting configured (opportunity for improvement)

## Key Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.110.0 | REST + WebSocket API |
| uvicorn | >=0.27.0 | ASGI server |
| pydantic | >=2.6.0 | Data validation |
| bleak | >=0.22.0 | BLE client |
| pyserial | >=3.5 | USB FTDI |
| aiosqlite | >=0.19.0 | Async SQLite |
| httpx | test | HTTP client for tests |
| pytest | test | Test framework |

---
*Last Updated*: 2026-04-10
*Auto-detected*: Languages, frameworks, dependencies, database, CI/CD, test counts, file structure
