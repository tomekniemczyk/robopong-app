# AcePad

Aplikacja do sterowania robotami pingpongowymi, by **[tthub.pl](https://tthub.pl)**.

## O projekcie

**AcePad** zastępuje oficjalną aplikację Newgy dla robota **Donic Robopong 3050XL** i zapewnia pełną kontrolę nad robotem — regulację częstotliwości, kąta, prędkości, trybów ćwiczeń itd.

## Robot

- **Model:** Donic Robopong 3050XL
- **Komunikacja:** BLE (Bluetooth Low Energy) + USB FTDI

## Architektura

- **Backend:** FastAPI + Bleak (BLE) + pyserial (USB), port 8000 (dev) / 8001 (prod)
- **Frontend:** Vue 3 CDN, `frontend/index.html`
- **Serwer produkcyjny:** `10.0.0.45`

## Jak uruchomić

```bash
./start.sh
```

Otwórz `http://localhost:8000` w przeglądarce.

## Testy

```bash
cd backend
venv/bin/pip install -r requirements-test.txt
venv/bin/pytest
```
