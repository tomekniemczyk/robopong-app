import asyncio
import logging
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

    async def set_ball(self, top: int, bot: int, osc: int, height: int, rotation: int, wait_ms: int = 1500):
        if self.left_handed:
            osc = 300 - osc  # mirror around center 150 (127↔173)
        dir_t = 1 if top < 0 else 0
        dir_b = 1 if bot < 0 else 0
        spd_t = min(999, int(abs(top) * 4.016))
        spd_b = min(999, int(abs(bot) * 4.016))
        leds  = self._spin_leds(top, bot)

        # Always use B command — starts motors immediately.
        # A command (fw >= 701) requires END protocol which we don't use yet;
        # without END, A sets params but may not spin motors → balls drop.
        cmd = f"B{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"

        logger.debug("→ %s top=%d bot=%d osc=%d h=%d rot=%d", cmd[:1], top, bot, osc, height, rotation)
        await self._write(cmd)
        if self.is_simulation:
            audio.play("sim_motor_start")

    async def throw(self):
        logger.debug("→ T")
        await self._write("T")
        if self.is_simulation:
            audio.play("sim_throw")

    async def stop(self):
        logger.debug("→ H (stop)")
        self._stop_drill_nowait()
        await self._write("H")
        if self.is_simulation:
            audio.play("sim_motor_stop")

    async def reset_head(self):
        """Send head reset command (V) for calibration."""
        await self._write("V")

    async def apply_calibration(self, cal: dict):
        """Send SpeedCAL (Q) to firmware after connect.
        U/O/R are NOT sent here — they set persistent firmware offsets that would
        be ADDED to every B command, making all balls fly too high/wide.
        U/O/R are only sent during the calibration wizard (same as original app)."""
        top = cal.get("top_speed", 161)
        speed_cal = top - 161
        if speed_cal > 0:
            await self._write(f"Q{speed_cal:03d}")
            await asyncio.sleep(0.3)
            logger.info("SpeedCAL applied: Q=%d", speed_cal)
        else:
            logger.info("SpeedCAL: no offset needed (top=%d)", top)

    # ── drill runner ──────────────────────────────────────────────────────────

    async def run_drill(self, balls: List[Dict], repeat: int = 1, count: int = 0, percent: int = 100, skip_warmup: bool = False, emit_countdown: bool = True):
        if self._drill and not self._drill.done():
            self._drill.cancel()

        min_wait_ms = 500 if len(balls) == 1 else 750

        async def _loop():
            first_ball_ready = False
            if not skip_warmup:
                # Phase 1: Spin flywheel at boosted speed (2s) — reach full RPM from standstill
                b0 = balls[0]
                await self._write("H")
                await asyncio.sleep(0.1)
                warmup_top = max(abs(b0["top_speed"]), 200) * (1 if b0["top_speed"] >= 0 else -1)
                warmup_bot = max(abs(b0["bot_speed"]), 200) * (1 if b0["bot_speed"] >= 0 else -1) if b0["bot_speed"] != 0 else 0
                await self.set_ball(warmup_top, warmup_bot, b0["oscillation"], b0["height"], b0["rotation"], b0.get("wait_ms", 1000))
                if emit_countdown:
                    self._emit("drill_countdown", {"sec": 3})
                await asyncio.sleep(1.0)
                if emit_countdown:
                    self._emit("drill_countdown", {"sec": 2})
                await asyncio.sleep(1.0)
                # Phase 2: Settle to actual drill params (1s) before first throw
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
                            await self.set_ball(b["top_speed"], b["bot_speed"], b["oscillation"], b["height"], b["rotation"], adj_wait)
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
                await self._write("H")
                self._emit("drill_ended", {})

        self._drill = asyncio.create_task(_loop())

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
