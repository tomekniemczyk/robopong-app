#!/usr/bin/env python3
"""Manual drill tester — runs drills from command line, logs all robot commands.

Usage:
    # Simulation mode (no robot needed)
    python test_drill_manual.py --sim

    # BLE connection
    python test_drill_manual.py --ble AA:BB:CC:DD:EE:FF

    # USB connection
    python test_drill_manual.py --usb /dev/ttyUSB0

    # Run specific drill from drills_default.json
    python test_drill_manual.py --sim --drill "Forehand Warmup" --count 5

    # Run with custom ball
    python test_drill_manual.py --sim --top 120 --bot 0 --osc 150 --height 142 --rot 150

    # Verify command format only (dry run, prints commands)
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

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robot import Robot
from transport import SimulationTransport


# ═══════════════════════════════════════════════════════════════════════════════
# REFERENCE: Original Newgy app formulas (from RE analysis)
# ═══════════════════════════════════════════════════════════════════════════════

def original_getMotorSpeed(pct, min_s=28, max_s=210):
    if pct == 0: return 0
    if pct < 0: return int(max_s * (pct / 100))
    return int(min_s + (max_s - min_s) * (pct / 100))

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
        # Color-code by command type
        colors = {
            "H": "\033[91m",    # red
            "B": "\033[93m",    # yellow
            "A": "\033[92m",    # green
            "T": "\033[96m",    # cyan
            "wTA": "\033[95m",  # magenta
            "END": "\033[94m",  # blue
            "Z": "\033[90m",    # gray
            "F": "\033[90m",
            "I": "\033[90m",
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

        # Verify B/A command format
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
            print(f"\n\033[92mAll {len(ball_cmds)} ball commands have correct format (19 chars, no spaces)\033[0m")


# ═══════════════════════════════════════════════════════════════════════════════
# DRILL RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

async def run_drill(robot, logger, balls, count=10, repeat=1, percent=100, mode=None):
    """Run a drill and wait for completion."""
    if mode:
        robot.drill_mode = mode

    effective = robot._effective_drill_mode()
    print(f"\nDrill: {len(balls)} ball(s), count={count}, repeat={repeat}, "
          f"percent={percent}%, mode={effective}")
    print(f"{'='*60}")

    for i, b in enumerate(balls):
        ref_cmd = original_build_B(b["top_speed"], b["bot_speed"],
                                    b["oscillation"], b["height"], b["rotation"])
        print(f"  Ball {i+1}: top={b['top_speed']} bot={b['bot_speed']} "
              f"osc={b['oscillation']} h={b['height']} rot={b['rotation']} "
              f"wait={b['wait_ms']}ms")
        print(f"          Reference B: {ref_cmd}")

    print(f"{'='*60}")
    print("Commands sent:\n")

    events = []
    def on_event(etype, data):
        if etype == "drill_progress":
            events.append(data)
            print(f"  {'':7s}  \033[97m⚡ ball {data.get('ball')}/{data.get('total')} "
                  f"(thrown: {data.get('thrown')})\033[0m")
        elif etype == "drill_ended":
            print(f"  {'':7s}  \033[97m✓ drill ended\033[0m")

    robot.add_listener(on_event)

    await robot.run_drill(balls, repeat=repeat, count=count, percent=percent,
                          skip_warmup=True, emit_countdown=False)

    # Wait for drill to complete
    total_balls = count if count > 0 else len(balls) * (repeat if repeat > 0 else 999)
    max_wait = min(total_balls * 3 + 5, 60)
    await asyncio.sleep(max_wait)

    robot.remove_listener(on_event)
    logger.dump_summary()
    print(f"\nBalls thrown: {len(events)}")


# ═══════════════════════════════════════════════════════════════════════════════
# VERIFY / COMPARE MODE
# ═══════════════════════════════════════════════════════════════════════════════

def verify_format():
    """Verify B/A command format against original app (no robot needed)."""
    robot = Robot()
    robot.firmware = 701
    robot.robot_version = 2

    test_cases = [
        ("Topspin FH", 120, 0, 164, 116, 150),
        ("Topspin BH", 120, 0, 136, 116, 150),
        ("Backspin", -20, 100, 150, 142, 150),
        ("Heavy backspin", -12, 100, 150, 116, 150),
        ("No spin", 50, 50, 150, 142, 150),
        ("Fast topspin", 149, -12, 150, 142, 150),
        ("Max speed", 210, 0, 150, 183, 150),
        ("Zero speed", 0, 0, 150, 142, 150),
        ("Both negative", -100, -80, 150, 142, 150),
        ("Extreme osc", 100, 50, 127, 75, 90),
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
            # Show field-by-field diff
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
    """Compare all default drill commands with original app."""
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
    conn.add_argument("--sim", action="store_true", help="Simulation mode (no robot)")
    conn.add_argument("--ble", metavar="ADDR", help="BLE address (AA:BB:CC:DD:EE:FF)")
    conn.add_argument("--usb", metavar="PORT", help="USB port (/dev/ttyUSB0)")
    conn.add_argument("--verify", action="store_true", help="Verify command format (dry run)")
    conn.add_argument("--compare", action="store_true", help="Compare all drills vs original")

    parser.add_argument("--drill", help="Drill name from drills_default.json")
    parser.add_argument("--top", type=int, default=120, help="Top motor raw (default: 120)")
    parser.add_argument("--bot", type=int, default=0, help="Bottom motor raw (default: 0)")
    parser.add_argument("--osc", type=int, default=150, help="Oscillation raw (default: 150)")
    parser.add_argument("--height", type=int, default=142, help="Height raw (default: 142)")
    parser.add_argument("--rot", type=int, default=150, help="Rotation raw (default: 150)")
    parser.add_argument("--wait", type=int, default=1500, help="Wait ms (default: 1500)")
    parser.add_argument("--count", type=int, default=5, help="Ball count (default: 5)")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat (0=infinite, default: 1)")
    parser.add_argument("--percent", type=int, default=100, help="Tempo percent (default: 100)")
    parser.add_argument("--mode", choices=["sync", "async", "auto"], default="auto",
                        help="Drill mode (default: auto)")

    args = parser.parse_args()

    # Verify / compare modes (no connection needed)
    if args.verify:
        ok = verify_format()
        sys.exit(0 if ok else 1)
    if args.compare:
        ok = compare_drills()
        sys.exit(0 if ok else 1)

    # Create robot
    robot = Robot()

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
    elif args.usb:
        print(f"Connecting USB: {args.usb}...")
        ok = await robot.connect_usb(args.usb)
        if not ok:
            print("USB connection failed!")
            sys.exit(1)
        print(f"Connected! FW={robot.firmware}, Version={robot.robot_version}")
    else:
        print("Specify connection: --sim, --ble ADDR, or --usb PORT")
        print("Or use: --verify, --compare")
        sys.exit(1)

    if args.mode != "auto":
        robot.drill_mode = args.mode

    logger = CommandLogger(robot)

    # Build ball list
    if args.drill:
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
            sys.exit(1)
        balls = found["balls"]
        print(f"Loaded drill: {found['name']} ({len(balls)} ball(s))")
    else:
        balls = [{
            "top_speed": args.top, "bot_speed": args.bot,
            "oscillation": args.osc, "height": args.height,
            "rotation": args.rot, "wait_ms": args.wait,
        }]

    try:
        await run_drill(robot, logger, balls, count=args.count,
                       repeat=args.repeat, percent=args.percent)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await robot.stop()
        if args.ble or args.usb:
            await robot.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
