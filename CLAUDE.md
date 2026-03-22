# Instrukcje dla Claude — robopong-app

## Kontekst projektu

Ten projekt to **autorska aplikacja zastępująca Newgy** dla robota pingpongowego Donic Robopong 3050XL.
Celem jest stworzenie własnego klienta, który komunikuje się z robotem i daje pełną kontrolę nad jego parametrami.

## Architektura

- **Backend:** FastAPI + Bleak (BLE) + pyserial (USB FTDI), plik `backend/main.py` + `backend/robot.py`
- **Frontend:** Vue 3 CDN, jeden plik `frontend/index.html`
- **Serwer produkcyjny:** `192.168.1.45`, user `robopong`, port `8001`
- **Deploy:** `ssh robopong@192.168.1.45` → `git pull` → restart uvicorn
- **Kamera:** motion, port `8081`

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
