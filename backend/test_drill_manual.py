#!/usr/bin/env python3
"""Manual drill tester — runs drills from command line, logs all robot commands.

Usage:
    # Simulation mode (no robot needed)
    python test_drill_manual.py --sim

    # BLE connection — auto-loads calibration, 3 test balls → confirm → full drill
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9

    # Use calibration params from .calibration.json
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --cal

    # Run named drill from built-in library
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --drill fh_flick_bs

    # Run with custom ball params
    python test_drill_manual.py --ble FC:0F:E7:6D:01:B9 --top 161 --bot 0 --osc 144 --height 150 --rot 150

    # USB connection
    python test_drill_manual.py --usb /dev/ttyUSB0

    # Verify command format only (dry run)
    python test_drill_manual.py --verify

    # Compare our output vs original app (reference check)
    python test_drill_manual.py --compare
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robot import Robot
from transport import SimulationTransport


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN DRILL LIBRARY (przetestowane na FC:0F:E7:6D:01:B9, 2026-04-07/10)
# ═══════════════════════════════════════════════════════════════════════════════

DRILLS = {
    "cal":         {"name": "Calibration (center table)", "top": 161, "bot":  0,  "osc": 144, "h": 150, "rot": 150, "wait": 2500},
    "fh_flick_bs": {"name": "FH Flick vs Backspin",       "top": -10, "bot": 90,  "osc": 137, "h": 117, "rot": 150, "wait": 2500},
    "fh_flick_ns": {"name": "FH Flick vs No-Spin",        "top":  58, "bot": 58,  "osc": 137, "h": 119, "rot": 150, "wait": 2500},
    "fh_flick_ts": {"name": "FH Flick vs Topspin",        "top":  60, "bot": 55,  "osc": 137, "h": 120, "rot": 150, "wait": 2500},
    "wide_fh_ns":  {"name": "Max Wide FH No-Spin",        "top":  58, "bot": 58,  "osc": 127, "h": 134, "rot": 147, "wait": 2500},
    "wide_bh_ns":  {"name": "Max Wide BH No-Spin",        "top":  60, "bot": 60,  "osc": 173, "h": 134, "rot": 147, "wait": 2500},
    "net_touch":   {"name": "Net Touch Recovery",         "top":  55, "bot": 55,  "osc": 137, "h": 125, "rot": 150, "wait": 2500},
    "ultra_short": {"name": "Ultra-Short Drop",           "top":  45, "bot": 45,  "osc": 140, "h": 116, "rot": 150, "wait": 2500},
}

DEFAULT_CAL = {"top_speed": 161, "bot_speed": 0, "oscillation": 150, "height": 183, "rotation": 150, "wait_ms": 1000}


def load_calibration(addr: str) -> dict:
    """Load calibration for device address from .calibration.json."""
    cal_file = Path(__file__).parent / ".calibration.json"
    if not cal_file.exists():
        print("  [cal] No .calibration.json — using default")
        return dict(DEFAULT_CAL)
    data = json.loads(cal_file.read_text())
    if addr in data:
        print(f"  [cal] Loaded for {addr}")
        return data[addr]
    if "_default_" in data:
        print(f"  [cal] No entry for {addr} — using _default_")
        return data["_default_"]
    print("  [cal] No calibration found — using default")
    return dict(DEFAULT_CAL)


# ═══════════════════════════════════════════════════════════════════════════════
# REFERENCE: Original Newgy app formulas (from RE analysis)
# ═══════════════════════════════════════════════════════════════════════════════

def original_getMotorPWM(raw, speed_cal=0):
    return round(abs(raw) * 4.016) + speed_cal

def original_getLEDS(top, bot):
    diff = top - bot
    if diff == 0: return 0
    ratio = abs(diff) / 360.0
    if ratio <= 0.10: level = 1
    elif ratio <= 0.50: level = 2
    elif ratio <= 0.75: level = 3
    else: level = 4
    return level + 4 if diff > 0 else level

def original_build_B(top, bot, osc, h, rot, speed_cal=0):
    """Build B command as the ORIGINAL app would."""
    dt = 1 if top < 0 else 0
    db = 1 if bot < 0 else 0
    pt = original_getMotorPWM(top, speed_cal)
    pb = original_getMotorPWM(bot, speed_cal)
    leds = original_getLEDS(top, bot)
    return f"B{dt}{pt:03d}{db}{pb:03d}{osc:03d}{h:03d}{rot:03d}{leds}"


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

class CommandLogger:
    """Wraps Robot._write to log all commands with timestamps."""

    def __init__(self, robot):
        self.robot = robot
        self.commands = []
        self.start_time = time.time()
        self._orig_write = robot._write

        async def logged_write(cmd):
            elapsed = time.time() - self.start_time
            self.commands.append((elapsed, cmd))
            self._print_cmd(elapsed, cmd)
            await self._orig_write(cmd)

        robot._write = logged_write

    def _print_cmd(self, elapsed, cmd):
        colors = {
            "H":   "\033[91m",    # red
            "B":   "\033[93m",    # yellow
            "A":   "\033[92m",    # green
            "T":   "\033[96m",    # cyan
            "wTA": "\033[95m",    # magenta
            "END": "\033[94m",    # blue
            "Q":   "\033[92m",    # green
            "Z":   "\033[90m",    # gray
            "F":   "\033[90m",
            "I":   "\033[90m",
        }
        reset = "\033[0m"
        color = "\033[0m"
        for prefix, c in colors.items():
            if cmd.startswith(prefix):
                color = c
                break
        print(f"  {elapsed:7.3f}s  {color}→ {cmd}{reset}")

    def dump_summary(self):
        print(f"\n{'='*60}")
        print(f"Command summary ({len(self.commands)} commands):")
        counts = {}
        for _, cmd in self.commands:
            key = cmd[:1] if cmd[0] in "BATHI" else cmd[:3]
            counts[key] = counts.get(key, 0) + 1
        for key, cnt in sorted(counts.items()):
            print(f"  {key}: {cnt}")

        ball_cmds = [(t, c) for t, c in self.commands
                     if c[0] in ("B", "A") and len(c) > 2]
        errors = []
        for t, cmd in ball_cmds:
            if len(cmd) != 19:
                errors.append(f"  {t:.3f}s: {cmd!r} — wrong length {len(cmd)} (expected 19)")
            if " " in cmd:
                errors.append(f"  {t:.3f}s: {cmd!r} — contains spaces")

        if errors:
            print(f"\n\033[91mFORMAT ERRORS:\033[0m")
            for e in errors:
                print(e)
        else:
            print(f"\n\033[92mAll {len(ball_cmds)} ball commands: correct format (19 chars, no spaces)\033[0m")


# ═══════════════════════════════════════════════════════════════════════════════
# DRILL SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════

async def pre_drill(robot):
    """Clear ball before drill — H×2 like original app."""
    await robot._write("H")
    await asyncio.sleep(0.2)
    await robot._write("H")
    await asyncio.sleep(1.0)


async def test_3_balls(robot, top, bot, osc, h, rot, wait_ms=2500, warmup_s=5):
    """Pre-drill → set ball → warmup → 3 throws → stop. Returns False on safety error."""
    print(f"\n--- TEST: 3 balls ---")
    print(f"  top={top} bot={bot} osc={osc} h={h} rot={rot} wait={wait_ms}ms")

    await pre_drill(robot)

    try:
        params = robot._build_ball_params(top, bot, osc, h, rot)
    except Robot.SafetyError as e:
        print(f"\033[91m  SAFETY ERROR: {e}\033[0m")
        return False

    await robot._write(f"B{params}")
    print(f"  Warmup {warmup_s}s...", end="", flush=True)
    await asyncio.sleep(warmup_s)
    print(" done")

    for i in range(3):
        print(f"  → Throw {i+1}/3")
        await robot._write("T")
        await asyncio.sleep(wait_ms / 1000)

    await robot._write("H")
    print("  Stopped.")
    return True


async def run_full_drill(robot, top, bot, osc, h, rot, wait_ms=2500, count=50, warmup_s=5):
    """Pre-drill → set ball → warmup → throw N balls → stop."""
    print(f"\n--- DRILL: {count} balls ---")

    await pre_drill(robot)

    try:
        params = robot._build_ball_params(top, bot, osc, h, rot)
    except Robot.SafetyError as e:
        print(f"\033[91m  SAFETY ERROR: {e}\033[0m")
        return

    await robot._write(f"B{params}")
    print(f"  Warmup {warmup_s}s...", end="", flush=True)
    await asyncio.sleep(warmup_s)
    print(" done")

    for i in range(count):
        print(f"  → {i+1}/{count}", end="\r", flush=True)
        await robot._write("T")
        await asyncio.sleep(wait_ms / 1000)

    await robot._write("H")
    print(f"\n  Done — {count} balls thrown.")


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFY / COMPARE MODE
# ═══════════════════════════════════════════════════════════════════════════════

def verify_format():
    robot = Robot()
    robot.firmware = 701
    robot.robot_version = 2

    test_cases = [
        ("Topspin FH",     120,   0, 164, 116, 150),
        ("Topspin BH",     120,   0, 136, 116, 150),
        ("Backspin",       -20, 100, 150, 142, 150),
        ("Heavy backspin", -12, 100, 150, 116, 150),
        ("No spin",         50,  50, 150, 142, 150),
        ("Fast topspin",   149, -12, 150, 142, 150),
        ("Max speed",      210,   0, 150, 183, 150),
        ("Zero speed",       0,   0, 150, 142, 150),
        ("Both negative", -100, -80, 150, 142, 150),
        ("Extreme osc",    100,  50, 127,  75,  90),
    ]

    print("B/A Command Format Verification")
    print("="*80)
    print(f"{'Case':<20} {'Our cmd':<24} {'Reference':<24} {'Match'}")
    print("-"*80)

    all_ok = True
    for name, top, bot, osc, h, rot in test_cases:
        our = "B" + robot._build_ball_params(top, bot, osc, h, rot)
        ref = original_build_B(top, bot, osc, h, rot)
        match = our == ref
        status = "\033[92m✓\033[0m" if match else "\033[91m✗\033[0m"
        if not match:
            all_ok = False
        print(f"  {name:<18} {our:<22} {ref:<22} {status}")
        if not match:
            print(f"  {'':18} \033[91mOurs:  {our!r}\033[0m")
            print(f"  {'':18} \033[92mRef:   {ref!r}\033[0m")
            for i, (a, b_char) in enumerate(zip(our, ref)):
                if a != b_char:
                    print(f"  {'':18} \033[91mDiff at pos {i}: ours='{a}' ref='{b_char}'\033[0m")

    print("-"*80)
    if all_ok:
        print("\033[92mAll commands match original app! ✓\033[0m")
    else:
        print("\033[91mMISMATCH DETECTED — fix _build_ball_params! ✗\033[0m")
    return all_ok


def compare_drills():
    robot = Robot()
    robot.firmware = 701
    robot.robot_version = 2

    defaults_path = os.path.join(os.path.dirname(__file__), "drills_default.json")
    if not os.path.exists(defaults_path):
        print(f"Not found: {defaults_path}")
        return False

    with open(defaults_path) as f:
        data = json.load(f)

    total = 0
    mismatches = 0

    for folder in data.get("folders", []):
        print(f"\n📁 {folder['name']}")
        for drill in folder.get("drills", []):
            for i, ball in enumerate(drill["balls"]):
                total += 1
                our = "B" + robot._build_ball_params(
                    ball["top_speed"], ball["bot_speed"],
                    ball["oscillation"], ball["height"], ball["rotation"])
                ref = original_build_B(
                    ball["top_speed"], ball["bot_speed"],
                    ball["oscillation"], ball["height"], ball["rotation"])
                if our != ref:
                    mismatches += 1
                    print(f"  \033[91m✗ {drill['name']} ball {i+1}\033[0m")
                    print(f"    Ours: {our!r}")
                    print(f"    Ref:  {ref!r}")

    print(f"\n{'='*60}")
    print(f"Total balls: {total}, Mismatches: {mismatches}")
    if mismatches == 0:
        print("\033[92mAll drill commands match original! ✓\033[0m")
    else:
        print(f"\033[91m{mismatches} mismatches found! ✗\033[0m")
    return mismatches == 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Manual drill tester for Robopong 3050XL")
    conn = parser.add_mutually_exclusive_group()
    conn.add_argument("--sim",     action="store_true", help="Simulation mode (no robot)")
    conn.add_argument("--ble",     metavar="ADDR",      help="BLE address (AA:BB:CC:DD:EE:FF)")
    conn.add_argument("--usb",     metavar="PORT",      help="USB port (/dev/ttyUSB0)")
    conn.add_argument("--verify",  action="store_true", help="Verify command format (dry run)")
    conn.add_argument("--compare", action="store_true", help="Compare all drills vs original")

    parser.add_argument("--drill",      help=f"Named drill: {', '.join(DRILLS.keys())} — or name from drills_default.json")
    parser.add_argument("--cal",        action="store_true", help="Use calibration params from .calibration.json")
    parser.add_argument("--count",      type=int, default=50,   help="Ball count for full drill (default: 50)")
    parser.add_argument("--warmup",     type=int, default=5,    help="Warmup seconds (default: 5)")
    parser.add_argument("--top",        type=int, default=161,  help="Top motor raw (default: 161)")
    parser.add_argument("--bot",        type=int, default=0,    help="Bottom motor raw (default: 0)")
    parser.add_argument("--osc",        type=int, default=144,  help="Oscillation raw (default: 144)")
    parser.add_argument("--height",     type=int, default=150,  help="Height raw (default: 150)")
    parser.add_argument("--rot",        type=int, default=150,  help="Rotation raw (default: 150)")
    parser.add_argument("--wait",       type=int, default=2500, help="Wait ms between throws (default: 2500)")
    parser.add_argument("--no-confirm", action="store_true",    help="Skip confirmation — run full drill immediately")
    parser.add_argument("--test-only",  action="store_true",    help="Only throw 3 test balls, no full drill")

    args = parser.parse_args()

    # Verify / compare modes (no connection needed)
    if args.verify:
        sys.exit(0 if verify_format() else 1)
    if args.compare:
        sys.exit(0 if compare_drills() else 1)

    # Create robot
    robot = Robot()
    cal = None

    if args.sim:
        robot.enable_simulation()
        print("Mode: SIMULATION")
    elif args.ble:
        print(f"Connecting BLE: {args.ble}...")
        ok = await robot.connect(args.ble)
        if not ok:
            print("BLE connection failed!")
            sys.exit(1)
        print(f"Connected! FW={robot.firmware}, Version={robot.robot_version}")

        # Auto-apply calibration (Q command) after every connect
        cal = load_calibration(args.ble)
        print(f"  [cal] top={cal.get('top_speed',161)} bot={cal.get('bot_speed',0)} "
              f"osc={cal.get('oscillation',150)} h={cal.get('height',183)} rot={cal.get('rotation',150)}")
        await robot.apply_calibration(cal)

    elif args.usb:
        print(f"Connecting USB: {args.usb}...")
        ok = await robot.connect_usb(args.usb)
        if not ok:
            print("USB connection failed!")
            sys.exit(1)
        print(f"Connected! FW={robot.firmware}, Version={robot.robot_version}")
    else:
        print("Specify connection: --sim, --ble ADDR, or --usb PORT")
        print(f"\nBuilt-in drills: {', '.join(DRILLS.keys())}")
        print("Or use: --verify, --compare")
        sys.exit(1)

    logger = CommandLogger(robot)

    # Resolve ball params
    if args.drill:
        if args.drill in DRILLS:
            d = DRILLS[args.drill]
            top, bot, osc, h, rot, wait_ms = d["top"], d["bot"], d["osc"], d["h"], d["rot"], d["wait"]
            print(f"Drill: {d['name']}")
        else:
            defaults_path = os.path.join(os.path.dirname(__file__), "drills_default.json")
            with open(defaults_path) as f:
                data = json.load(f)
            found = None
            for folder in data.get("folders", []):
                for drill in folder.get("drills", []):
                    if drill["name"].lower() == args.drill.lower():
                        found = drill
                        break
            if not found:
                print(f"Drill not found: {args.drill}")
                print(f"Built-in: {', '.join(DRILLS.keys())}")
                sys.exit(1)
            b0 = found["balls"][0]
            top, bot, osc, h, rot = (
                b0["top_speed"], b0["bot_speed"], b0["oscillation"],
                b0["height"], b0["rotation"])
            wait_ms = b0.get("wait_ms", args.wait)
            print(f"Drill: {found['name']}")
    elif args.cal:
        src = cal if cal else load_calibration(args.ble or "")
        top    = src.get("top_speed", 161)
        bot    = src.get("bot_speed", 0)
        osc    = src.get("oscillation", 144)
        h      = src.get("height", 150)
        rot    = src.get("rotation", 150)
        wait_ms = args.wait
        print("Mode: CALIBRATION TEST")
    else:
        top, bot, osc, h, rot, wait_ms = args.top, args.bot, args.osc, args.height, args.rot, args.wait

    print(f"\nParams: top={top} bot={bot} osc={osc} h={h} rot={rot} wait={wait_ms}ms")
    print(f"{'='*60}")
    print("Commands:\n")

    try:
        ok = await test_3_balls(robot, top, bot, osc, h, rot,
                                wait_ms=wait_ms, warmup_s=args.warmup)
        if not ok:
            return

        if args.test_only:
            print("Test-only mode — done.")
        else:
            if not args.no_confirm and not args.sim:
                resp = input(f"\nOK? Run {args.count} balls? [Enter=yes / q=quit]: ").strip().lower()
                if resp == "q":
                    print("Aborted.")
                    return

            await run_full_drill(robot, top, bot, osc, h, rot,
                                 wait_ms=wait_ms, count=args.count, warmup_s=args.warmup)

        logger.dump_summary()

    except KeyboardInterrupt:
        print("\nStopping...")
        await robot._write("H")
    finally:
        await robot.stop()
        if args.ble or args.usb:
            await robot.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
