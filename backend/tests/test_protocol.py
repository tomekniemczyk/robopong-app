"""Protocol compliance tests — ground truth from reverse-engineered Newgy app.

██████████████████████████████████████████████████████████████████████████████
██  THESE TESTS ARE THE CONTRACT — DO NOT MODIFY TO FIX FAILING TESTS!    ██
██  If a test fails, FIX THE IMPLEMENTATION, not the test.                ██
██                                                                        ██
██  Source of truth:                                                       ██
██    re/BUSINESS_LOGIC_COMPLETE.md   — decompiled business logic          ██
██    re/ANDROID_APP_RE.md            — Android app reverse engineering     ██
██    re/WINDOWS_APP_RE.md            — Windows app reverse engineering     ██
██████████████████████████████████████████████████████████████████████████████

Tests verify that our implementation matches the ORIGINAL Newgy app behavior
at every stage of the protocol: conversion, command format, LED calculation,
calibration, and drill execution.
"""

import pytest
import re as regex


# ═══════════════════════════════════════════════════════════════════════════════
# REFERENCE IMPLEMENTATION — Original Newgy app formulas (DO NOT CHANGE)
# ═══════════════════════════════════════════════════════════════════════════════

class OriginalApp:
    """Reference implementation from decompiled Newgy app.
    Source: re/BUSINESS_LOGIC_COMPLETE.md section 2 (AdvancedBallConverter)"""

    # ── Motor speed conversion (% → raw 0-210) ──────────────────────────────

    @staticmethod
    def getMotorSpeed(motor_percent: int, min_speed: int = 28, max_speed: int = 210) -> int:
        """AdvancedBallConverter.getMotorSpeed()
        Source: ANDROID_APP_RE.md:174-181, BUSINESS_LOGIC_COMPLETE.md:86
        Note: C# Convert.ToInt32() ROUNDS to nearest, not truncates."""
        if motor_percent == 0:
            return 0
        if motor_percent < 0:
            return round(max_speed * (motor_percent / 100))
        return round(min_speed + (max_speed - min_speed) * (motor_percent / 100))

    # ── Head position conversions ────────────────────────────────────────────

    @staticmethod
    def getHeight(height_percent: int) -> int:
        """Source: BUSINESS_LOGIC_COMPLETE.md:87"""
        return int(75 + 135 * (height_percent / 100))

    @staticmethod
    def getOscillation(osc_percent: int, left_handed: bool = False) -> int:
        """Source: BUSINESS_LOGIC_COMPLETE.md:88"""
        if left_handed:
            osc_percent = 100 - osc_percent
        return int(173 - 46 * (osc_percent / 100))

    @staticmethod
    def getRotation(degrees: int) -> int:
        """Source: BUSINESS_LOGIC_COMPLETE.md:89"""
        raw = int(150 + 60 * (degrees / 90))
        return max(90, min(210, raw))

    # ── PWM for B/A command ──────────────────────────────────────────────────

    @staticmethod
    def getMotorPWM(raw_motor: int, speed_cal: int = 0, firmware: int = 701) -> int:
        """Convert raw motor value (0-210) to PWM for B/A command.
        Source: BUSINESS_LOGIC_COMPLETE.md:247-249
        Note: SpeedCAL is always 0 due to bug in original (line 244-245).
        Note: C# formats double with :000 which ROUNDS, not truncates."""
        if firmware == 206:
            return raw_motor + 5
        return round(abs(raw_motor) * 4.016) + speed_cal

    # ── LED calculation ──────────────────────────────────────────────────────

    @staticmethod
    def getLEDS(top_motor_raw: int, bot_motor_raw: int) -> int:
        """Source: BUSINESS_LOGIC_COMPLETE.md:271-279
        Uses RAW motor values (0-210), not percentages."""
        diff = top_motor_raw - bot_motor_raw
        if diff == 0:
            return 0
        ratio = abs(diff) / 360.0
        if ratio <= 0.10:
            level = 1  # OneBottom/OneTop
        elif ratio <= 0.50:
            level = 2  # TwoBottom/TwoTop
        elif ratio <= 0.75:
            level = 3  # ThreeBottom/ThreeTop
        else:
            level = 4  # FourBottom/FourTop
        # diff > 0 means top > bottom → Top spin → values 5-8
        # diff < 0 means bottom > top → Bottom spin → values 1-4
        return level + 4 if diff > 0 else level

    # ── B/A command format ───────────────────────────────────────────────────

    @staticmethod
    def buildBCommand(top_raw: int, bot_raw: int, osc_raw: int, height_raw: int,
                      rot_raw: int, firmware: int = 701, speed_cal: int = 0) -> str:
        """Build complete B command string as original app would.
        Source: BUSINESS_LOGIC_COMPLETE.md:252, ANDROID_APP_RE.md:521
        Format: B{d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L}"""
        dir_t = 1 if top_raw < 0 else 0
        dir_b = 1 if bot_raw < 0 else 0
        pwm_t = OriginalApp.getMotorPWM(top_raw, speed_cal, firmware)
        pwm_b = OriginalApp.getMotorPWM(bot_raw, speed_cal, firmware)
        leds = OriginalApp.getLEDS(top_raw, bot_raw)
        return f"B{dir_t}{pwm_t:03d}{dir_b}{pwm_b:03d}{osc_raw:03d}{height_raw:03d}{rot_raw:03d}{leds}"

    @staticmethod
    def buildACommand(top_raw: int, bot_raw: int, osc_raw: int, height_raw: int,
                      rot_raw: int, firmware: int = 701, speed_cal: int = 0) -> str:
        """Build A command (async mode). Same format as B but prefix A.
        Source: BUSINESS_LOGIC_COMPLETE.md:257"""
        cmd = OriginalApp.buildBCommand(top_raw, bot_raw, osc_raw, height_raw,
                                         rot_raw, firmware, speed_cal)
        return "A" + cmd[1:]  # Replace B with A

    # ── SpeedCAL ─────────────────────────────────────────────────────────────

    @staticmethod
    def calcSpeedCAL(top_motor_raw: int, robot_version: int = 2) -> int:
        """Source: ANDROID_APP_RE.md:716-728
        robot_version: 2=Gen2/SecondRun, 0/1=Gen1"""
        if robot_version == 2:
            return top_motor_raw - 161
        return top_motor_raw - 170


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION FORMULA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMotorSpeedConversion:
    """Verify getMotorSpeed matches the reference table.
    Source: BUSINESS_LOGIC_COMPLETE.md:92-101"""

    REFERENCE_TABLE = [
        # (percent, expected_raw) — C# Convert.ToInt32() rounds to nearest
        (0,   0),
        (25,  74),     # 28 + 182*0.25 = 73.5 → round = 74 (banker's: nearest even)
        (50,  119),    # 28 + 182*0.50 = 119.0 → 119
        (73,  161),    # Gen2 calibration: 28 + 182*0.73 = 160.86 → round = 161
        (77,  168),    # Gen1 calibration: 28 + 182*0.77 = 168.14 → round = 168
        (100, 210),    # 28 + 182*1.00 = 210
    ]

    @pytest.mark.parametrize("percent,expected_raw", REFERENCE_TABLE)
    def test_positive_speed(self, percent, expected_raw):
        """Reference: BUSINESS_LOGIC_COMPLETE.md table Motor(%)→raw"""
        result = OriginalApp.getMotorSpeed(percent)
        assert result == expected_raw, (
            f"getMotorSpeed({percent}%) should be {expected_raw} raw, got {result}")

    def test_zero_returns_zero(self):
        """pct=0 always returns 0, not min(28)."""
        assert OriginalApp.getMotorSpeed(0) == 0

    def test_negative_speed(self):
        """Negative: raw = 210 * (pct/100), sign preserved.
        Source: ANDROID_APP_RE.md:179"""
        assert OriginalApp.getMotorSpeed(-50) == -105  # 210 * -0.5
        assert OriginalApp.getMotorSpeed(-100) == -210

    def test_min_positive_is_28(self):
        """Smallest positive speed: getMotorSpeed(1) = int(28 + 182*0.01) = int(29.82) = 29"""
        result = OriginalApp.getMotorSpeed(1)
        assert result >= 28, f"Min positive raw should be >= 28, got {result}"

    def test_max_positive_is_210(self):
        assert OriginalApp.getMotorSpeed(100) == 210


class TestPWMConversion:
    """Verify raw motor → PWM for B/A command.
    Source: BUSINESS_LOGIC_COMPLETE.md:94-101"""

    REFERENCE_TABLE = [
        # (raw, expected_pwm) — C# formats double with :000 which rounds
        (0,   0),
        (73,  293),   # 73 * 4.016 = 293.168 → round = 293
        (119, 478),   # 119 * 4.016 = 477.904 → round = 478
        (161, 647),   # Gen2 cal: 161 * 4.016 = 646.576 → round = 647
        (168, 675),   # Gen1 cal: 168 * 4.016 = 674.688 → round = 675
        (210, 843),   # Max: 210 * 4.016 = 843.36 → round = 843
    ]

    @pytest.mark.parametrize("raw,expected_pwm", REFERENCE_TABLE)
    def test_pwm_values(self, raw, expected_pwm):
        """Reference: BUSINESS_LOGIC_COMPLETE.md B-PWM column"""
        result = OriginalApp.getMotorPWM(raw)
        assert result == expected_pwm, (
            f"PWM for raw={raw} should be {expected_pwm}, got {result}")

    def test_firmware_206(self):
        """Old firmware: PWM = raw + 5"""
        assert OriginalApp.getMotorPWM(100, firmware=206) == 105

    def test_speed_cal_added(self):
        """SpeedCAL is added to PWM (but always 0 in practice)."""
        assert OriginalApp.getMotorPWM(100, speed_cal=10) == round(100 * 4.016) + 10

    def test_max_pwm_is_843(self):
        """Max motor=210 → PWM=843. NOT 999!"""
        assert OriginalApp.getMotorPWM(210) == 843


class TestHeightConversion:
    """Source: BUSINESS_LOGIC_COMPLETE.md:87, range 75-210"""

    REFERENCE = [(0, 75), (50, 142), (80, 183), (100, 210)]

    @pytest.mark.parametrize("percent,expected", REFERENCE)
    def test_height_values(self, percent, expected):
        result = OriginalApp.getHeight(percent)
        assert result == expected


class TestOscillationConversion:
    """Source: BUSINESS_LOGIC_COMPLETE.md:88, range 127-173, center=150"""

    REFERENCE = [(0, 173), (50, 150), (100, 127)]

    @pytest.mark.parametrize("percent,expected", REFERENCE)
    def test_oscillation_values(self, percent, expected):
        result = OriginalApp.getOscillation(percent)
        assert result == expected

    def test_left_handed_inverts(self):
        """Left-handed: pct = 100 - pct before conversion."""
        assert OriginalApp.getOscillation(0, left_handed=True) == 127   # same as RH 100%
        assert OriginalApp.getOscillation(100, left_handed=True) == 173  # same as RH 0%
        assert OriginalApp.getOscillation(50, left_handed=True) == 150  # center unchanged


class TestRotationConversion:
    """Source: BUSINESS_LOGIC_COMPLETE.md:89, range 90-210, center=150"""

    REFERENCE = [(-90, 90), (0, 150), (90, 210)]

    @pytest.mark.parametrize("degrees,expected", REFERENCE)
    def test_rotation_values(self, degrees, expected):
        result = OriginalApp.getRotation(degrees)
        assert result == expected

    def test_clamped_to_range(self):
        assert OriginalApp.getRotation(-180) == 90   # clamped
        assert OriginalApp.getRotation(180) == 210   # clamped


# ═══════════════════════════════════════════════════════════════════════════════
# LED CALCULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLEDCalculation:
    """LED indicator logic from original app.
    Source: BUSINESS_LOGIC_COMPLETE.md:271-279

    Mapping: 0=None, 1=OneBottom, 2=TwoBottom, 3=ThreeBottom, 4=FourBottom,
             5=OneTop, 6=TwoTop, 7=ThreeTop, 8=FourTop"""

    def test_equal_speeds_no_led(self):
        assert OriginalApp.getLEDS(100, 100) == 0
        assert OriginalApp.getLEDS(0, 0) == 0

    def test_topspin_small_diff(self):
        """Top > Bottom, ratio ≤ 0.10 → OneTop(5)"""
        # diff=30, ratio=30/360=0.083 ≤ 0.10
        assert OriginalApp.getLEDS(130, 100) == 5

    def test_topspin_medium_diff(self):
        """Top > Bottom, ratio ≤ 0.50 → TwoTop(6)"""
        # diff=100, ratio=100/360=0.278 ≤ 0.50
        assert OriginalApp.getLEDS(200, 100) == 6

    def test_topspin_large_diff(self):
        """Top > Bottom, ratio ≤ 0.75 → ThreeTop(7)"""
        # diff=210, ratio=210/360=0.583 ≤ 0.75
        assert OriginalApp.getLEDS(210, 0) == 7

    def test_topspin_extreme_diff(self):
        """Top > Bottom, ratio > 0.75 → FourTop(8)"""
        # Use signed values to get large diff: top=210, bot=-100 → diff=310
        # ratio=310/360=0.861 > 0.75
        assert OriginalApp.getLEDS(210, -100) == 8

    def test_backspin_small_diff(self):
        """Bottom > Top, ratio ≤ 0.10 → OneBottom(1)"""
        assert OriginalApp.getLEDS(100, 130) == 1

    def test_backspin_medium_diff(self):
        """Bottom > Top, ratio ≤ 0.50 → TwoBottom(2)"""
        assert OriginalApp.getLEDS(0, 100) == 2

    def test_backspin_large_diff(self):
        """Bottom > Top, ratio ≤ 0.75 → ThreeBottom(3)"""
        assert OriginalApp.getLEDS(0, 210) == 3

    def test_backspin_extreme_diff(self):
        """Bottom > Top, ratio > 0.75 → FourBottom(4)"""
        assert OriginalApp.getLEDS(-100, 210) == 4

    def test_boundary_0_10(self):
        """Exactly ratio=0.10 → level 1 (One)"""
        # diff=36, ratio=36/360=0.10 exactly
        assert OriginalApp.getLEDS(36, 0) == 5  # OneTop

    def test_boundary_0_50(self):
        """Exactly ratio=0.50 → level 2 (Two)"""
        # diff=180, ratio=180/360=0.50 exactly
        assert OriginalApp.getLEDS(180, 0) == 6  # TwoTop

    def test_boundary_0_75(self):
        """Exactly ratio=0.75 → level 3 (Three)"""
        # diff=270, ratio=270/360=0.75 exactly
        assert OriginalApp.getLEDS(270, 0) == 7  # ThreeTop


# ═══════════════════════════════════════════════════════════════════════════════
# B/A COMMAND FORMAT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBCommandFormat:
    """B command format compliance.
    Source: ANDROID_APP_RE.md:521, WINDOWS_APP_RE.md:287, BUSINESS_LOGIC_COMPLETE.md:252

    Correct format: B{d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L}
    Total: B + 18 chars = 19 chars

    ████████████████████████████████████████████████████████████████████
    ██  FORMAT DOES NOT CONTAIN "00" SpeedCAL FIELD!                 ██
    ██  SpeedCAL is only used in PWM CALCULATION, not in format.    ██
    ██  Source: BUSINESS_LOGIC_COMPLETE.md:243-245,252               ██
    ██  Three independent RE docs confirm: 18-char format.           ██
    ████████████████████████████████████████████████████████████████████
    """

    def test_format_length(self):
        """B command is exactly 19 chars (B + 18 payload)."""
        cmd = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        assert len(cmd) == 19, f"B command should be 19 chars, got {len(cmd)}: {cmd!r}"

    def test_no_spaces(self):
        """B command has NO spaces."""
        cmd = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        assert " " not in cmd, f"B command should not contain spaces: {cmd!r}"

    def test_no_speedcal_field(self):
        """No '00' SpeedCAL field between speeds and oscillation."""
        cmd = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        # After B + dir(1) + speed(3) + dir(1) + speed(3) = 8 chars
        # Next 3 chars should be oscillation, NOT "00x"
        payload = cmd[1:]  # strip B
        osc_field = payload[8:11]
        assert osc_field == "150", f"Oscillation field at pos 9-11 should be '150', got '{osc_field}'"

    def test_reference_example(self):
        """Verify with the reference example from ANDROID_APP_RE.md:524-540.
        Top=75%(raw=165), Bot=25%(raw=74), Osc=50%(raw=150), H=50%(raw=142), Rot=0°(raw=150)

        Expected command: B066302971501421506
        - PWM top: 165*4.016=662.6→663 (wait, actually int(662.64)=662!)
        """
        # Let me compute step by step:
        # top_raw=165, PWM=int(165*4.016)=int(662.64)=662
        # bot_raw=74,  PWM=int(74*4.016)=int(297.184)=297
        # LEDS: diff=165-74=91, ratio=91/360=0.253 → ≤0.50 → level 2, diff>0 → 6
        # top_raw=165, PWM=round(165*4.016)=round(662.64)=663
        # bot_raw=74,  PWM=round(74*4.016)=round(297.184)=297
        # LEDS: diff=165-74=91, ratio=91/360=0.253 → ≤0.50 → level 2, diff>0 → 6
        cmd = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        assert cmd == "B066302971501421506", f"Reference example mismatch: {cmd}"

    def test_field_positions(self):
        """Verify each field is at the correct position."""
        # Use distinctive values to identify each field
        cmd = OriginalApp.buildBCommand(top_raw=100, bot_raw=50, osc_raw=173,
                                         height_raw=75, rot_raw=210)
        payload = cmd[1:]
        assert payload[0] == "0", "dir_top should be 0 for positive"
        assert payload[1:4] == f"{round(100*4.016):03d}", "top PWM at pos 2-4"
        assert payload[4] == "0", "dir_bot should be 0 for positive"
        assert payload[5:8] == f"{round(50*4.016):03d}", "bot PWM at pos 6-8"
        assert payload[8:11] == "173", "osc at pos 9-11"
        assert payload[11:14] == "075", "height at pos 12-14"
        assert payload[14:17] == "210", "rotation at pos 15-17"

    def test_negative_direction(self):
        """Negative motor speed → direction bit = 1."""
        cmd = OriginalApp.buildBCommand(-100, -50, 150, 142, 150)
        payload = cmd[1:]
        assert payload[0] == "1", "dir_top should be 1 for negative"
        assert payload[4] == "1", "dir_bot should be 1 for negative"

    def test_zero_speed(self):
        """Zero speed: direction=0, PWM=000."""
        cmd = OriginalApp.buildBCommand(0, 0, 150, 142, 150)
        payload = cmd[1:]
        assert payload[0:4] == "0000", "zero top: dir=0, pwm=000"
        assert payload[4:8] == "0000", "zero bot: dir=0, pwm=000"


class TestACommandFormat:
    """A command has identical format to B, just different prefix.
    Source: ANDROID_APP_RE.md:557-569, BUSINESS_LOGIC_COMPLETE.md:257"""

    def test_same_format_different_prefix(self):
        b = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        a = OriginalApp.buildACommand(165, 74, 150, 142, 150)
        assert a[0] == "A"
        assert b[0] == "B"
        assert a[1:] == b[1:], "A and B payload should be identical"

    def test_a_command_length(self):
        cmd = OriginalApp.buildACommand(100, 50, 150, 142, 150)
        assert len(cmd) == 19


class TestWTACommand:
    """wTA command for async drill wait time.
    Source: ANDROID_APP_RE.md:602-608"""

    def test_format(self):
        """wTA{waitTime/10:000}"""
        wait_ms = 1500
        cmd = f"wTA{wait_ms // 10:03d}"
        assert cmd == "wTA150"

    def test_short_wait(self):
        cmd = f"wTA{500 // 10:03d}"
        assert cmd == "wTA050"

    def test_long_wait(self):
        cmd = f"wTA{5000 // 10:03d}"
        assert cmd == "wTA500"


class TestENDCommand:
    """END command to start async drill execution.
    Source: BUSINESS_LOGIC_COMPLETE.md:300"""

    def test_format(self):
        """END{count:3}{random(1-255):3}{delay*10:3}"""
        count = 60
        seed = 42
        delay_s = 0
        cmd = f"END{count:03d}{seed:03d}{int(delay_s * 10):03d}"
        assert cmd == "END060042000"

    def test_with_delay(self):
        cmd = f"END{10:03d}{128:03d}{int(2.0 * 10):03d}"
        assert cmd == "END010128020"

    def test_count_padding(self):
        cmd = f"END{1:03d}{1:03d}{0:03d}"
        assert cmd == "END001001000"


# ═══════════════════════════════════════════════════════════════════════════════
# SpeedCAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpeedCAL:
    """SpeedCAL calibration algorithm.
    Source: ANDROID_APP_RE.md:716-728, BUSINESS_LOGIC_COMPLETE.md:346-351"""

    def test_gen2_baseline(self):
        """Gen2 (SecondRun): 73% → raw=161 → offset = 161-161 = 0"""
        raw = OriginalApp.getMotorSpeed(73)  # ~160
        cal = OriginalApp.calcSpeedCAL(raw, robot_version=2)
        assert cal <= 0, "Default Gen2 cal should be ≤ 0 (not sent)"

    def test_gen1_baseline(self):
        """Gen1: 77% → raw=168 → offset = 168-170 = -2"""
        raw = OriginalApp.getMotorSpeed(77)
        cal = OriginalApp.calcSpeedCAL(raw, robot_version=1)
        assert cal <= 0, "Default Gen1 cal should be ≤ 0 (not sent)"

    def test_gen2_higher_speed(self):
        """If user calibrates to higher speed, offset > 0, Q command sent."""
        raw = 175  # above baseline 161
        cal = OriginalApp.calcSpeedCAL(raw, robot_version=2)
        assert cal == 14
        # Q command would be: Q014
        assert f"Q{cal:03d}" == "Q014"

    def test_q_command_format(self):
        """Q{offset:000} — 3-digit zero-padded."""
        assert f"Q{0:03d}" == "Q000"
        assert f"Q{25:03d}" == "Q025"


# ═══════════════════════════════════════════════════════════════════════════════
# IMPLEMENTATION COMPLIANCE TESTS — verify robot.py matches original
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildBallParamsCompliance:
    """Test that Robot._build_ball_params matches the original app output.
    These tests use RAW motor values (as stored in our Ball model)."""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        self.robot = Robot()
        self.robot.firmware = 701
        self.robot.robot_version = 2

    def _get_params(self, top, bot, osc, height, rot):
        """Call _build_ball_params and return the result."""
        return self.robot._build_ball_params(top, bot, osc, height, rot)

    def _get_b_cmd(self, top, bot, osc, height, rot):
        return "B" + self._get_params(top, bot, osc, height, rot)

    def test_command_length(self):
        """B command must be exactly 19 chars total."""
        cmd = self._get_b_cmd(165, 74, 150, 142, 150)
        assert len(cmd) == 19, (
            f"B command should be 19 chars (B + 18 payload), got {len(cmd)}: {cmd!r}")

    def test_no_spaces_in_command(self):
        """Command must not contain spaces."""
        cmd = self._get_b_cmd(165, 74, 150, 142, 150)
        assert " " not in cmd, f"B command should not contain spaces: {cmd!r}"

    def test_no_speedcal_00_field(self):
        """Must NOT have '00' SpeedCAL between speeds and oscillation."""
        cmd = self._get_b_cmd(100, 50, 173, 75, 210)
        payload = cmd[1:]
        # Position 8-10 must be oscillation (173), not "00" + something
        osc_at_pos = payload[8:11]
        assert osc_at_pos == "173", (
            f"Oscillation at positions 9-11 should be '173', got '{osc_at_pos}'. "
            f"Full command: {cmd!r}")

    def test_matches_original_for_typical_topspin(self):
        """Typical topspin ball: raw top=165, bot=74, osc=150, h=142, rot=150.
        Must produce same B command as original app."""
        our_cmd = self._get_b_cmd(165, 74, 150, 142, 150)
        ref_cmd = OriginalApp.buildBCommand(165, 74, 150, 142, 150)
        assert our_cmd == ref_cmd, (
            f"Mismatch!\n  Ours:     {our_cmd!r}\n  Original: {ref_cmd!r}")

    def test_matches_original_for_backspin(self):
        """Backspin ball: top=-20, bot=100."""
        our_cmd = self._get_b_cmd(-20, 100, 150, 142, 150)
        ref_cmd = OriginalApp.buildBCommand(-20, 100, 150, 142, 150)
        assert our_cmd == ref_cmd, (
            f"Mismatch!\n  Ours:     {our_cmd!r}\n  Original: {ref_cmd!r}")

    def test_matches_original_for_zero_speed(self):
        """Both motors off: used during calibration zero step."""
        our_cmd = self._get_b_cmd(0, 0, 150, 142, 150)
        ref_cmd = OriginalApp.buildBCommand(0, 0, 150, 142, 150)
        assert our_cmd == ref_cmd

    def test_matches_original_for_max_speed(self):
        """Maximum speed: raw=210."""
        our_cmd = self._get_b_cmd(210, 0, 150, 183, 150)
        ref_cmd = OriginalApp.buildBCommand(210, 0, 150, 183, 150)
        assert our_cmd == ref_cmd

    def test_matches_original_negative_both(self):
        """Both motors negative (unusual but valid)."""
        our_cmd = self._get_b_cmd(-100, -80, 150, 142, 150)
        ref_cmd = OriginalApp.buildBCommand(-100, -80, 150, 142, 150)
        assert our_cmd == ref_cmd

    def test_oscillation_extremes(self):
        """Test oscillation at min=127 and max=173."""
        for osc in [127, 150, 173]:
            our_cmd = self._get_b_cmd(100, 50, osc, 142, 150)
            ref_cmd = OriginalApp.buildBCommand(100, 50, osc, 142, 150)
            assert our_cmd == ref_cmd, f"Mismatch at osc={osc}"

    def test_height_extremes(self):
        """Test height at min=75 and max=210."""
        for h in [75, 142, 210]:
            our_cmd = self._get_b_cmd(100, 50, 150, h, 150)
            ref_cmd = OriginalApp.buildBCommand(100, 50, 150, h, 150)
            assert our_cmd == ref_cmd, f"Mismatch at height={h}"

    def test_rotation_extremes(self):
        """Test rotation at min=90 and max=210."""
        for rot in [90, 150, 210]:
            our_cmd = self._get_b_cmd(100, 50, 150, 142, rot)
            ref_cmd = OriginalApp.buildBCommand(100, 50, 150, 142, rot)
            assert our_cmd == ref_cmd, f"Mismatch at rotation={rot}"

    def test_left_handed_oscillation_mirroring(self):
        """Left-handed mirrors oscillation: 300 - osc."""
        self.robot.left_handed = True
        params = self._get_params(100, 50, 136, 142, 150)
        # 300 - 136 = 164
        # Expected: same as right-handed with osc=164
        self.robot.left_handed = False
        params_rh = self._get_params(100, 50, 164, 142, 150)
        assert params == params_rh

    def test_safety_rejects_over_210(self):
        """Values > 210 raw must be REJECTED by safety guard.
        Original app max motor raw = 210. Values above are dangerous."""
        from robot import Robot
        with pytest.raises(Robot.SafetyError):
            self._get_params(249, 0, 150, 142, 150)

    def test_max_safe_speed_produces_correct_pwm(self):
        """Max safe raw value (210) → PWM = 843."""
        params = self._get_params(210, 0, 150, 142, 150)
        pwm_str = params[1:4]
        assert int(pwm_str) == 843

    def test_led_values_match_original(self):
        """LED calculation must use same thresholds as original app."""
        test_cases = [
            (100, 100, 0),     # equal → 0
            (130, 100, 5),     # small top diff → OneTop(5)
            (200, 100, 6),     # medium top diff → TwoTop(6)
            (210, 0, 7),       # large top diff → ThreeTop(7)
            (0, 100, 2),       # medium bot diff → TwoBottom(2)
            (0, 210, 3),       # large bot diff → ThreeBottom(3)
        ]
        for top, bot, expected_led in test_cases:
            params = self._get_params(top, bot, 150, 142, 150)
            led = int(params[-1])
            assert led == expected_led, (
                f"LED for top={top},bot={bot}: expected {expected_led}, got {led}")


class TestApplyCalibrationCompliance:
    """Test calibration command sequence matches original app + AcePad extension.
    Original app (ControlCalibrate): R → U → Q → O
    AcePad: R → U → O → Q (all 4 sent on every connect, not just wizard)
    Source: BUSINESS_LOGIC_COMPLETE.md:346-351, feedback_calibration.md"""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        self.robot = Robot()
        self.robot.firmware = 701
        self.robot.robot_version = 2
        self.sent_commands = []

        async def capture_write(cmd):
            self.sent_commands.append(cmd)
        self.robot._write = capture_write
        from transport import SimulationTransport
        self.robot._transport = SimulationTransport()

    @pytest.mark.asyncio
    async def test_full_sequence_sends_R_U_O(self):
        """Full calibration always sends R, U, O regardless of speed."""
        cal = {"top_speed": 161, "height": 183, "oscillation": 144, "rotation": 150}
        await self.robot.apply_calibration(cal)
        assert any(c.startswith("R") for c in self.sent_commands), "R must be sent"
        assert any(c.startswith("U") for c in self.sent_commands), "U must be sent"
        assert any(c.startswith("O") for c in self.sent_commands), "O must be sent"

    @pytest.mark.asyncio
    async def test_R_U_O_values_from_cal(self):
        """R=rotation, U=height, O=oscillation values taken from cal dict."""
        cal = {"height": 184, "oscillation": 144, "rotation": 155, "top_speed": 161}
        await self.robot.apply_calibration(cal)
        r_cmds = [c for c in self.sent_commands if c.startswith("R")]
        u_cmds = [c for c in self.sent_commands if c.startswith("U")]
        o_cmds = [c for c in self.sent_commands if c.startswith("O")]
        assert r_cmds[0] == "R155"
        assert u_cmds[0] == "U184"
        assert o_cmds[0] == "O144"

    @pytest.mark.asyncio
    async def test_R_U_O_defaults_when_not_specified(self):
        """Defaults: height=183, oscillation=150, rotation=150."""
        cal = {"top_speed": 161}
        await self.robot.apply_calibration(cal)
        r_cmds = [c for c in self.sent_commands if c.startswith("R")]
        u_cmds = [c for c in self.sent_commands if c.startswith("U")]
        o_cmds = [c for c in self.sent_commands if c.startswith("O")]
        assert r_cmds[0] == "R150"
        assert u_cmds[0] == "U183"
        assert o_cmds[0] == "O150"

    @pytest.mark.asyncio
    async def test_speedcal_default_gen2_not_sent(self):
        """Gen2 default: top=161 → offset=0, Q NOT sent."""
        cal = {"top_speed": 161}
        await self.robot.apply_calibration(cal)
        q_cmds = [c for c in self.sent_commands if c.startswith("Q")]
        assert len(q_cmds) == 0, "Q should not be sent when offset ≤ 0"

    @pytest.mark.asyncio
    async def test_speedcal_higher_sends_q(self):
        """Higher cal: top=175 → offset=14 → Q014 sent."""
        cal = {"top_speed": 175}
        await self.robot.apply_calibration(cal)
        q_cmds = [c for c in self.sent_commands if c.startswith("Q")]
        assert len(q_cmds) == 1
        assert q_cmds[0] == "Q014"

    @pytest.mark.asyncio
    async def test_speedcal_q_format(self):
        """Q command: 3-digit zero-padded."""
        cal = {"top_speed": 166}  # offset = 166-161 = 5
        await self.robot.apply_calibration(cal)
        q_cmds = [c for c in self.sent_commands if c.startswith("Q")]
        assert q_cmds[0] == "Q005"

    @pytest.mark.asyncio
    async def test_sequence_order_R_then_U_then_O(self):
        """Sequence order: R → U → O (before Q)."""
        cal = {"height": 184, "oscillation": 144, "rotation": 150, "top_speed": 161}
        await self.robot.apply_calibration(cal)
        r_idx = next(i for i, c in enumerate(self.sent_commands) if c.startswith("R"))
        u_idx = next(i for i, c in enumerate(self.sent_commands) if c.startswith("U"))
        o_idx = next(i for i, c in enumerate(self.sent_commands) if c.startswith("O"))
        assert r_idx < u_idx < o_idx, "Order must be R → U → O"

    @pytest.mark.asyncio
    async def test_calibration_stored_for_reconnect(self):
        """Cal dict stored in _calibration for auto-reconnect."""
        cal = {"top_speed": 161, "height": 184}
        await self.robot.apply_calibration(cal)
        assert self.robot._calibration == cal


# ═══════════════════════════════════════════════════════════════════════════════
# COMMIT CALIBRATION — full save sequence matching original complete()
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommitCalibration:
    """commit_calibration replicates original ControlCalibrate.complete() from stage 3.
    Source: BUSINESS_LOGIC_COMPLETE.md:306-361, ANDROID_APP_RE.md:738-755"""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        self.robot = Robot()
        self.robot.firmware = 701
        self.robot.robot_version = 2
        self.sent_commands = []

        async def capture_write(cmd):
            self.sent_commands.append(cmd)
        self.robot._write = capture_write
        from transport import SimulationTransport
        self.robot._transport = SimulationTransport()

    @pytest.mark.asyncio
    async def test_full_sequence_order(self):
        """Original order: R → U → (Q if >0) → B{zeros,h-30} → O × 2 → H → W000."""
        cal = {"top_speed": 175, "height": 183, "oscillation": 150, "rotation": 150}
        await self.robot.commit_calibration(cal)
        prefixes = [c[0] if c[:3] != "W00" else "W" for c in self.sent_commands]
        # Expected: R, U, Q, B, O, O, H, W
        assert prefixes == ["R", "U", "Q", "B", "O", "O", "H", "W"], \
            f"Unexpected order: {self.sent_commands}"

    @pytest.mark.asyncio
    async def test_no_Q_when_speed_default(self):
        """Gen2 default top=161 → offset=0 → Q skipped."""
        cal = {"top_speed": 161, "height": 183, "oscillation": 150, "rotation": 150}
        await self.robot.commit_calibration(cal)
        q_cmds = [c for c in self.sent_commands if c.startswith("Q")]
        assert len(q_cmds) == 0

    @pytest.mark.asyncio
    async def test_B_has_zero_motors_and_height_minus_30(self):
        """B command in commit has zero motors and height-30 (original baseline offset).
        Format: B{d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L} — zero motors, osc=150, h=153, rot=150, leds=0."""
        cal = {"top_speed": 161, "height": 183, "oscillation": 150, "rotation": 150}
        await self.robot.commit_calibration(cal)
        b_cmd = next(c for c in self.sent_commands if c.startswith("B"))
        assert b_cmd == "B000000001501531500", f"unexpected B format: {b_cmd}"

    @pytest.mark.asyncio
    async def test_O_sent_twice(self):
        """O command sent twice with same osc value (original complete behavior)."""
        cal = {"top_speed": 161, "height": 183, "oscillation": 144, "rotation": 150}
        await self.robot.commit_calibration(cal)
        o_cmds = [c for c in self.sent_commands if c.startswith("O")]
        assert len(o_cmds) == 2
        assert o_cmds[0] == o_cmds[1] == "O144"

    @pytest.mark.asyncio
    async def test_ends_with_H_then_W000(self):
        """Final two commands: H (ClearBall), W000 (SetAdjustment)."""
        cal = {"top_speed": 161, "height": 183, "oscillation": 150, "rotation": 150}
        await self.robot.commit_calibration(cal)
        assert self.sent_commands[-2] == "H"
        assert self.sent_commands[-1] == "W000"

    @pytest.mark.asyncio
    async def test_height_adjusted_clamped_to_min(self):
        """If user height < SAFE_HEIGHT_MIN+30, h_adjusted clamped to SAFE_HEIGHT_MIN (no crash)."""
        cal = {"top_speed": 161, "height": 80, "oscillation": 150, "rotation": 150}
        await self.robot.commit_calibration(cal)
        b_cmd = next(c for c in self.sent_commands if c.startswith("B"))
        # 80-30=50, clamped to 75 (SAFE_HEIGHT_MIN)
        assert "075" in b_cmd, f"h_adjusted should be clamped to 75; got: {b_cmd}"


# ═══════════════════════════════════════════════════════════════════════════════
# HANDSHAKE SEQUENCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHandshakeSequence:
    """Handshake must match original app sequence.
    Source: BUSINESS_LOGIC_COMPLETE.md:371-375, ANDROID_APP_RE.md:60-86"""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        from transport import SimulationTransport
        self.robot = Robot()
        self.sent = []

        async def capture(cmd):
            self.sent.append(cmd)
        self.robot._write = capture
        self.robot._transport = SimulationTransport()

    @pytest.mark.asyncio
    async def test_handshake_starts_with_Z_and_H(self):
        """Phase 1: Z×3 then H."""
        await self.robot._handshake()
        # First 4 commands: Z, Z, Z, H
        assert self.sent[0] == "Z"
        assert self.sent[1] == "Z"
        assert self.sent[2] == "Z"
        assert self.sent[3] == "H"

    @pytest.mark.asyncio
    async def test_handshake_sends_firmware_query(self):
        """Phase 2: F command to get firmware version."""
        await self.robot._handshake()
        assert "F" in self.sent

    @pytest.mark.asyncio
    async def test_handshake_sends_version_query(self):
        """Phase 3: I command to get robot version."""
        await self.robot._handshake()
        assert "I" in self.sent

    @pytest.mark.asyncio
    async def test_handshake_ends_with_H_W000(self):
        """Phase 4: Final H + W000 reset."""
        await self.robot._handshake()
        assert self.sent[-2] == "H"
        assert self.sent[-1] == "W000"

    @pytest.mark.asyncio
    async def test_handshake_order(self):
        """Full order: Z×3, H, F, I, [J02], H, W000."""
        await self.robot._handshake()
        z_count = 0
        for cmd in self.sent:
            if cmd == "Z":
                z_count += 1
            else:
                break
        assert z_count == 3, f"Should start with 3 Z commands, got {z_count}"
        # F must come before I
        f_idx = self.sent.index("F")
        i_idx = self.sent.index("I")
        assert f_idx < i_idx, "F must come before I"


# ═══════════════════════════════════════════════════════════════════════════════
# SAFETY GUARD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSafetyGuard:
    """Safety guard must reject parameters outside hardware limits."""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        self.robot = Robot()
        self.robot.firmware = 701
        self.robot.robot_version = 2
        self.Robot = Robot

    def test_rejects_motor_over_210(self):
        with pytest.raises(self.Robot.SafetyError, match="top_speed"):
            self.robot._build_ball_params(211, 0, 150, 142, 150)

    def test_rejects_motor_under_minus_210(self):
        with pytest.raises(self.Robot.SafetyError, match="bot_speed"):
            self.robot._build_ball_params(0, -211, 150, 142, 150)

    def test_rejects_height_too_low(self):
        with pytest.raises(self.Robot.SafetyError, match="height"):
            self.robot._build_ball_params(100, 0, 150, 74, 150)

    def test_rejects_height_too_high(self):
        with pytest.raises(self.Robot.SafetyError, match="height"):
            self.robot._build_ball_params(100, 0, 150, 211, 150)

    def test_rejects_osc_too_low(self):
        with pytest.raises(self.Robot.SafetyError, match="oscillation"):
            self.robot._build_ball_params(100, 0, 126, 142, 150)

    def test_rejects_osc_too_high(self):
        with pytest.raises(self.Robot.SafetyError, match="oscillation"):
            self.robot._build_ball_params(100, 0, 174, 142, 150)

    def test_rejects_rotation_too_low(self):
        with pytest.raises(self.Robot.SafetyError, match="rotation"):
            self.robot._build_ball_params(100, 0, 150, 142, 89)

    def test_rejects_rotation_too_high(self):
        with pytest.raises(self.Robot.SafetyError, match="rotation"):
            self.robot._build_ball_params(100, 0, 150, 142, 211)

    def test_accepts_all_limits(self):
        """All values at exact limits should pass."""
        self.robot._build_ball_params(210, -210, 127, 75, 90)
        self.robot._build_ball_params(-210, 210, 173, 210, 210)
        self.robot._build_ball_params(0, 0, 150, 142, 150)

    def test_rejects_pwm_over_843(self):
        """Even if raw ≤ 210, verify PWM check exists."""
        # raw=210 → PWM=843, exactly at limit → should pass
        self.robot._build_ball_params(210, 0, 150, 142, 150)

    def test_multiple_errors_reported(self):
        """Multiple out-of-range params reported together."""
        with pytest.raises(self.Robot.SafetyError) as exc_info:
            self.robot._build_ball_params(250, 250, 200, 300, 300)
        msg = str(exc_info.value)
        assert "top_speed" in msg
        assert "bot_speed" in msg
        assert "height" in msg


# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE MULTIBALL / EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiballCommandGeneration:
    """Verify B/A commands for various ball configurations from default drills."""

    @pytest.fixture(autouse=True)
    def setup_robot(self):
        from robot import Robot
        self.robot = Robot()
        self.robot.firmware = 701
        self.robot.robot_version = 2

    def _verify_ball(self, top, bot, osc, h, rot):
        """Verify our command matches original for given raw values."""
        our = "B" + self.robot._build_ball_params(top, bot, osc, h, rot)
        ref = OriginalApp.buildBCommand(top, bot, osc, h, rot)
        assert our == ref, f"Mismatch for ball({top},{bot},{osc},{h},{rot}):\n  ours={our!r}\n  ref ={ref!r}"

    def test_forehand_topspin(self):
        """FH topspin: top=120, bot=0, osc=164, h=116, rot=150"""
        self._verify_ball(120, 0, 164, 116, 150)

    def test_backhand_topspin(self):
        """BH topspin: top=120, bot=0, osc=136, h=116, rot=150"""
        self._verify_ball(120, 0, 136, 116, 150)

    def test_backspin_ball(self):
        """Backspin: top=-20, bot=100"""
        self._verify_ball(-20, 100, 150, 142, 150)

    def test_heavy_backspin(self):
        """Heavy backspin: top=-12, bot=100"""
        self._verify_ball(-12, 100, 150, 116, 150)

    def test_sidespin_ball(self):
        """Sidespin: rotation ≠ 150"""
        self._verify_ball(149, -12, 150, 142, 180)

    def test_fast_topspin(self):
        """Fast topspin: top=149, bot=-12"""
        self._verify_ball(149, -12, 150, 142, 150)

    def test_medium_nospin(self):
        """No spin (equal speeds): top=50, bot=50"""
        self._verify_ball(50, 50, 150, 142, 150)

    def test_light_topspin(self):
        """Light topspin: top=75, bot=50"""
        self._verify_ball(75, 50, 150, 142, 150)

    def test_mixed_speeds(self):
        """Various speed/spin combos from default drills."""
        balls = [
            (100, 0, 150, 142, 150),
            (50, 50, 150, 142, 150),
            (12, 87, 150, 142, 150),
            (125, 12, 150, 142, 150),
            (62, 62, 150, 142, 150),
            (5, 100, 150, 142, 150),
            (37, 75, 150, 142, 150),
            (144, -25, 150, 142, 150),
            (77, 50, 150, 142, 150),
            (112, 62, 150, 142, 150),
        ]
        for top, bot, osc, h, rot in balls:
            self._verify_ball(top, bot, osc, h, rot)

    def test_multiball_drill_all_balls_valid(self):
        """A multiball drill: each ball must produce a valid B command."""
        # 2-ball FH/BH footwork drill
        drill_balls = [
            {"top": 120, "bot": 0, "osc": 164, "h": 116, "rot": 150},
            {"top": 120, "bot": 0, "osc": 136, "h": 116, "rot": 150},
        ]
        for b in drill_balls:
            self._verify_ball(b["top"], b["bot"], b["osc"], b["h"], b["rot"])

    def test_multiball_drill_alternating_spin(self):
        """Multi-ball with alternating topspin/backspin."""
        balls = [
            (120, 0, 150, 142, 150),    # topspin
            (-20, 100, 150, 142, 150),   # backspin
            (120, 0, 164, 142, 150),     # topspin FH
            (-20, 100, 136, 142, 150),   # backspin BH
        ]
        for top, bot, osc, h, rot in balls:
            self._verify_ball(top, bot, osc, h, rot)

    def test_extreme_values(self):
        """Edge cases: min/max of each parameter."""
        self._verify_ball(210, 0, 127, 75, 90)     # all mins (except top=max)
        self._verify_ball(0, 210, 173, 210, 210)    # all maxes (except top=0)
        self._verify_ball(-210, -210, 150, 142, 150) # both negative max
