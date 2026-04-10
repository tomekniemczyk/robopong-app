#!/usr/bin/env python3
"""Manual drill tester — steruje robotem przez WebSocket serwera (identycznie jak web app).

Kalibracja, połączenie BLE, format komend — wszystko przez serwer.
Brak duplikacji logiki z main.py/robot.py.

Użycie:
    # Połącz przez serwer, testuj drill 3 piłkami
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --drill ultra_short --test-only

    # Pełny drill (3 testowe → potwierdzenie → N piłek)
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --drill fh_flick_bs

    # Custom parametry
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --top 45 --bot 45 --osc 140 --height 116 --rot 150

    # Inny port serwera (domyślnie 8000)
    python test_drill_manual.py --server ws://localhost:8001/ws --drill fh_flick_bs

    # Robot już połączony — pomija connect, tylko kalibruje i puszcza
    python test_drill_manual.py --drill ultra_short --test-only
"""

import argparse
import asyncio
import json
import os
import sys
import time

import websockets


# ═══════════════════════════════════════════════════════════════════════════════
# WBUDOWANA BIBLIOTEKA DRILLI
# ═══════════════════════════════════════════════════════════════════════════════

DRILLS = {
    "cal":         {"name": "Calibration (center table)", "top_speed": 161, "bot_speed":  0,  "oscillation": 144, "height": 150, "rotation": 150, "wait_ms": 2500},
    "fh_flick_bs": {"name": "FH Flick vs Backspin",       "top_speed": -10, "bot_speed": 90,  "oscillation": 137, "height": 117, "rotation": 150, "wait_ms": 2500},
    "fh_flick_ns": {"name": "FH Flick vs No-Spin",        "top_speed":  58, "bot_speed": 58,  "oscillation": 137, "height": 119, "rotation": 150, "wait_ms": 2500},
    "fh_flick_ts": {"name": "FH Flick vs Topspin",        "top_speed":  60, "bot_speed": 55,  "oscillation": 137, "height": 120, "rotation": 150, "wait_ms": 2500},
    "wide_fh_ns":  {"name": "Max Wide FH No-Spin",        "top_speed":  58, "bot_speed": 58,  "oscillation": 127, "height": 134, "rotation": 147, "wait_ms": 2500},
    "wide_bh_ns":  {"name": "Max Wide BH No-Spin",        "top_speed":  60, "bot_speed": 60,  "oscillation": 173, "height": 134, "rotation": 147, "wait_ms": 2500},
    "net_touch":   {"name": "Net Touch Recovery",         "top_speed":  55, "bot_speed": 55,  "oscillation": 137, "height": 125, "rotation": 150, "wait_ms": 2500},
    "ultra_short": {"name": "Ultra-Short Drop",           "top_speed":  45, "bot_speed": 45,  "oscillation": 140, "height": 116, "rotation": 150, "wait_ms": 2500},
}


# ═══════════════════════════════════════════════════════════════════════════════
# WS KLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class DrillClient:
    """Cienki klient WebSocket — identyczna ścieżka jak web app."""

    def __init__(self, server_url: str):
        self.url = server_url
        self._ws = None
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._reader_task = None
        self.role = None
        self.connected = False
        self.device = ""

    async def connect(self):
        self._ws = await websockets.connect(self.url, open_timeout=10)
        self._reader_task = asyncio.create_task(self._reader())

        # Odbierz stan początkowy (status + ewentualnie calibration_loaded)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=1)
            except asyncio.TimeoutError:
                break
            t = msg.get("type")
            if t == "status":
                self.role = msg.get("role", "OBSERVER")
                self.connected = msg.get("connected", False)
                self.device = msg.get("device", "")
                break

        print(f"WS: {self.url}  rola={self.role}  robot={'tak' if self.connected else 'nie'} ({self.device or '-'})")

        if self.role not in ("CONTROLLER", "controller"):
            print("Przejmuję kontrolę (force_takeover)...")
            await self._send("force_takeover")
            # Czekaj na session_role z CONTROLLER
            deadline2 = time.monotonic() + 3
            while time.monotonic() < deadline2:
                try:
                    msg = await asyncio.wait_for(self._inbox.get(), timeout=1)
                    if msg.get("type") == "session_role" and msg.get("role") in ("CONTROLLER", "controller"):
                        self.role = "CONTROLLER"
                        break
                except asyncio.TimeoutError:
                    break
            if self.role not in ("CONTROLLER", "controller"):
                self.role = "CONTROLLER"  # zakładamy sukces (force)

    async def close(self):
        if self._reader_task:
            self._reader_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _reader(self):
        """Pochłania wszystkie wiadomości WS i wkłada do kolejki."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                    t = msg.get("type", "")
                    if t == "calibration_loaded":
                        cal = msg.get("cal", {})
                        print(f"  [kalibracja] h={cal.get('height')} osc={cal.get('oscillation')} "
                              f"rot={cal.get('rotation')} top={cal.get('top_speed')}")
                    elif t == "error":
                        print(f"  [błąd] {msg.get('message', msg)}")
                    elif t == "status":
                        new_c = msg.get("connected", False)
                        if new_c != self.connected:
                            self.connected = new_c
                            self.device = msg.get("device", "")
                            print(f"  [status] robot={'podłączony' if self.connected else 'rozłączony'} ({self.device or '-'})")
                    await self._inbox.put(msg)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    async def _send(self, action: str, **kwargs):
        msg = {"action": action, **kwargs}
        await self._ws.send(json.dumps(msg))

    async def robot_connect(self, addr: str):
        """Połącz robota przez serwer — serwer robi BLE + kalibrację R/U/O/Q."""
        print(f"Łączę robota: {addr}...")
        await self._send("connect", address=addr)
        # Czekaj na calibration_loaded (max 30s)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=2)
                if msg.get("type") == "calibration_loaded":
                    self.connected = True
                    self.device = addr
                    print("  Robot połączony, kalibracja załadowana ✓")
                    return True
                if msg.get("type") == "error":
                    print(f"  Błąd połączenia: {msg.get('message')}")
                    return False
            except asyncio.TimeoutError:
                pass
        print("  Timeout przy łączeniu robota")
        return False

    async def apply_cal(self):
        """Wymuś aplikację kalibracji (R/U/O/Q → firmware)."""
        await self._send("apply_calibration")
        await asyncio.sleep(1.5)  # 4 komendy × 0.3s = 1.2s + margines

    async def stop(self):
        await self._send("stop")
        await asyncio.sleep(0.2)

    async def set_ball(self, ball: dict):
        await self._send("set_ball", ball=ball)
        await asyncio.sleep(0.3)

    async def throw(self):
        await self._send("throw")

    async def pre_drill(self):
        """H×2 przed każdym drillem — jak oryginalna aplikacja."""
        await self.stop()
        await self.stop()
        await asyncio.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# DRILL FLOW
# ═══════════════════════════════════════════════════════════════════════════════

async def run_drill(client: DrillClient, ball: dict, count: int, warmup_s: int,
                   test_only: bool, no_confirm: bool):
    wait_s = ball.get("wait_ms", 2500) / 1000

    # Kalibracja — zawsze przed drillem (bezpieczne, idempotentne)
    print("Aplikuję kalibrację (R/U/O/Q)...")
    await client.apply_cal()

    # Pre-drill
    await client.pre_drill()

    # Ustaw piłkę + rozgrzewka
    await client.set_ball(ball)
    print(f"Rozgrzewka {warmup_s}s...", end="", flush=True)
    await asyncio.sleep(warmup_s)
    print(" gotowe")

    # 3 testowe piłki
    print("\n--- TEST: 3 piłki ---")
    for i in range(3):
        print(f"  -> Rzut {i+1}/3")
        await client.throw()
        await asyncio.sleep(wait_s)
    await client.stop()
    print("  Zatrzymano.")

    if test_only:
        print("\nTylko test -- koniec.")
        return

    # Potwierdzenie przed pełnym drillem
    if not no_confirm:
        resp = input(f"\nOK? Uruchomić {count} piłek? [Enter=tak / q=pomiń]: ").strip().lower()
        if resp == "q":
            print("Pominięto.")
            return

    # Pełny drill
    print(f"\n--- DRILL: {count} piłek ---")
    await client.pre_drill()
    await client.set_ball(ball)
    print(f"Rozgrzewka {warmup_s}s...", end="", flush=True)
    await asyncio.sleep(warmup_s)
    print(" gotowe")

    t0 = time.monotonic()
    for i in range(count):
        print(f"  -> {i+1}/{count}", end="\r", flush=True)
        await client.throw()
        await asyncio.sleep(wait_s)
    await client.stop()
    elapsed = time.monotonic() - t0
    print(f"\n  Koniec -- {count} piłek w {elapsed:.0f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Drill tester (WS klient serwera)")
    parser.add_argument("--server",      default="ws://localhost:8001/ws", help="URL serwera WS (domyślnie prod :8001)")
    parser.add_argument("--ble",         metavar="ADDR", help="Adres BLE (pomija jeśli robot już połączony)")
    parser.add_argument("--drill",       help=f"Nazwany drill: {', '.join(DRILLS.keys())}")
    parser.add_argument("--top",         type=int, default=161)
    parser.add_argument("--bot",         type=int, default=0)
    parser.add_argument("--osc",         type=int, default=144)
    parser.add_argument("--height",      type=int, default=150)
    parser.add_argument("--rot",         type=int, default=150)
    parser.add_argument("--wait",        type=int, default=2500, help="ms między rzutami")
    parser.add_argument("--count",       type=int, default=50,   help="Liczba piłek (pełny drill)")
    parser.add_argument("--warmup",      type=int, default=5,    help="Rozgrzewka w sekundach")
    parser.add_argument("--test-only",   action="store_true",    help="Tylko 3 testowe piłki")
    parser.add_argument("--no-confirm",  action="store_true",    help="Bez potwierdzenia przed pełnym drillem")

    args = parser.parse_args()

    # Rozwiąż parametry piłki
    if args.drill:
        if args.drill in DRILLS:
            ball = dict(DRILLS[args.drill])
            print(f"Drill: {ball.pop('name')}")
        else:
            # Szukaj w drills_default.json
            defaults_path = os.path.join(os.path.dirname(__file__), "drills_default.json")
            ball = None
            try:
                data = json.loads(open(defaults_path).read())
                for folder in data.get("folders", []):
                    for d in folder.get("drills", []):
                        if d["name"].lower() == args.drill.lower():
                            b = d["ball"]
                            ball = {
                                "top_speed":   b.get("top_speed", 161),
                                "bot_speed":   b.get("bot_speed", 0),
                                "oscillation": b.get("oscillation", 144),
                                "height":      b.get("height", 150),
                                "rotation":    b.get("rotation", 150),
                                "wait_ms":     b.get("wait_ms", 2500),
                            }
                            print(f"Drill: {d['name']}")
                            break
                    if ball:
                        break
            except Exception as e:
                print(f"Blad ladowania drills_default.json: {e}")
            if not ball:
                print(f"Nieznany drill: {args.drill}")
                print(f"Dostepne: {', '.join(DRILLS.keys())}")
                sys.exit(1)
    else:
        ball = {
            "top_speed":   args.top,
            "bot_speed":   args.bot,
            "oscillation": args.osc,
            "height":      args.height,
            "rotation":    args.rot,
            "wait_ms":     args.wait,
        }

    print(f"Parametry: top={ball['top_speed']} bot={ball['bot_speed']} "
          f"osc={ball['oscillation']} h={ball['height']} rot={ball['rotation']} wait={ball['wait_ms']}ms")
    print("=" * 60)

    client = DrillClient(args.server)
    try:
        await client.connect()

        # Połącz robota jeśli podano adres i nie jest połączony (lub inny robot)
        if args.ble and (not client.connected or client.device != args.ble):
            ok = await client.robot_connect(args.ble)
            if not ok:
                sys.exit(1)
        elif not client.connected:
            print("Robot nie jest połączony. Uzyj --ble ADDR zeby połączyć.")
            sys.exit(1)

        await run_drill(client, ball,
                        count=args.count,
                        warmup_s=args.warmup,
                        test_only=args.test_only,
                        no_confirm=args.no_confirm)
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrzerwano.")
