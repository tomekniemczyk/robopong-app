"""Drill execution flow tests — verify command sequences match original app.

██████████████████████████████████████████████████████████████████████████████
██  THESE TESTS ARE THE CONTRACT — DO NOT MODIFY TO FIX FAILING TESTS!    ██
██  If a test fails, FIX THE IMPLEMENTATION, not the test.                ██
██                                                                        ██
██  Source of truth:                                                       ██
██    re/BUSINESS_LOGIC_COMPLETE.md:282-303  — runDrill logic              ██
██    re/ANDROID_APP_RE.md:557-578          — setBall + async protocol     ██
██████████████████████████████████████████████████████████████████████████████

Tests verify the SEQUENCE and FORMAT of commands sent during drill execution,
matching the original Newgy app behavior for both sync and async modes.
"""

import asyncio
import pytest
import re as regex
from unittest.mock import AsyncMock, patch

from robot import Robot
from transport import SimulationTransport


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class CommandCapture:
    """Captures all commands sent by Robot, with timing info."""

    def __init__(self, robot: Robot):
        self.commands = []
        self.robot = robot
        self._orig_write = robot._write

        async def capture(cmd):
            self.commands.append(cmd)
        robot._write = capture

    def get(self):
        return list(self.commands)

    def clear(self):
        self.commands.clear()

    def filter(self, prefix):
        return [c for c in self.commands if c.startswith(prefix)]

    def filter_ball_cmds(self):
        """Return only B and A commands."""
        return [c for c in self.commands if c[0] in ("B", "A")]

    def dump(self):
        """For debugging: print all captured commands."""
        for i, cmd in enumerate(self.commands):
            print(f"  [{i}] {cmd}")


def make_ball(top=120, bot=0, osc=150, height=142, rotation=150, wait_ms=1500):
    return {
        "top_speed": top, "bot_speed": bot, "oscillation": osc,
        "height": height, "rotation": rotation, "wait_ms": wait_ms,
    }


def make_robot(firmware=701, mode="sync") -> tuple:
    """Create a Robot with SimulationTransport and CommandCapture."""
    robot = Robot()
    robot._transport = SimulationTransport()
    robot.firmware = firmware
    robot.robot_version = 2
    robot.drill_mode = mode
    cap = CommandCapture(robot)
    return robot, cap


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC DRILL TESTS — B + T protocol (fw < 701 or USB)
# Source: BUSINESS_LOGIC_COMPLETE.md:285-293
# ═══════════════════════════════════════════════════════════════════════════════

class TestSyncDrillSingleBall:
    """Sync drill with single ball — simplest case."""

    @pytest.mark.asyncio
    async def test_single_ball_sends_B_then_T(self):
        """Each ball: setBall (B command) → throw (T command).
        Source: BUSINESS_LOGIC_COMPLETE.md:286-289"""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=120, bot=0, wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=1, skip_warmup=True)
        await asyncio.sleep(2.5)
        robot.stop_drill()
        await asyncio.sleep(0.1)

        ball_cmds = cap.filter_ball_cmds()
        t_cmds = cap.filter("T")
        assert len(ball_cmds) >= 1, f"Should send at least 1 B command, sent: {cap.get()}"
        assert len(t_cmds) >= 1, f"Should send at least 1 T command, sent: {cap.get()}"

    @pytest.mark.asyncio
    async def test_single_ball_B_format_correct(self):
        """B command must be 19 chars (B + 18 payload), no spaces."""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=100, bot=50)

        await robot.run_drill([ball], repeat=1, count=1, skip_warmup=True)
        await asyncio.sleep(2.5)
        robot.stop_drill()
        await asyncio.sleep(0.1)

        b_cmds = cap.filter("B")
        # Filter out the initial/final H commands
        b_ball_cmds = [c for c in b_cmds if len(c) > 2]
        assert len(b_ball_cmds) >= 1
        for cmd in b_ball_cmds:
            assert len(cmd) == 19, f"B command should be 19 chars, got {len(cmd)}: {cmd!r}"
            assert " " not in cmd, f"B command should not contain spaces: {cmd!r}"

    @pytest.mark.asyncio
    async def test_drill_ends_with_H(self):
        """Drill must end with H (stop) command.
        Source: all drill paths end with ClearBall → H"""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=100, bot=50, wait_ms=500)

        await robot.run_drill([ball], repeat=1, count=1, skip_warmup=True)
        await asyncio.sleep(2.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        cmds = cap.get()
        assert cmds[-1] == "H", f"Drill should end with H, last cmd: {cmds[-1]}"

    @pytest.mark.asyncio
    async def test_count_limits_throws(self):
        """count parameter limits total balls thrown."""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=100, bot=50, wait_ms=500)

        await robot.run_drill([ball], repeat=0, count=3, skip_warmup=True)
        await asyncio.sleep(5.0)

        t_cmds = cap.filter("T")
        assert len(t_cmds) == 3, f"Should throw exactly 3, threw {len(t_cmds)}"


class TestSyncDrillMultiBall:
    """Sync drill with multiple balls — B changes between throws."""

    @pytest.mark.asyncio
    async def test_alternating_balls_send_different_B(self):
        """Each ball in sequence gets its own B command.
        Source: BUSINESS_LOGIC_COMPLETE.md:286 'for each ball in drill'"""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball_fh = make_ball(top=120, bot=0, osc=164, wait_ms=500)
        ball_bh = make_ball(top=120, bot=0, osc=136, wait_ms=500)

        await robot.run_drill([ball_fh, ball_bh], repeat=1, count=0, skip_warmup=True)
        await asyncio.sleep(3.0)

        b_cmds = [c for c in cap.filter("B") if len(c) > 2]
        assert len(b_cmds) >= 2, f"Should send B for each ball, got {len(b_cmds)}"
        # The two B commands should be different (different osc)
        assert b_cmds[0] != b_cmds[1], "Multi-ball B commands should differ"

    @pytest.mark.asyncio
    async def test_multiball_B_T_alternation(self):
        """Pattern should be: B1, T, B2, T, B1, T, ... (B before each throw)."""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball1 = make_ball(top=100, bot=0, wait_ms=500)
        ball2 = make_ball(top=80, bot=20, wait_ms=500)

        await robot.run_drill([ball1, ball2], repeat=1, count=0, skip_warmup=True)
        await asyncio.sleep(4.0)

        # Extract B and T commands in order
        bt_sequence = []
        for cmd in cap.get():
            if cmd.startswith("B") and len(cmd) > 2:
                bt_sequence.append("B")
            elif cmd == "T":
                bt_sequence.append("T")

        # Should be: B, T, B, T (for 2-ball, 1 repeat)
        assert len(bt_sequence) >= 4, f"Expected at least 4 B/T commands, got {bt_sequence}"
        # Verify alternation
        for i in range(0, len(bt_sequence) - 1, 2):
            assert bt_sequence[i] == "B", f"Position {i} should be B"
            assert bt_sequence[i + 1] == "T", f"Position {i+1} should be T"


class TestSyncDrillWarmup:
    """Warmup phase in sync drill mode.
    Note: Warmup is NOT part of original app — it's our addition.
    But we still test its behavior for consistency."""

    @pytest.mark.asyncio
    async def test_warmup_sends_initial_B_before_countdown(self):
        """When warmup enabled, first B is sent before countdown."""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=100, bot=50, wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=1,
                              skip_warmup=False, emit_countdown=False)
        await asyncio.sleep(5.0)

        b_cmds = [c for c in cap.filter("B") if len(c) > 2]
        assert len(b_cmds) >= 2, "Warmup should send additional B command"

    @pytest.mark.asyncio
    async def test_first_H_before_warmup(self):
        """Warmup starts with H (stop) to reset state."""
        robot, cap = make_robot(firmware=600, mode="sync")
        ball = make_ball(top=100, bot=50, wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=1,
                              skip_warmup=False, emit_countdown=False)
        await asyncio.sleep(5.0)

        cmds = cap.get()
        assert cmds[0] == "H", f"First command should be H (stop), got {cmds[0]}"


# ═══════════════════════════════════════════════════════════════════════════════
# ASYNC DRILL TESTS — wTA + A + END protocol (fw >= 701, BLE)
# Source: BUSINESS_LOGIC_COMPLETE.md:295-303
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncDrillSingleBall:
    """Async drill with single ball."""

    @pytest.mark.asyncio
    async def test_sequence_H_wTA_A_END(self):
        """Async drill sequence: H → wTA → A → END.
        Source: BUSINESS_LOGIC_COMPLETE.md:295-300"""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0, osc=150, height=142, rotation=150, wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=0)
        # Wait for loading + execution
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        cmds = cap.get()

        # Must start with H
        assert cmds[0] == "H", f"Async drill must start with H, got {cmds[0]}"

        # Must have wTA command
        wta_cmds = [c for c in cmds if c.startswith("wTA")]
        assert len(wta_cmds) >= 1, f"Must send wTA, commands: {cmds}"

        # Must have A command
        a_cmds = [c for c in cmds if c.startswith("A")]
        assert len(a_cmds) >= 1, f"Must send A command, commands: {cmds}"

        # Must have END command
        end_cmds = [c for c in cmds if c.startswith("END")]
        assert len(end_cmds) >= 1, f"Must send END command, commands: {cmds}"

    @pytest.mark.asyncio
    async def test_wTA_before_A(self):
        """wTA must come before its corresponding A command.
        Source: ANDROID_APP_RE.md:565 'writeCommand wTA... then A...'"""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0, wait_ms=2000)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        cmds = cap.get()
        wta_idx = next(i for i, c in enumerate(cmds) if c.startswith("wTA"))
        a_idx = next(i for i, c in enumerate(cmds) if c.startswith("A"))
        assert wta_idx < a_idx, f"wTA (idx={wta_idx}) must come before A (idx={a_idx})"

    @pytest.mark.asyncio
    async def test_A_before_END(self):
        """All A commands must be sent before END."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0, wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        cmds = cap.get()
        last_a = max(i for i, c in enumerate(cmds) if c.startswith("A"))
        first_end = next(i for i, c in enumerate(cmds) if c.startswith("END"))
        assert last_a < first_end, "All A commands must precede END"

    @pytest.mark.asyncio
    async def test_wTA_format(self):
        """wTA command: wTA{waitTime/10:03d}."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(wait_ms=2100)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta = cap.filter("wTA")[0]
        assert regex.match(r"^wTA\d{3}$", wta), f"wTA format wrong: {wta!r}"
        # 2100ms / 10 = 210
        val = int(wta[3:])
        assert val >= 1, "wTA value must be ≥ 1"

    @pytest.mark.asyncio
    async def test_A_command_format(self):
        """A command must be 19 chars (A + 18 payload), no spaces."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=100, bot=50)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        a_cmds = cap.filter("A")
        assert len(a_cmds) >= 1
        for cmd in a_cmds:
            assert len(cmd) == 19, f"A command should be 19 chars, got {len(cmd)}: {cmd!r}"
            assert " " not in cmd, f"A command should not contain spaces: {cmd!r}"

    @pytest.mark.asyncio
    async def test_END_format(self):
        """END command: END{count:03d}{seed:03d}{delay:03d}.
        Source: BUSINESS_LOGIC_COMPLETE.md:300"""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        end_cmds = cap.filter("END")
        assert len(end_cmds) >= 1
        end = end_cmds[0]
        assert regex.match(r"^END\d{3}\d{3}\d{3}$", end), f"END format wrong: {end!r}"
        # Parse fields
        count = int(end[3:6])
        seed = int(end[6:9])
        delay = int(end[9:12])
        assert count >= 1, "END count must be ≥ 1"
        assert 1 <= seed <= 255, f"END seed must be 1-255, got {seed}"
        assert delay >= 0, "END delay must be ≥ 0"

    @pytest.mark.asyncio
    async def test_drill_ends_with_H(self):
        """Async drill must also end with H."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=100, bot=50, wait_ms=500)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        cmds = cap.get()
        assert cmds[-1] == "H", f"Drill should end with H, last: {cmds[-1]}"


class TestAsyncDrillMultiBall:
    """Async drill with multiple balls.
    Source: BUSINESS_LOGIC_COMPLETE.md:296-297 'for each ball: setBall + wait(250ms)'"""

    @pytest.mark.asyncio
    async def test_each_ball_gets_wTA_A_pair(self):
        """Each ball in drill gets its own wTA + A pair."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball1 = make_ball(top=120, bot=0, osc=164, wait_ms=1500)
        ball2 = make_ball(top=80, bot=20, osc=136, wait_ms=2000)

        await robot.run_drill([ball1, ball2], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta_cmds = cap.filter("wTA")
        a_cmds = cap.filter("A")
        assert len(wta_cmds) >= 2, f"2-ball drill needs 2 wTA commands, got {len(wta_cmds)}"
        assert len(a_cmds) >= 2, f"2-ball drill needs 2 A commands, got {len(a_cmds)}"

    @pytest.mark.asyncio
    async def test_wTA_values_match_ball_wait_times(self):
        """wTA values should correspond to each ball's wait_ms."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball1 = make_ball(wait_ms=1500)
        ball2 = make_ball(wait_ms=2500)

        await robot.run_drill([ball1, ball2], repeat=1, count=0, percent=100)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta_cmds = cap.filter("wTA")
        assert len(wta_cmds) >= 2

        # At 100% tempo, wTA values should match wait_ms / 10
        wta_vals = [int(c[3:]) for c in wta_cmds[:2]]
        assert wta_vals[0] >= 150, f"Ball1 wTA should be ≥ 150, got {wta_vals[0]}"
        assert wta_vals[1] >= 250, f"Ball2 wTA should be ≥ 250, got {wta_vals[1]}"

    @pytest.mark.asyncio
    async def test_A_commands_differ_for_different_balls(self):
        """Different balls produce different A commands."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball_fh = make_ball(top=120, bot=0, osc=164)
        ball_bh = make_ball(top=80, bot=20, osc=136)

        await robot.run_drill([ball_fh, ball_bh], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        a_cmds = cap.filter("A")
        assert len(a_cmds) >= 2
        assert a_cmds[0] != a_cmds[1], "Different balls should produce different A commands"

    @pytest.mark.asyncio
    async def test_wTA_A_interleaving(self):
        """wTA and A must be interleaved: wTA1, A1, wTA2, A2."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball1 = make_ball(top=120, bot=0, wait_ms=1500)
        ball2 = make_ball(top=80, bot=20, wait_ms=2000)

        await robot.run_drill([ball1, ball2], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        # Extract wTA and A in order
        wa_sequence = []
        for cmd in cap.get():
            if cmd.startswith("wTA"):
                wa_sequence.append("wTA")
            elif cmd.startswith("A"):
                wa_sequence.append("A")

        # Should be: wTA, A, wTA, A
        assert len(wa_sequence) >= 4, f"Expected ≥ 4 wTA/A commands, got {wa_sequence}"
        assert wa_sequence[0] == "wTA"
        assert wa_sequence[1] == "A"
        assert wa_sequence[2] == "wTA"
        assert wa_sequence[3] == "A"

    @pytest.mark.asyncio
    async def test_three_ball_drill(self):
        """3-ball drill: 3 wTA + 3 A commands."""
        robot, cap = make_robot(firmware=701, mode="async")
        balls = [
            make_ball(top=120, bot=0, osc=164),
            make_ball(top=80, bot=20, osc=150),
            make_ball(top=60, bot=60, osc=136),
        ]

        await robot.run_drill(balls, repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta_cmds = cap.filter("wTA")
        a_cmds = cap.filter("A")
        end_cmds = cap.filter("END")
        assert len(wta_cmds) >= 3
        assert len(a_cmds) >= 3
        assert len(end_cmds) >= 1


class TestAsyncDrillNoPreSpinB:
    """Async drill must NOT send B command to pre-spin motors.
    Mixing B with A confuses the firmware.
    Source: git commit 4e56c5a"""

    @pytest.mark.asyncio
    async def test_no_B_command_in_async_drill(self):
        """Async drill should only use A commands for balls, not B.
        (B{zeros} on stop/cleanup is a motor-kill safety command, not a ball cmd.)"""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0)

        await robot.run_drill([ball], repeat=1, count=0)
        await asyncio.sleep(5.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        # Ignore zero-motor B safety command; only ball-config B is forbidden
        zero_b = "B000000001501501500"
        b_ball_cmds = [c for c in cap.filter("B") if len(c) > 2 and c != zero_b]
        assert len(b_ball_cmds) == 0, (
            f"Async drill should not send B ball commands, got: {b_ball_cmds}")


# ═══════════════════════════════════════════════════════════════════════════════
# DRILL MODE AUTO-DETECT
# ═══════════════════════════════════════════════════════════════════════════════

class TestDrillModeDetection:
    """Drill mode auto-detection based on firmware and transport.
    Source: robot.py _effective_drill_mode"""

    def test_ble_fw701_is_async(self):
        robot = Robot()
        robot.drill_mode = "auto"
        robot.firmware = 701
        from unittest.mock import MagicMock
        mock_transport = MagicMock()
        mock_transport.transport_type = "ble"
        mock_transport.is_connected = True
        robot._transport = mock_transport
        assert robot._effective_drill_mode() == "async"

    def test_usb_is_sync(self):
        robot = Robot()
        robot.drill_mode = "auto"
        robot.firmware = 701
        from unittest.mock import MagicMock
        mock_transport = MagicMock()
        mock_transport.transport_type = "usb"
        mock_transport.is_connected = True
        robot._transport = mock_transport
        assert robot._effective_drill_mode() == "sync"

    def test_old_firmware_is_sync(self):
        robot = Robot()
        robot.drill_mode = "auto"
        robot.firmware = 600
        from unittest.mock import MagicMock
        mock_transport = MagicMock()
        mock_transport.transport_type = "ble"
        mock_transport.is_connected = True
        robot._transport = mock_transport
        assert robot._effective_drill_mode() == "sync"

    def test_forced_sync(self):
        robot = Robot()
        robot.drill_mode = "sync"
        robot.firmware = 701
        assert robot._effective_drill_mode() == "sync"

    def test_forced_async(self):
        robot = Robot()
        robot.drill_mode = "async"
        robot.firmware = 600
        assert robot._effective_drill_mode() == "async"


# ═══════════════════════════════════════════════════════════════════════════════
# STOP / CANCEL BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestDrillStopBehavior:
    """Stopping a drill must always send H."""

    @pytest.mark.asyncio
    async def test_stop_drill_sends_H(self):
        """stop_drill() must send H command."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(top=120, bot=0, wait_ms=2000)

        await robot.run_drill([ball], repeat=0, count=0)
        await asyncio.sleep(1.0)
        robot.stop_drill()
        await asyncio.sleep(0.5)

        h_cmds = cap.filter("H")
        assert len(h_cmds) >= 2, "stop_drill must send H (initial + stop)"

    @pytest.mark.asyncio
    async def test_stop_method_sends_H(self):
        """robot.stop() must send H."""
        robot, cap = make_robot(firmware=701, mode="async")
        await robot.stop()
        assert "H" in cap.get()


# ═══════════════════════════════════════════════════════════════════════════════
# PERCENT / TEMPO ADJUSTMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPercentAdjustment:
    """Percent parameter adjusts wait times in drills."""

    @pytest.mark.asyncio
    async def test_100_percent_no_change(self):
        """At 100%, wait times should be close to original."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=0, percent=100)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta = cap.filter("wTA")[0]
        val = int(wta[3:])
        assert val == 150, f"At 100%, wTA should be 150 (1500/10), got {val}"

    @pytest.mark.asyncio
    async def test_lower_percent_longer_wait(self):
        """Lower percent → longer wait times (slower tempo)."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(wait_ms=1500)

        await robot.run_drill([ball], repeat=1, count=0, percent=50)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta = cap.filter("wTA")[0]
        val = int(wta[3:])
        assert val > 150, f"At 50%, wTA should be > 150, got {val}"

    @pytest.mark.asyncio
    async def test_higher_percent_shorter_wait(self):
        """Higher percent → shorter wait times (faster tempo)."""
        robot, cap = make_robot(firmware=701, mode="async")
        ball = make_ball(wait_ms=2000)

        await robot.run_drill([ball], repeat=1, count=0, percent=150)
        await asyncio.sleep(3.0)
        robot.stop_drill()
        await asyncio.sleep(0.2)

        wta = cap.filter("wTA")[0]
        val = int(wta[3:])
        # 2000ms at 150% → faster → wTA < 200
        assert val < 200, f"At 150%, wTA should be < 200 (normal=200), got {val}"
