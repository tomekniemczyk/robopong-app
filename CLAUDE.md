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

### Testy backend (196 testów)
- `test_api.py` — integracja: scenariusze, kalibracja, presety
- `test_api_drills.py` — integracja: CRUD foldery, drille, override, reorder
- `test_api_training.py` — integracja: CRUD treningi, historia, nagrania, notatki
- `test_api_exercises.py` — integracja: exercises, duration override
- `test_history_enhanced.py` — integracja: historia treningów, komentarze, kasowanie
- `test_recordings_enhanced.py` — integracja: nagrania, porównywanie, ZIP download
- `test_db.py` — unit: SQLite scenariusze
- `test_presets.py` — unit: SQLite presety
- `test_drills.py` — unit: file-based drills storage
- `test_exercises.py` — unit: file-based exercises storage
- `test_training_storage.py` — unit: file-based training storage
- `test_transport.py` — unit: SimulationTransport, ABC, USBTransport
- `test_models.py` — unit: Pydantic validation
- `conftest.py` — shared fixtures (client, tmp files)

## Architektura

### Stack
- **Backend:** FastAPI + Bleak (BLE) + pyserial (USB FTDI) + SQLite + file-based JSON
- **Frontend:** Vue 3 CDN (no build step, no router), single-file SPA
- **Serwer produkcyjny:** Raspberry Pi `192.168.1.73`, user `robopong`, port `8001`
- **Kamera:** motion, port `8081`, nagrywanie przez ffmpeg (MJPEG → H.264 MP4)
- **Deploy:** `./deploy.sh` — polling co 15s, deploy tylko po CI pass (`gh run`)
- **CI:** GitHub Actions — Python 3.11, pytest

### Warstwy backendu

- `transport.py` — ABC `RobotTransport` → `BLETransport` (Bleak/MLDP), `USBTransport` (pyserial FTDI), `SimulationTransport`
- `robot.py` — `Robot`: orkiestracja połączenia, handshake (Z→H→F→I→J02), reconnect, health monitor (ping co 10s), drill loop
- `main.py` — FastAPI app, REST endpoints + WebSocket (`/ws`), broadcast logów, session management (CONTROLLER/OBSERVER/PENDING + takeover)
- `training.py` — `TrainingRunner`: state machine (start/stop/pause/resume/skip), integracja z Recorder, historia sesji, step notes, percent override
- `recordings.py` — `Recorder`: ffmpeg subprocess (motion MJPEG → MP4), auto-delete <30s, metadata do SQLite
- `db.py` — SQLite (`robopong.db`): 11 tabel (patrz niżej)
- `presets.py` + `presets.db` — osobna baza presetów konfiguracji robota
- `drills.py`, `exercises.py`, `training.py` — CRUD dla odpowiednich encji (file-based JSON + SQLite hybryd)
- `players.py` — thin wrapper nad `db.py`, walidacja, cascade delete
- `audio.py` — dźwięki WAV przez `aplay` (pliki w `backend/sounds/`)
- `models.py` — Pydantic models (Ball, ScenarioIn, DrillIn, TrainingStep, etc.)

### Frontend

- **Vue 3 CDN** — `frontend/index.html` (~5000 linii), brak build tooling, brak Vue Router
- **Nawigacja:** tab-based przez `page` ref z `v-show` (NIE `v-if` — zachowuje stan)
- **Widoki:** scenarios, connect, drills, training, exercises, camera, logs, calibration
- **Komunikacja:** hybrid WebSocket (real-time events) + REST (CRUD)
- **Stan:** 100+ reactive refs w `setup()`, computed properties, watchers
- **i18n:** `t(key)` dla UI (`i18n.js`), `tc(type, key)` dla treści (`content_i18n.js`), 5 języków (PL/EN/DE/FR/ZH)
- **CSS:** dark theme (`style.css`), mobile-first, max-width 680px, safe-area insets
- **PWA:** `manifest.json` (standalone, no icons yet)

**UWAGA:** `t()` zarejestrowana jako `app.config.globalProperties.t` — NIE zwracaj z `setup()`, bo Vue 3 prod compiler przesłoni ją zmienną v-for!

### Bazy danych i storage

**SQLite `robopong.db` — tabele:**
| Tabela | Opis |
|--------|------|
| scenarios | proste kontenery drilli (name, balls JSON, repeat) |
| players | profile graczy (name, handedness, lang) |
| user_trainings | treningi użytkownika (name, steps JSON) |
| training_history | historia sesji (status, elapsed, steps, notes, comment) |
| recordings_meta | metadane nagrań MP4 (player, step, duration, size) |
| voice_notes | notatki głosowe WebM (player, step, duration) |
| ball_landings | pozycje lądowania piłek (player, drill, x, y) |
| ball_exploration | eksploracja parametrów piłki (pełne parametry + ocena) |
| favorites | ulubione per gracz (training/drill/exercise) |
| drill_folders | foldery drilli (legacy, backward compat) |
| drills | drille (legacy, backward compat) |

**SQLite `presets.db`:** presety kalibracji robota

**File-based JSON:**
| Plik | Opis |
|------|------|
| `drills_default.json` + `.drills_user.json` | factory drille + user overrides/custom |
| `exercises_default.json` + `.exercises_user.json` | factory ćwiczenia + user duration overrides |
| `trainings_default.json` | factory treningi (readonly) |
| `.calibration.json` | kalibracja per-device (keyed by address) |
| `.last_device` | ostatnio połączone urządzenie |

## Mapa API

### REST Endpoints

```
# System
GET  /api/deploy-time
GET  /api/volume
PUT  /api/volume
POST /api/volume/test

# Kalibracja
GET  /api/calibration
PUT  /api/calibration

# Presety
GET    /api/presets
POST   /api/presets
PUT    /api/presets/{id}
PUT    /api/presets/{id}/default
DELETE /api/presets/{id}

# Scenariusze
GET    /api/scenarios
GET    /api/scenarios/{id}
POST   /api/scenarios
PUT    /api/scenarios/{id}
DELETE /api/scenarios/{id}

# Drille
GET    /api/drills/tree
GET    /api/drills/export
GET    /api/drills/{id}
POST   /api/drills
PUT    /api/drills/{id}
PUT    /api/drills/{id}/count
PUT    /api/drills/{id}/reset
DELETE /api/drills/{id}
POST   /api/drills/reset-all
POST   /api/drills/folders
PUT    /api/drills/folders/{id}
PUT    /api/drills/folders/reorder
DELETE /api/drills/folders/{id}
PUT    /api/drills/reorder

# Cwiczenia
GET  /api/exercises
PUT  /api/exercises/{id}/duration
POST /api/exercises/reset-all

# Treningi
GET    /api/trainings
GET    /api/trainings/{id}
POST   /api/trainings
PUT    /api/trainings/{id}
DELETE /api/trainings/{id}
POST   /api/trainings/{id}/duplicate

# Historia treningow
GET    /api/training-history
GET    /api/training-history/{id}
PUT    /api/training-history/{id}/comment
DELETE /api/training-history/{id}

# Gracze
GET    /api/players
GET    /api/players/{id}
POST   /api/players
PUT    /api/players/{id}
DELETE /api/players/{id}
GET    /api/players/{id}/stats
GET    /api/players/{id}/history
GET    /api/players/{id}/recordings
GET    /api/players/{id}/favorites
POST   /api/players/{id}/favorites
DELETE /api/players/{id}/favorites

# Nagrania
GET    /api/recordings
GET    /api/recordings/compare
GET    /api/recordings/info
GET    /api/recordings/download-zip
GET    /api/recordings/{player_id}/{filename}
DELETE /api/recordings/{player_id}/{filename}

# Notatki glosowe
POST   /api/voice-notes
GET    /api/voice-notes
GET    /api/voice-notes/{id}/audio
DELETE /api/voice-notes/{id}

# Ball landings
POST   /api/ball-landings
GET    /api/ball-landings
DELETE /api/ball-landings/{id}

# Ball exploration
POST   /api/ball-exploration
GET    /api/ball-exploration
DELETE /api/ball-exploration/{id}
```

### WebSocket Protocol (`/ws`)

**Client → Server** (`action` field):
```
# Połączenie / urządzenie
scan, connect, disconnect, usb_scan, usb_connect, usb_disconnect, reset_ble, set_simulation

# Sterowanie robotem (wymaga roli CONTROLLER)
set_ball, throw, throw_ball, stop, begin_calibration
run_scenario, run_drill, run_drill_solo, run_exercise_solo, run_step_solo

# Sterowanie treningiem
run_training, stop_training, pause_training, resume_training, skip_training
training_note, set_next_percent

# Sesje
request_takeover, cancel_takeover, respond_takeover, release_control
```

**Server → Client** (`type` field):
```
# Status
status, scan_result, usb_ports, calibration_loaded, usb_connected

# Sesje
session_role, sessions, takeover_request, takeover_response

# Drill / trening
training_info, training_countdown, training_step, training_drill_progress
training_exercise_progress, training_step_done, training_pause
training_paused, training_resumed, training_skipped, training_percent_changed
training_ended

# Historia i nagrania
history_created, history_updated, recording_started, recording_saved

# System
server_log, info, error, reconnecting, robot_response
```

## Mapa projektu

```
robopong-app/
├── start.sh                    # dev server (port 8000)
├── deploy.sh                   # prod deploy script (polling CI)
├── CLAUDE.md                   # instrukcje dla Claude Code
│
├── .claude/
│   └── commands/
│       ├── task.md             # /task — tworzenie GitHub Issues
│       └── tasks.md            # /tasks — wyświetlanie boardu Issues
│
├── backend/                    # FastAPI + robot control
│   ├── main.py         (1152) # REST API + WebSocket /ws + static files
│   ├── robot.py         (418) # Robot: orkiestracja połączenia, komendy, drill loop
│   ├── transport.py     (364) # ABC RobotTransport → BLE / USB / Simulation
│   ├── db.py            (927) # SQLite: 11 tabel (players, history, recordings, ...)
│   ├── presets.py         (74) # SQLite: presety konfiguracji robota
│   ├── drills.py         (284) # CRUD drilli (file-based JSON)
│   ├── exercises.py       (80) # CRUD ćwiczeń (file-based JSON)
│   ├── training.py       (532) # TrainingRunner + CRUD treningów (file + SQLite)
│   ├── recordings.py     (197) # Recorder: ffmpeg MJPEG → MP4
│   ├── players.py         (39) # profile graczy (wrapper nad db.py)
│   ├── models.py          (66) # Pydantic: Ball, ScenarioIn, DrillIn, TrainingStep
│   ├── audio.py           (40) # dźwięki treningowe (aplay WAV)
│   ├── cli.py            (209) # CLI do sterowania robotem
│   ├── *_default.json          # domyślne dane: drills, exercises, trainings
│   ├── sounds/                 # pliki WAV (beepy, countdown, training events)
│   ├── requirements.txt        # zależności produkcyjne
│   ├── requirements-test.txt   # zależności testowe (pytest, httpx)
│   └── tests/                  # 196 testów (pytest)
│       ├── conftest.py                # shared fixtures
│       ├── test_api.py                # integracja: scenariusze, kalibracja, presety
│       ├── test_api_drills.py         # integracja: CRUD drilli
│       ├── test_api_training.py       # integracja: CRUD treningów
│       ├── test_api_exercises.py      # integracja: exercises
│       ├── test_history_enhanced.py   # integracja: historia treningów
│       ├── test_recordings_enhanced.py # integracja: nagrania
│       ├── test_db.py                 # unit: SQLite
│       ├── test_presets.py            # unit: presety
│       ├── test_drills.py             # unit: drills storage
│       ├── test_exercises.py          # unit: exercises storage
│       ├── test_training_storage.py   # unit: training storage
│       ├── test_transport.py          # unit: transport layer
│       └── test_models.py            # unit: Pydantic validation
│
├── frontend/                   # Vue 3 (CDN, SPA)
│   ├── index.html       (4996) # cała aplikacja Vue (single file)
│   ├── style.css         (561) # dark theme, mobile-first CSS
│   ├── i18n.js           (603) # tłumaczenia UI (PL/EN/DE/FR/ZH)
│   ├── content_i18n.js   (526) # tłumaczenia treści (ćwiczenia, drille, treningi)
│   ├── manifest.json           # PWA manifest
│   ├── drills_default.json     # domyślne drille (kopia frontend)
│   └── img/                    # SVG ikony (height, oscillation, rotation)
│
├── re/                         # reverse engineering protokołu (16MB)
│   ├── ANDROID_APP_RE.md       # RE aplikacji Android
│   ├── WINDOWS_APP_RE.md       # RE aplikacji Windows
│   ├── IOS_APP_RE.md           # RE aplikacji iOS
│   ├── BUSINESS_LOGIC_COMPLETE.md # wspólna logika, formuły
│   ├── PROTOCOL_RE.md          # protokół komunikacji
│   └── convert_drills.py + raw data  # ekstrakcja drilli z oryginalnych app
│
├── docs/                       # dokumentacja
│   ├── protocol.md             # protokół robota
│   └── ux-flow.html            # diagram UX flow
│
└── .github/workflows/ci.yml   # GitHub Actions CI
```

> **UWAGA:** Mapa musi być aktualizowana przy istotnych zmianach struktury — nowy moduł, nowy katalog, usunięcie pliku. Drobne zmiany wewnątrz istniejących plików nie wymagają aktualizacji.

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

## Claude Code Setup

### Slash commands (`.claude/commands/`)
- `/task [opis]` — tworzy GitHub Issue z priorytetem (domyślnie `sredni`)
  - Format: `gh issue create --repo tomekniemczyk/robopong-app --title "..." --body "..." --label "backlog,PRIORYTET"`
- `/tasks` — wyświetla board z GitHub Issues (backlog / w-toku / gotowe)

### Używane pluginy (relevantne dla projektu)
| Plugin | Zastosowanie w projekcie |
|--------|--------------------------|
| `commit-commands` | `/commit` — commitowanie zmian |
| `playwright` | Testowanie UI przez browser automation |
| `frontend-design` | Projektowanie komponentów Vue |
| `code-simplifier` | Refaktoring po implementacji |
| `claude-md-management` | Audyt i update tego pliku |
| `firecrawl` | Research dokumentacji, web scraping |

### Memory — konwencje
Pamięć trwała w `~/.claude/projects/.../memory/`:
- `MEMORY.md` — indeks plików memory
- `project_robopong.md` — kontekst, architektura, protokół, kalibracja, RE docs
- `feedback_tasks.md` — zadania na GitHub Issues (nie TASKS.md)
- `feedback_calibration.md` — silniki stop po rzucie, bez auto-rozgrzewki, centrum=150
- `feedback_workflow.md` — commit na main, worktree, rebase + force-with-lease

Zasady:
- Każde nowe ustalenie dot. protokołu/wartości/UX → zapisuj w memory i CLAUDE.md
- Ustalenia z testów na żywo mają priorytet nad dokumentacją RE

## Zasady pracy

### Git workflow (OBOWIĄZKOWE)
- **Commituj prosto na `main`** — bez feature branchy, bez PRów
- **ZAWSZE pracuj w worktree** (`git worktree add /tmp/robopong-work HEAD`) — **NIGDY nie edytuj plików bezpośrednio w głównym katalogu roboczym** (`/home/robopong/robopong-app`)
- Przy każdym nowym zadaniu — twórz **nowy worktree od aktualnego main** (`git pull` + `git worktree add`), nigdy nie reużywaj starego
- **Przed pushem ZAWSZE rebase na main**: `git pull --rebase origin main`
- **Konflikty przy rebase: ZAWSZE rozwiązuj logicznie** — przeczytaj obie strony konfliktu, zrozum intencję obu zmian, scal je zachowując funkcjonalność obu. NIGDY nie wybieraj ślepo "ours" ani "theirs". Po rozwiązaniu: `git add` + `git rebase --continue`
- **Push z `--force-with-lease`**: `git push --force-with-lease origin main` — bezpieczny force push, chroni przed nadpisaniem cudzych commitów
- Pełna sekwencja po pracy w worktree: commit → `git checkout main` → `git pull --rebase origin main` → rozwiąż konflikty → `git push --force-with-lease origin main` → `git worktree remove`
- Nie używaj `/commit-push-pr` — tylko `/commit` + push na main

> ⚠️ **KRYTYCZNE — równoległe sesje Claude:**
> Projekt jest rozwijany równolegle w wielu sesjach Claude jednocześnie. Każda sesja może wprowadzać zmiany do tych samych plików (zwłaszcza `frontend/index.html`). Przy rebase **OBOWIĄZKOWO**:
> 1. Uruchom `git diff HEAD origin/main` przed rebase — sprawdź co zmieniły inne sesje
> 2. Przy każdym konflikcie otwórz **oba** pliki (ours i theirs) i ręcznie zweryfikuj że żadna funkcja, przycisk ani fragment kodu nie zniknął
> 3. Po rebase uruchom `git diff HEAD~N HEAD` i przejrzyj **cały diff** — upewnij się że własne zmiany są obecne i nie nadpisały cudzych
> 4. Jeśli nie ma konfliktu ale plik był dotknięty przez obie strony — mimo to sprawdź wynik wizualnie
> Przykład błędu: commit `ba059c7` nadpisał nawigację (`navigateToDrill`) bo rebase nie wykrył konfliktu w dużym pliku HTML

### Zarządzanie zadaniami (OBOWIĄZKOWE)
- Gdy użytkownik mówi "dodaj zadanie", "nowe zadanie", "task:", "TODO:" — **zawsze** twórz GitHub Issue
- Repozytorium: `tomekniemczyk/robopong-app`
- Komenda: `gh issue create --repo tomekniemczyk/robopong-app --title "..." --body "..." --label "backlog,PRIORYTET"`
- Priorytety (etykiety): `wysoki`, `sredni`, `niski` — domyślnie `sredni`
- Nowe zadania: etykieta `backlog`

### Spójność UI — ikony i konwencje (OBOWIĄZKOWE)
- **Czas/timer:** zawsze `⏱` (U+23F1) — drill config, drill popup, training overlay
- **Nagrywanie:** zawsze `🎥` + czerwony REC z pulsem (`recBlink`)
- **Piłki:** zawsze `tr.balls_label` z i18n, format `thrown/total`
- **Pauza/Stop/Play:** `⏸` / `⏹` / `▶` — te same znaki w całej aplikacji
- **Notatki:** `💬`, **Mikrofon:** `🎙`
- Przy dodawaniu nowej ikony — sprawdź czy istnieje już konwencja w systemie i użyj tej samej
- Fonty w overlay'ach: kluczowe dane (counter, czas) muszą być czytelne z 3m (~28px+)

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

### Aktualizacja mapy projektu (OBOWIĄZKOWE)
- Przy dodaniu/usunięciu pliku źródłowego, modułu lub katalogu — zaktualizuj sekcję "Mapa projektu" w CLAUDE.md
- Przy zmianie liczby linii o >20% w kluczowym pliku — zaktualizuj liczbę w nawiasie
- Nie aktualizuj mapy przy drobnych zmianach wewnątrz istniejących plików
