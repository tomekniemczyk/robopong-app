# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Instrukcje dla Claude — AcePad

## Kontekst projektu

**AcePad** (by tthub.pl) to aplikacja do sterowania robotami pingpongowymi, zastępująca Newgy dla Donic Robopong 3050XL.
Celem jest stworzenie własnego klienta, który komunikuje się z robotem i daje pełną kontrolę nad jego parametrami.

## Komendy deweloperskie

```bash
# Start serwera (dev, port 8000)
./start.sh

# Instalacja zależności testowych + testy
cd backend
venv/bin/pip install -r requirements-test.txt
venv/bin/pytest

# Pojedynczy test
venv/bin/pytest tests/test_api.py::nazwa_testu

# Prod deploy (auto-deploy co 15s z CI pass check)
./deploy.sh
```

### Testy backend (143 testów)
- `test_api.py` — integracja: scenariusze, kalibracja, presety
- `test_api_drills.py` — integracja: CRUD foldery, drille, override, reorder
- `test_api_training.py` — integracja: CRUD treningi
- `test_api_exercises.py` — integracja: exercises, duration override
- `test_db.py` — unit: SQLite scenariusze
- `test_presets.py` — unit: SQLite presety
- `test_drills.py` — unit: file-based drills storage
- `test_exercises.py` — unit: file-based exercises storage
- `test_training_storage.py` — unit: file-based training storage
- `test_transport.py` — unit: SimulationTransport, ABC, USBTransport
- `test_models.py` — unit: Pydantic validation
- `conftest.py` — shared fixtures (client, tmp files)

## Architektura

- **Backend:** FastAPI + Bleak (BLE) + pyserial (USB FTDI), plik `backend/main.py` + `backend/robot.py`
- **Frontend:** Vue 3 CDN, jeden plik `frontend/index.html`, i18n w `frontend/i18n.js`
- **Serwer produkcyjny:** `192.168.1.45`, user `robopong`, port `8001`
- **Deploy:** `./deploy.sh` — polling co 15s, deploy tylko po CI pass (`gh run`)
- **Kamera:** motion, port `8081`

### Warstwy backendu

- `transport.py` — ABC `RobotTransport` → `BLETransport` (Bleak/MLDP), `USBTransport` (pyserial FTDI), `SimulationTransport`
- `robot.py` — `Robot`: orkiestracja połączenia, reconnect, wysyłanie komend, zarządzanie drill loop
- `main.py` — FastAPI app, REST endpoints + WebSocket (`/ws`), broadcast logów do przeglądarki
- `db.py` — SQLite (`robopong.db`): tabele `scenarios`, `drills`, `drill_folders`
- `presets.py` + `presets.db` — osobna baza presetów konfiguracji robota
- `drills.py`, `exercises.py`, `training.py` — CRUD dla odpowiednich encji (file-based JSON)
- `models.py` — Pydantic models (Ball, ScenarioIn, DrillIn, TrainingStep, etc.)
- `audio.py` — dźwięki (pliki w `backend/sounds/`)

### i18n
- 5 języków: PL, EN, DE, FR, ZH — klucze w `frontend/i18n.js`
- Funkcja `t()` zarejestrowana jako `app.config.globalProperties.t` (NIE w setup return!)
- **UWAGA:** Vue 3 prod compiler minifikuje zmienne v-for — NIE zwracaj `t` z setup(), bo zostanie przesłonięte

### Deploy troubleshooting
- CI musi przejść — `deploy.sh` odpytuje `gh run list`
- Wymaga `python-multipart` w requirements.txt (FastAPI form data)
- Static files: `Cache-Control: no-cache` middleware w main.py

## Protokół robota (ZBADANY — patrz `re/`)

Protokół Robopong 3050XL jest w pełni udokumentowany w `re/`:
- `re/ANDROID_APP_RE.md` — aplikacja Android (Xamarin, BLE+USB)
- `re/WINDOWS_APP_RE.md` — aplikacja Windows (WPF, FTDI USB)
- `re/IOS_APP_RE.md` — aplikacja iOS (Xamarin, CoreBluetooth)
- `re/BUSINESS_LOGIC_COMPLETE.md` — wspólna logika biznesowa, formuły, bugi, porównanie

### Kluczowe wartości (NIE ZMIENIAJ BEZ POWODU)
- **Centrum głowicy = 150** (oscylacja, rotacja, wysokość) — NIE 128!
- Oscillation: zakres 127–173, centrum 150
- Height: zakres 75–210
- Rotation: zakres 90–210, centrum 150
- Prędkość silnika: `raw * 4.016` = wartość PWM w komendzie B/A
- BLE terminator: `\r`, USB terminator: `\r\n`
- USB init: bajt `0x5A` × 2 na 9600 baud (nie "Z\r\n"!)
- Firmware >= 701: komenda `A` + `wTA` zamiast `B`
- LEDS: `ratio = |top-bot| / 360`, wartości 0–8

### Kalibracja UX (USER FEEDBACK)
- Po rzucie kalibracyjnym silniki STOP (H) — nie kręcą ciągle
- Sekwencja Rzut: `set_ball → 300ms → T → 1500ms → H`
- Przycisk "Wyślij" = rozkręca silniki (trzyma)
- Przycisk "Rzut" = wyślij + rzut + auto-stop
- Bez auto-rozgrzewki silników przy wejściu w kalibrację
- Kalibracja per-device (keyed by device address w `.calibration.json`)
- Default kalibracji (Android Gen2): top=160, bot=0, osc=150, h=183, rot=150, wait=1000

## Zasady pracy

### Git workflow (OBOWIĄZKOWE)
- **Commituj prosto na `main`** — bez feature branchy, bez PRów
- Lokalna praca Claude: używaj **worktree** (`git worktree add`) żeby uniknąć konfliktów z działającym serwerem
- Push: `git push origin main`
- Nie używaj `/commit-push-pr` — tylko `/commit` + push na main

### Zarządzanie zadaniami (OBOWIĄZKOWE)
- Gdy użytkownik mówi "dodaj zadanie", "nowe zadanie", "task:", "TODO:" — **zawsze** twórz GitHub Issue
- Repozytorium: `tomekniemczyk/robopong-app`
- Komenda: `gh issue create --repo tomekniemczyk/robopong-app --title "..." --body "..." --label "backlog,PRIORYTET"`
- Priorytety (etykiety): `wysoki`, `sredni`, `niski` — domyślnie `sredni`
- Nowe zadania: etykieta `backlog`

### Styl kodu
- Zwięzły, bez nadmiarowych komentarzy
- Brak nadmiarowej obsługi błędów dla scenariuszy niemożliwych
- Bez feature flags, backward-compat shims itp.
- VERBOSE logging domyślnie włączone (przełącznik w `main.py`)

### Komunikacja
- Odpowiedzi po polsku, chyba że kod/nazwy techniczne wymagają angielskiego
- Krótko i na temat
- Nie podsumowuj tego co właśnie zrobiłeś — użytkownik widzi diff

### Dokumentowanie ustaleń
- Każde ustalenie dot. protokołu/wartości/UX zapisuj w memory i CLAUDE.md
- Ustalenia z testów na żywo mają priorytet nad RE dokumentacją

## Slash commands

- `/task [opis]` — dodaj nowe zadanie jako GitHub Issue
- `/tasks` — pokaż stan boardu z GitHub Issues
