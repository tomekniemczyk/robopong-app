import asyncio
import logging
import random as _random
from typing import Callable, Dict, List, Optional

import audio
from transport import RobotTransport, BLETransport, USBTransport, SimulationTransport

from bleak import BleakScanner

logger = logging.getLogger(__name__)


class Robot:
    def __init__(self, on_event: Optional[Callable] = None):
        self._transport: Optional[RobotTransport] = None
        self._drill:       Optional[asyncio.Task] = None
        self._reconnect:   Optional[asyncio.Task] = None
        self.firmware:     int = 0
        self.robot_version: int = -1
        self.device:       str = ""
        self._last_addr:   str = ""
        self._auto_reconnect: bool = False
        self._health_task: Optional[asyncio.Task] = None
        self._awaiting_version: bool = False
        self._fw_buffer:   str = ""
        self._on_event = on_event or (lambda *_: None)
        self._listeners: List[Callable] = []
        self.left_handed: bool = False
        # Drill mode: "auto" (BLE FW>=701→async, else sync), "sync", "async"
        self.drill_mode: str = "auto"
        self._drill_response_queue: Optional[asyncio.Queue] = None
        self._tracking_drill_responses: bool = False
        self._calibration: Optional[dict] = None   # stored after apply_calibration, re-applied on reconnect

    # ── listener API ──────────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict):
        self._on_event(event_type, data)
        for cb in self._listeners:
            cb(event_type, data)

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    # ── discovery ─────────────────────────────────────────────────────────────

    async def scan(self, timeout: float = 8.0) -> List[Dict]:
        devices = await BleakScanner.discover(timeout=timeout)
        return [{"name": d.name or "(brak nazwy)", "address": d.address} for d in devices]

    def usb_ports(self) -> List[str]:
        return USBTransport.list_ports()

    # ── connection ────────────────────────────────────────────────────────────

    async def connect(self, address: str) -> bool:
        self._last_addr = address
        self._auto_reconnect = True
        return await self._do_connect(address)

    async def _do_connect(self, address: str) -> bool:
        await self._disconnect_transport()
        transport = BLETransport()
        transport.set_on_data(self._on_data)
        ok = await transport.connect(address)
        if ok:
            transport.set_on_disconnect(self._on_ble_disconnect)
            self._transport = transport
            self.device = address
            self._push_status()
            await self._handshake()
            self._start_health_monitor()
            return True
        self._emit("error", {"message": f"BLE connection failed: {address}"})
        return False

    async def connect_usb(self, port: str) -> bool:
        await self._disconnect_transport()
        transport = USBTransport()
        ok = await transport.connect(port)
        if ok:
            self._transport = transport
            self.device = f"USB:{port}"
            self._push_status()
            self._emit("usb_connected", {"port": port})
            return True
        self._emit("error", {"message": f"USB connection failed: {port}"})
        return False

    def enable_simulation(self):
        self._transport = SimulationTransport()
        self.device = "SIMULATION"
        self.firmware = 999
        self.robot_version = 2
        self._push_status()

    def disable_simulation(self):
        self._transport = None
        self.device = ""
        self.firmware = 0
        self.robot_version = -1
        self._push_status()

    async def reset_ble(self):
        logger.info("Resetting BLE for %s", self._last_addr)
        addr = self._last_addr
        self._stop_health_monitor()
        await self._disconnect_transport()
        self.firmware = 0
        self.robot_version = -1
        self.device = ""
        self._push_status()
        await asyncio.sleep(2)
        if self._auto_reconnect and addr:
            if not await self._do_connect(addr):
                await asyncio.sleep(5)
                await self._do_connect(addr)

    async def disconnect(self):
        self._auto_reconnect = False
        self._stop_drill_nowait()
        self._stop_health_monitor()
        if self._reconnect and not self._reconnect.done():
            self._reconnect.cancel()
        if self._transport and self._transport.is_connected:
            try:
                await self._write("H")
                await self._transport.disconnect()
            except Exception:
                pass
        self._transport = None
        self.firmware = 0
        self.robot_version = -1
        self.device = ""
        self._push_status()

    async def _disconnect_transport(self):
        transport = self._transport
        self._transport = None
        if transport:
            transport.set_on_disconnect(None)
            if transport.is_connected:
                try:
                    await transport.disconnect()
                except Exception:
                    pass

    # ── robot control ─────────────────────────────────────────────────────────

    # ── safety limits (from original Newgy app RE analysis) ─────────────────
    SAFE_MOTOR_RAW_MAX = 210       # getMotorSpeed max output
    SAFE_HEIGHT_MIN = 75
    SAFE_HEIGHT_MAX = 210
    SAFE_OSC_MIN = 127
    SAFE_OSC_MAX = 173
    SAFE_ROT_MIN = 90
    SAFE_ROT_MAX = 210
    SAFE_PWM_MAX = 843             # 210 * 4.016 — original app max

    class SafetyError(Exception):
        """Raised when ball parameters would send unsafe values to robot."""
        pass

    def _validate_ball_params(self, top: int, bot: int, osc: int, height: int, rotation: int):
        """Validate parameters are within safe hardware limits.
        Raises SafetyError if any parameter could damage the robot."""
        errors = []
        if abs(top) > self.SAFE_MOTOR_RAW_MAX:
            errors.append(f"top_speed={top} exceeds ±{self.SAFE_MOTOR_RAW_MAX}")
        if abs(bot) > self.SAFE_MOTOR_RAW_MAX:
            errors.append(f"bot_speed={bot} exceeds ±{self.SAFE_MOTOR_RAW_MAX}")
        if not (self.SAFE_HEIGHT_MIN <= height <= self.SAFE_HEIGHT_MAX):
            errors.append(f"height={height} outside {self.SAFE_HEIGHT_MIN}-{self.SAFE_HEIGHT_MAX}")
        if not (self.SAFE_OSC_MIN <= osc <= self.SAFE_OSC_MAX):
            errors.append(f"oscillation={osc} outside {self.SAFE_OSC_MIN}-{self.SAFE_OSC_MAX}")
        if not (self.SAFE_ROT_MIN <= rotation <= self.SAFE_ROT_MAX):
            errors.append(f"rotation={rotation} outside {self.SAFE_ROT_MIN}-{self.SAFE_ROT_MAX}")
        pwm_t = round(abs(top) * 4.016)
        pwm_b = round(abs(bot) * 4.016)
        if pwm_t > self.SAFE_PWM_MAX:
            errors.append(f"top PWM={pwm_t} exceeds {self.SAFE_PWM_MAX}")
        if pwm_b > self.SAFE_PWM_MAX:
            errors.append(f"bot PWM={pwm_b} exceeds {self.SAFE_PWM_MAX}")
        if errors:
            raise Robot.SafetyError("; ".join(errors))

    def _build_ball_params(self, top: int, bot: int, osc: int, height: int, rotation: int) -> str:
        """Build ball parameter string for B/A commands.
        Format: {d}{sss}{d}{sss}{ooo}{hhh}{rrr}{L} — 18 chars.
        Source: BUSINESS_LOGIC_COMPLETE.md:252, ANDROID_APP_RE.md:521"""
        self._validate_ball_params(top, bot, osc, height, rotation)
        if self.left_handed:
            osc = 300 - osc  # mirror around center 150 (127↔173)
        dir_t = 1 if top < 0 else 0
        dir_b = 1 if bot < 0 else 0
        spd_t = min(999, round(abs(top) * 4.016))
        spd_b = min(999, round(abs(bot) * 4.016))
        leds  = self._spin_leds(top, bot)
        return f"{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"

    async def set_ball(self, top: int, bot: int, osc: int, height: int, rotation: int, wait_ms: int = 1500):
        try:
            params = self._build_ball_params(top, bot, osc, height, rotation)
        except Robot.SafetyError as e:
            logger.error("SAFETY STOP: %s", e)
            await self._write("H")
            self._emit("error", {"message": f"SAFETY: {e}", "critical": True})
            raise
        cmd = f"B{params}"
        logger.debug("→ B top=%d bot=%d osc=%d h=%d rot=%d cmd=%s", top, bot, osc, height, rotation, cmd)
        await self._write(cmd)
        if self.is_simulation:
            audio.play("sim_motor_start")

    def _effective_drill_mode(self) -> str:
        """Determine drill mode. Default: sync (app-controlled timing via B+T).

        Async mode (wTA+A+END, robot-managed) has unresolved issues on Gen2/FW701:
        robot sends N after loaded-ball-count throws (not END count), causing
        drill to restart every few balls (head lowers and drill begins again).
        Until the firmware behavior is better understood, sync is the safe default.

        User can opt in to async via `set_drill_mode` WS action for testing."""
        if self.drill_mode != "auto":
            return self.drill_mode
        return "sync"

    async def throw(self):
        logger.debug("→ T")
        await self._write("T")
        if self.is_simulation:
            audio.play("sim_throw")

    async def stop(self):
        """Force full motor stop. Sends B{zeros}+H+H sequence because H alone
        sometimes leaves flywheel spinning on FW 701 (observed: 1-2 min coast
        after mid-drill stop). B with zero PWM explicitly clears motor speed."""
        logger.debug("→ STOP: B{zeros} + H×2")
        self._stop_drill_nowait()
        try:
            zero_params = self._build_ball_params(0, 0, 150, 150, 150)
            await self._write(f"B{zero_params}")
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning("stop: B{zeros} failed: %s", e)
        await self._write("H")
        await asyncio.sleep(0.05)
        await self._write("H")
        if self.is_simulation:
            audio.play("sim_motor_stop")

    async def reset_head(self):
        """Send head reset command (V) for calibration."""
        await self._write("V")

    async def apply_calibration(self, cal: dict):
        """Restore calibration offsets after connect/reconnect (minimal sequence).

        Firmware stores U/O/R as head position offsets:
          effective_h   = h_B   + (U - 150)
          effective_osc = osc_B + (O - 150)
          effective_rot = rot_B + (R - 150)

        Original app sent offsets only during calibration wizard and relied on
        firmware to persist them. Robopong 3050XL does NOT persist across power
        cycles, so we resend R/U/O/Q after every connect.

        For saving calibration from UI, use commit_calibration() which runs the
        full original ControlCalibrate.complete() sequence."""
        self._calibration = cal

        h   = cal.get("height",      183)
        osc = cal.get("oscillation", 150)
        rot = cal.get("rotation",    150)
        top = cal.get("top_speed",   161)

        await self._write(f"R{rot:03d}")
        await asyncio.sleep(0.3)
        await self._write(f"U{h:03d}")
        await asyncio.sleep(0.3)
        await self._write(f"O{osc:03d}")
        await asyncio.sleep(0.3)

        speed_cal = top - 161  # Gen2 baseline
        if speed_cal > 0:
            await self._write(f"Q{speed_cal:03d}")
            await asyncio.sleep(0.3)

        logger.info("Calibration restored: R=%d U=%d O=%d Q=%d", rot, h, osc, speed_cal)

    async def commit_calibration(self, cal: dict):
        """Save calibration from UI — full sequence matching original complete() in stage 3.

        Original flow (ControlCalibrate.complete, BUSINESS_LOGIC_COMPLETE.md:306-361):
          1. R{rot}   — commit rotation offset (end of stage 1 in wizard)
          2. U{h}     — commit height offset   (end of stage 2 in wizard)
          3. Q{speed} — commit speed offset    (stage 3, only if offset > 0)
          4. B{zeros, h-30, osc, rot} — final state with zero motors, height-30
          5. wait 500ms
          6. O{osc} × 2 with 500ms between — adjust oscillation (sent twice)
          7. H    — ClearBall
          8. W000 — SetAdjustment (end of calibration session)

        AcePad uses 1-screen UI but matches the protocol exactly."""
        self._calibration = cal

        h   = cal.get("height",      183)
        osc = cal.get("oscillation", 150)
        rot = cal.get("rotation",    150)
        top = cal.get("top_speed",   161)

        await self._write(f"R{rot:03d}")
        await asyncio.sleep(0.3)
        await self._write(f"U{h:03d}")
        await asyncio.sleep(0.3)

        speed_cal = top - 161  # Gen2 baseline
        if speed_cal > 0:
            await self._write(f"Q{speed_cal:03d}")
            await asyncio.sleep(0.3)

        # B with zero motors and height-30 (original baseline offset compensation)
        h_adjusted = max(self.SAFE_HEIGHT_MIN, h - 30)
        params = self._build_ball_params(0, 0, osc, h_adjusted, rot)
        await self._write(f"B{params}")
        await asyncio.sleep(0.5)

        # Adjust Oscillation × 2 (original sends twice with 500ms between)
        await self._write(f"O{osc:03d}")
        await asyncio.sleep(0.5)
        await self._write(f"O{osc:03d}")
        await asyncio.sleep(0.3)

        # Finish: ClearBall + SetAdjustment
        await self._write("H")
        await asyncio.sleep(0.3)
        await self._write("W000")

        logger.info("Calibration committed: R=%d U=%d O=%d Q=%d + B{zeros,h-30} + O×2 + H + W000",
                    rot, h, osc, speed_cal)

    # ── drill runner ──────────────────────────────────────────────────────────

    async def run_drill(self, balls: List[Dict], repeat: int = 1, count: int = 0, percent: int = 100, skip_warmup: bool = False, emit_countdown: bool = True):
        if self._drill and not self._drill.done():
            self._drill.cancel()

        min_wait_ms = 500 if len(balls) == 1 else 750
        mode = self._effective_drill_mode()
        logger.info("Drill start: mode=%s, balls=%d, repeat=%s, count=%d, percent=%d",
                     mode, len(balls), "inf" if repeat == 0 else repeat, count, percent)

        if mode == "async":
            self._drill = asyncio.create_task(
                self._drill_loop_async(balls, repeat, count, percent, min_wait_ms, skip_warmup, emit_countdown))
        else:
            self._drill = asyncio.create_task(
                self._drill_loop_sync(balls, repeat, count, percent, min_wait_ms, skip_warmup, emit_countdown))

    # ── async drill: wTA + A + END (FW >= 701, robot manages timing) ─────

    async def _drill_loop_async(self, balls, repeat, count, percent, min_wait_ms, skip_warmup, emit_countdown):
        """Async protocol: preload balls via wTA+A, execute via END, robot manages throws."""
        # Build ball commands (params + adjusted wait)
        ball_cmds = []
        for b in balls:
            try:
                params = self._build_ball_params(
                    b["top_speed"], b["bot_speed"],
                    b["oscillation"], b["height"], b["rotation"])
            except Robot.SafetyError as e:
                logger.error("SAFETY STOP in drill: %s", e)
                await self._write("H")
                self._emit("error", {"message": f"SAFETY: {e}", "critical": True})
                self._emit("drill_ended", {})
                return
            raw_wait = b.get("wait_ms", 1500)
            adj_wait = max(min_wait_ms, int(raw_wait * (100 + (100 - percent)) / 100))
            ball_cmds.append((params, adj_wait))

        thrown = 0
        self._drill_response_queue = asyncio.Queue()

        try:
            # Clean stop before loading — no B pre-spin (mixing B with A confuses firmware)
            await self._write("H")
            await asyncio.sleep(0.2)

            while True:
                # Calculate batch size for END command (max 999)
                if count > 0:
                    remaining = count - thrown
                elif repeat > 0:
                    remaining = len(balls) * repeat - thrown
                else:
                    remaining = 999  # infinite — batch at 999
                if remaining <= 0:
                    break
                batch = min(remaining, 999)

                # Load all balls: wTA + A for each
                # Original app waits for K after each command — add delays to let robot process
                for params, wait_ms in ball_cmds:
                    wta = max(1, wait_ms // 10)
                    logger.debug("→ wTA%03d + A%s...", wta, params[:12])
                    await self._write(f"wTA{wta:03d}")
                    await asyncio.sleep(0.15)  # wait for robot to process wTA (K)
                    await self._write(f"A{params}")
                    await asyncio.sleep(0.15)  # wait for robot to process A (K)

                # Clear stray responses from loading phase
                while not self._drill_response_queue.empty():
                    try:
                        self._drill_response_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                # Start tracking + send END
                self._tracking_drill_responses = True
                seed = _random.randint(1, 255)
                cmd = f"END{batch:03d}{seed:03d}000"
                logger.info("→ %s (batch=%d)", cmd, batch)
                await self._write(cmd)

                # Simulation: fake K/N responses
                if self.is_simulation:
                    asyncio.create_task(self._simulate_drill_responses(batch, ball_cmds))

                # Wait for K (ball thrown) and N (drill complete) from robot
                batch_thrown = 0
                while batch_thrown < batch:
                    try:
                        resp = await asyncio.wait_for(self._drill_response_queue.get(), timeout=60)
                    except asyncio.TimeoutError:
                        logger.warning("Drill response timeout after %d/%d balls", batch_thrown, batch)
                        break
                    if resp == "K":
                        thrown += 1
                        batch_thrown += 1
                        ball_idx = (thrown - 1) % len(balls)
                        run = (thrown - 1) // len(balls)
                        self._emit("drill_progress", {
                            "ball": ball_idx + 1, "total": len(balls), "run": run + 1,
                            "max_repeat": repeat, "thrown": thrown, "count": count, "percent": percent,
                        })
                        if count > 0 and thrown >= count:
                            break
                    elif resp == "N":
                        logger.debug("Robot sent N — batch complete (%d thrown)", batch_thrown)
                        break

                self._tracking_drill_responses = False

                # Check termination
                if count > 0 and thrown >= count:
                    break
                if repeat > 0 and thrown >= len(balls) * repeat:
                    break
                # infinite (repeat=0, count=0): reload balls and send another END
        except asyncio.CancelledError:
            pass
        finally:
            self._tracking_drill_responses = False
            self._drill_response_queue = None
            try:
                zero_params = self._build_ball_params(0, 0, 150, 150, 150)
                await self._write(f"B{zero_params}")
                await asyncio.sleep(0.05)
            except Exception:
                pass
            await self._write("H")
            self._emit("drill_ended", {})

    async def _simulate_drill_responses(self, count: int, ball_cmds: list):
        """Simulate robot K/N responses for simulation mode."""
        for i in range(count):
            if not self._drill_response_queue:
                return
            _, wait_ms = ball_cmds[i % len(ball_cmds)]
            await asyncio.sleep(wait_ms / 1000)
            if self._drill_response_queue:
                self._drill_response_queue.put_nowait("K")
                audio.play("sim_throw")
        await asyncio.sleep(0.1)
        if self._drill_response_queue:
            self._drill_response_queue.put_nowait("N")

    # ── sync drill: B + T (legacy/USB, app manages timing) ───────────────

    async def _drill_loop_sync(self, balls, repeat, count, percent, min_wait_ms, skip_warmup, emit_countdown):
        """Sync protocol: B command + T throw, app controls all timing."""
        # Pre-validate all balls before starting
        for b in balls:
            try:
                self._validate_ball_params(
                    b["top_speed"], b["bot_speed"], b["oscillation"], b["height"], b["rotation"])
            except Robot.SafetyError as e:
                logger.error("SAFETY STOP in drill: %s", e)
                await self._write("H")
                self._emit("error", {"message": f"SAFETY: {e}", "critical": True})
                self._emit("drill_ended", {})
                return

        first_ball_ready = False
        if not skip_warmup:
            b0 = balls[0]
            await self._write("H")
            await asyncio.sleep(0.1)
            warmup_top = min(abs(b0["top_speed"]), self.SAFE_MOTOR_RAW_MAX) * (1 if b0["top_speed"] >= 0 else -1)
            warmup_bot = min(abs(b0["bot_speed"]), self.SAFE_MOTOR_RAW_MAX) * (1 if b0["bot_speed"] >= 0 else -1) if b0["bot_speed"] != 0 else 0
            await self.set_ball(warmup_top, warmup_bot, b0["oscillation"], b0["height"], b0["rotation"], b0.get("wait_ms", 1000))
            if emit_countdown:
                self._emit("drill_countdown", {"sec": 3})
            await asyncio.sleep(1.0)
            if emit_countdown:
                self._emit("drill_countdown", {"sec": 2})
            await asyncio.sleep(1.0)
            await self.set_ball(b0["top_speed"], b0["bot_speed"], b0["oscillation"], b0["height"], b0["rotation"], b0.get("wait_ms", 1000))
            if emit_countdown:
                self._emit("drill_countdown", {"sec": 1})
            await asyncio.sleep(1.0)
            first_ball_ready = True

        run = 0
        thrown = 0
        try:
            while repeat == 0 or run < repeat:
                for i, b in enumerate(balls):
                    if count > 0 and thrown >= count:
                        return
                    raw_wait = b.get("wait_ms", 1500)
                    adj_wait = max(min_wait_ms, int(raw_wait * (100 + (100 - percent)) / 100))
                    if first_ball_ready:
                        first_ball_ready = False
                    else:
                        await self.set_ball(b["top_speed"], b["bot_speed"],
                                            b["oscillation"], b["height"], b["rotation"], adj_wait)
                        await asyncio.sleep(0.15)
                    await self.throw()
                    thrown += 1
                    self._emit("drill_progress", {
                        "ball": i + 1, "total": len(balls), "run": run + 1,
                        "max_repeat": repeat, "thrown": thrown, "count": count, "percent": percent,
                    })
                    await asyncio.sleep(max(0.3, adj_wait / 1000 - 0.15))
                run += 1
        except asyncio.CancelledError:
            pass
        finally:
            try:
                zero_params = self._build_ball_params(0, 0, 150, 150, 150)
                await self._write(f"B{zero_params}")
                await asyncio.sleep(0.05)
            except Exception:
                pass
            await self._write("H")
            self._emit("drill_ended", {})

    def stop_drill(self):
        self._stop_drill_nowait()
        asyncio.create_task(self._write("H"))

    # ── health monitor ────────────────────────────────────────────────────────

    def _start_health_monitor(self):
        self._stop_health_monitor()
        self._health_task = asyncio.create_task(self._health_loop())

    def _stop_health_monitor(self):
        if self._health_task and not self._health_task.done():
            self._health_task.cancel()

    async def _health_loop(self):
        try:
            while True:
                await asyncio.sleep(10)
                if not self.is_connected or self.transport_type != "ble":
                    break
                await self._write("Z")
                await asyncio.sleep(3)
                ble = self._transport
                if isinstance(ble, BLETransport) and asyncio.get_event_loop().time() - ble.last_notify > 30:
                    logger.warning("No BLE response for 30s — resetting")
                    await self.reset_ble()
                    break
        except asyncio.CancelledError:
            pass

    # ── internal ──────────────────────────────────────────────────────────────

    async def _handshake(self):
        # Phase 1: Init — Z×3 + H (like original apps)
        for _ in range(3):
            await self._write("Z")
            await asyncio.sleep(0.12)
        await self._write("H")
        await asyncio.sleep(0.5)

        # Phase 2: Firmware — enable buffering BEFORE sending F
        self._fw_buffer = ""
        self._awaiting_version = True
        await self._write("F")
        # Original app waits 2s; BLE may deliver "701" as "7"+"01" fragments
        for _ in range(20):
            await asyncio.sleep(0.1)
            if self.firmware > 0:
                break

        # Phase 3: Robot version — send I only after firmware detected
        await self._write("I")
        for _ in range(10):
            await asyncio.sleep(0.1)
            if self.robot_version >= 0:
                break
        self._awaiting_version = False
        self._fw_buffer = ""

        if self.robot_version < 0 and self.firmware >= 220:
            logger.info("Version unknown, forcing Gen2 (J02)")
            await self._write("J02")
            self.robot_version = 2
            await asyncio.sleep(0.2)

        # Phase 4: Final reset
        await self._write("H")
        await asyncio.sleep(0.1)
        await self._write("W000")
        await asyncio.sleep(0.2)
        logger.info("Handshake complete: fw=%d version=%d", self.firmware, self.robot_version)

    async def _write(self, cmd: str):
        if not self._transport or not self._transport.is_connected:
            logger.warning("Cannot send '%s' — not connected", cmd)
            return
        await self._transport.write(cmd)

    def _on_data(self, text: str):
        """Callback from BLE transport notifications."""
        self._emit("robot_response", {"data": text})

        # Capture K/N during async drill execution (after END sent)
        if self._tracking_drill_responses and self._drill_response_queue:
            for ch in text:
                if ch in ("K", "N"):
                    try:
                        self._drill_response_queue.put_nowait(ch)
                    except asyncio.QueueFull:
                        pass

        if self._awaiting_version:
            if text in ("K", "N", "M"):
                return
            # Version digit (single 0-2) — only after firmware already detected
            if len(text) == 1 and text in ("0", "1", "2") and self.firmware > 0:
                self.robot_version = int(text)
                self._awaiting_version = False
                self._fw_buffer = ""
                logger.info("Robot version: %d (%s)", self.robot_version,
                            {0: "OriginalNewFW", 1: "Original", 2: "SecondRun/Gen2"}.get(self.robot_version, "?"))
                self._push_status()
                return
            # Buffer numeric fragments — BLE may split e.g. "701" into "7"+"01"
            try:
                int(text)
                self._fw_buffer += text
                fw = int(self._fw_buffer)
                if 100 <= fw <= 9999:
                    self.firmware = fw
                    logger.info("Firmware detected: %d", fw)
                    self._push_status()
            except ValueError:
                self._fw_buffer = ""
            return

        try:
            v = int(text)
            if 100 <= v <= 9999:
                self.firmware = v
                self._push_status()
        except ValueError:
            pass

    def _on_ble_disconnect(self):
        """Callback from BLE transport disconnect."""
        self._transport = None
        self.firmware = 0
        self.robot_version = -1
        self.device = ""
        self._stop_health_monitor()
        self._push_status()
        if self._auto_reconnect and self._last_addr:
            if self._reconnect and not self._reconnect.done():
                self._reconnect.cancel()
            logger.info("BLE disconnected — reconnecting to %s", self._last_addr)
            self._reconnect = asyncio.create_task(self._reconnect_loop())

    def _push_status(self):
        self._emit("status", {
            "connected":     self.is_connected,
            "firmware":      self.firmware,
            "robot_version": self.robot_version,
            "device":        self.device,
            "transport":     self.transport_type,
            "drill_mode":    self.drill_mode,
            "effective_drill_mode": self._effective_drill_mode(),
        })

    async def _reconnect_loop(self):
        delays = [2, 3, 5, 10, 15, 30, 30, 60]
        for delay in delays:
            await asyncio.sleep(delay)
            if not self._auto_reconnect or self.is_connected:
                return
            logger.info("Reconnecting to %s (%ds)", self._last_addr, delay)
            self._emit("reconnecting", {"address": self._last_addr})
            ok = await self._do_connect(self._last_addr)
            if ok:
                logger.info("Reconnected successfully")
                if self._calibration:
                    await self.apply_calibration(self._calibration)
                return
        logger.warning("Reconnect failed — all attempts exhausted")
        self._emit("error", {"message": "Nie udało się ponownie połączyć z robotem"})

    def _stop_drill_nowait(self):
        if self._drill and not self._drill.done():
            self._drill.cancel()

    @staticmethod
    def _spin_leds(top: int, bot: int) -> int:
        diff = top - bot
        if diff == 0:
            return 0
        ratio = abs(diff) / 360.0
        if ratio <= 0.10:   level = 1
        elif ratio <= 0.50: level = 2
        elif ratio <= 0.75: level = 3
        else:               level = 4
        return level + 4 if diff > 0 else level

    @property
    def is_connected(self) -> bool:
        return self._transport is not None and self._transport.is_connected

    @property
    def transport_type(self) -> str:
        return self._transport.transport_type if self._transport else ""

    @property
    def is_simulation(self) -> bool:
        return isinstance(self._transport, SimulationTransport)
