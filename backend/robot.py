import asyncio
import glob
import logging
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

logger = logging.getLogger(__name__)

MLDP_SERVICE   = "00035b03-58e6-07dd-021a-08123a000300"
MLDP_DATA_CHAR = "00035b03-58e6-07dd-021a-08123a000301"
MLDP_CTRL_CHAR = "00035b03-58e6-07dd-021a-08123a0003ff"


# ─── BLE system helpers ─────────────────────────────────────────────────────

def _bt_cmd(*args, timeout=5) -> str:
    try:
        r = subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except Exception as e:
        logger.warning("Bluetooth command failed: %s", e)
        return ""

def _bt_disconnect(address: str):
    _bt_cmd("disconnect", address)

def _bt_is_paired(address: str) -> bool:
    return "Paired: yes" in _bt_cmd("info", address)

def _bt_pair_dbus(address: str) -> bool:
    try:
        import dbus, dbus.mainloop.glib, dbus.service
        from gi.repository import GLib

        OBJ_PATH, AGENT_IF = "/robopong/agent", "org.bluez.Agent1"
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        class Agent(dbus.service.Object):
            @dbus.service.method(AGENT_IF, in_signature="", out_signature="")
            def Release(self): pass
            @dbus.service.method(AGENT_IF, in_signature="os", out_signature="")
            def AuthorizeService(self, device, uuid): pass
            @dbus.service.method(AGENT_IF, in_signature="o", out_signature="s")
            def RequestPinCode(self, device): return "0000"
            @dbus.service.method(AGENT_IF, in_signature="o", out_signature="u")
            def RequestPasskey(self, device): return dbus.UInt32(0)
            @dbus.service.method(AGENT_IF, in_signature="ouq", out_signature="")
            def DisplayPasskey(self, device, passkey, entered): pass
            @dbus.service.method(AGENT_IF, in_signature="ou", out_signature="")
            def RequestConfirmation(self, device, passkey): pass
            @dbus.service.method(AGENT_IF, in_signature="o", out_signature="")
            def RequestAuthorization(self, device): pass
            @dbus.service.method(AGENT_IF, in_signature="", out_signature="")
            def Cancel(self): pass

        agent = Agent(bus, OBJ_PATH)
        mgr = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")
        mgr.RegisterAgent(OBJ_PATH, "NoInputNoOutput")
        mgr.RequestDefaultAgent(OBJ_PATH)

        result = {"ok": False}
        mainloop = GLib.MainLoop()

        def do_pair():
            dev_path = f"/org/bluez/hci0/dev_{address.replace(':', '_')}"
            try:
                props = dbus.Interface(bus.get_object("org.bluez", dev_path), "org.freedesktop.DBus.Properties")
                props.Set("org.bluez.Device1", "Trusted", dbus.Boolean(True))
                dbus.Interface(bus.get_object("org.bluez", dev_path), "org.bluez.Device1").Pair()
                result["ok"] = bool(props.Get("org.bluez.Device1", "Paired"))
            except Exception as e:
                logger.error("Pairing failed: %s", e)
            GLib.idle_add(mainloop.quit)

        threading.Thread(target=do_pair, daemon=True).start()
        mainloop.run()
        try: mgr.UnregisterAgent(OBJ_PATH)
        except Exception: pass
        return result["ok"]
    except Exception as e:
        logger.error("Pairing system error: %s", e)
        return False


# ─── USB transport (FTDI via pyserial) ────────────────────────────────────────

class _USBTransport:
    """Synchronous FTDI USB transport wrapped for async use."""

    FTDI_VID_PID = "0403:6001"

    def __init__(self):
        self._ser = None
        self._lock = threading.Lock()
        self.port: str = ""

    @staticmethod
    def list_ports() -> List[str]:
        try:
            import serial.tools.list_ports
            ports = []
            for p in serial.tools.list_ports.comports():
                vid_pid = f"{p.vid:04x}:{p.pid:04x}" if p.vid else ""
                if "ftdi" in (p.manufacturer or "").lower() or \
                   vid_pid == _USBTransport.FTDI_VID_PID or \
                   "newgy" in (p.description or "").lower() or \
                   "usb serial" in (p.description or "").lower():
                    ports.append(p.device)
            # fallback: ttyUSB* devices
            if not ports:
                ports = sorted(glob.glob("/dev/ttyUSB*"))
            return ports
        except Exception:
            return sorted(glob.glob("/dev/ttyUSB*"))

    def connect(self, port: str) -> bool:
        import serial
        try:
            # Step 1: init handshake at 9600 baud
            s = serial.Serial(
                port=port, baudrate=9600, bytesize=8,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                timeout=1, rtscts=False, dsrdtr=False,
            )
            s.rts = True
            s.dtr = True
            time.sleep(0.1)
            s.write(b"\x5a")  # raw byte wake-up, NOT "Z\r\n"
            time.sleep(0.25)
            s.write(b"\x5a")
            time.sleep(0.25)
            s.close()

            # Step 2: main connection at 115200 baud
            s = serial.Serial(
                port=port, baudrate=115200, bytesize=8,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                timeout=1, rtscts=False, dsrdtr=False,
            )
            s.rts = True
            s.dtr = True
            s.reset_input_buffer()
            s.reset_output_buffer()

            # Wait for Z response (K/N/M), retry up to 5s
            deadline = time.time() + 5.0
            ok = False
            while time.time() < deadline:
                s.write(b"Z\r\n")
                resp = s.read(1).decode("ascii", errors="ignore")
                if resp in ("K", "N", "M"):
                    ok = True
                    break
                time.sleep(0.3)

            if not ok:
                s.close()
                return False

            s.write(b"H\r\n")
            s.read(1)  # consume response

            with self._lock:
                self._ser = s
                self.port = port
            return True
        except Exception as e:
            logger.error("USB connection failed: %s", e)
            return False

    def disconnect(self):
        with self._lock:
            if self._ser:
                try:
                    self._ser.write(b"H\r\n")
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None
            self.port = ""

    def write(self, cmd: str) -> Optional[str]:
        with self._lock:
            if not self._ser:
                return None
            try:
                self._ser.reset_input_buffer()
                self._ser.write((cmd + "\r\n").encode())
                resp = self._ser.read(1).decode("ascii", errors="ignore")
                return resp
            except Exception as e:
                logger.error("USB write failed: %s", e)
                return None

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._ser is not None and self._ser.is_open


# ─── Robot ────────────────────────────────────────────────────────────────────

class Robot:
    def __init__(self, on_event: Optional[Callable] = None):
        # BLE
        self._client:      Optional[BleakClient] = None
        self._drill:       Optional[asyncio.Task] = None
        self._reconnect:   Optional[asyncio.Task] = None
        self.firmware:     int = 0
        self.device:       str = ""
        self._last_addr:   str = ""
        self._auto_reconnect: bool = False
        self._health_task: Optional[asyncio.Task] = None
        self._last_notify: float = 0

        # USB
        self._usb = _USBTransport()

        self._emit = on_event or (lambda *_: None)

    # ── discovery ─────────────────────────────────────────────────────────────

    async def scan(self, timeout: float = 8.0) -> List[Dict]:
        devices = await BleakScanner.discover(timeout=timeout)
        return [
            {"name": d.name or "(brak nazwy)", "address": d.address}
            for d in devices
        ]

    def usb_ports(self) -> List[str]:
        return _USBTransport.list_ports()

    # ── connection ────────────────────────────────────────────────────────────

    async def connect(self, address: str) -> bool:
        self._last_addr = address
        self._auto_reconnect = True
        return await self._do_connect(address)

    async def _do_connect(self, address: str) -> bool:
        if self._client:
            try: await self._client.disconnect()
            except Exception: pass
            self._client = None
        await asyncio.to_thread(_bt_disconnect, address)
        await asyncio.sleep(1)

        if not await asyncio.to_thread(_bt_is_paired, address):
            logger.info("Pairing with %s...", address)
            self._emit("pairing", {"address": address})
            try: await BleakScanner.find_device_by_address(address, timeout=10)
            except Exception: pass
            if not await asyncio.to_thread(_bt_pair_dbus, address):
                self._emit("error", {"message": "Parowanie BLE nie powiodło się"})
                return False
            logger.info("Paired with %s", address)
            await asyncio.to_thread(_bt_disconnect, address)
            await asyncio.sleep(2)

        try:
            dev = await BleakScanner.find_device_by_address(address, timeout=12)
            if not dev:
                self._emit("error", {"message": f"Nie znaleziono {address} w skanie BLE"})
                return False
            self._client = BleakClient(dev, disconnected_callback=self._on_disconnect)
            await self._client.connect(timeout=15.0)
            await self._client.start_notify(MLDP_DATA_CHAR, self._on_notify)
            self.device = address
            self._last_notify = asyncio.get_event_loop().time()
            self._push_status()
            await self._handshake()
            self._start_health_monitor()
            return True
        except (BleakError, Exception) as e:
            logger.error("BLE connection failed: %s", e)
            self._emit("error", {"message": str(e)})
            self._client = None
            return False

    async def connect_usb(self, port: str) -> bool:
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, self._usb.connect, port)
        if ok:
            self.device = f"USB:{port}"
            self._push_status()
            self._emit("usb_connected", {"port": port})
        else:
            self._emit("error", {"message": f"Nie udało się połączyć USB na {port}"})
        return ok

    async def reset_ble(self):
        logger.info("Resetting BLE for %s", self._last_addr)
        self._emit("ble_reset", {"address": self._last_addr})
        addr = self._last_addr
        self._stop_health_monitor()
        if self._client:
            try: await self._client.disconnect()
            except Exception: pass
            self._client = None
        self.firmware = 0
        self.device = ""
        self._push_status()
        await asyncio.to_thread(_bt_disconnect, addr)
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
        # BLE
        if self._client and self._client.is_connected:
            try:
                await self._write("H")
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None
        # USB
        if self._usb.is_connected:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._usb.disconnect)
        self.firmware = 0
        self.device = ""
        self._push_status()

    # ── robot control ─────────────────────────────────────────────────────────

    async def set_ball(
        self,
        top: int, bot: int,
        osc: int, height: int, rotation: int,
        wait_ms: int = 1500,
    ):
        dir_t = 1 if top < 0 else 0
        dir_b = 1 if bot < 0 else 0
        spd_t = min(999, int(abs(top) * 4.016))
        spd_b = min(999, int(abs(bot) * 4.016))
        leds  = self._spin_leds(top, bot)

        if self.firmware >= 701:
            wta = f"wTA{wait_ms // 10:03d}"
            await self._write(wta)
            await asyncio.sleep(0.08)
            cmd = f"A{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"
        else:
            cmd = f"B{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"

        logger.debug("Sending ball: top=%d bot=%d osc=%d height=%d rot=%d leds=%d", top, bot, osc, height, rotation, leds)
        await self._write(cmd)

    async def throw(self):
        logger.debug("Sending throw command")
        await self._write("T")

    async def stop(self):
        logger.debug("Sending stop command")
        self._stop_drill_nowait()
        await self._write("H")

    # ── drill runner ──────────────────────────────────────────────────────────

    async def run_drill(self, balls: List[Dict], repeat: int = 1,
                        count: int = 0, percent: int = 100):
        if self._drill and not self._drill.done():
            self._drill.cancel()

        min_wait_ms = 500 if len(balls) == 1 else 750

        async def _loop():
            # SetupDrill — rozgrzewka jak w oryginale
            await self._write("H")
            await asyncio.sleep(0.2)
            await self._write("H")
            await asyncio.sleep(1.0)
            b0 = balls[0]
            await self.set_ball(b0["top_speed"], b0["bot_speed"],
                               b0["oscillation"], b0["height"], b0["rotation"],
                               b0.get("wait_ms", 1000))
            await asyncio.sleep(0.3)
            await self.set_ball(b0["top_speed"], b0["bot_speed"],
                               b0["oscillation"], b0["height"], b0["rotation"],
                               b0.get("wait_ms", 1000))
            logger.info("SetupDrill: warmup 1.5s")
            await asyncio.sleep(1.5)

            run = 0
            thrown = 0
            try:
                while repeat == 0 or run < repeat:
                    for i, b in enumerate(balls):
                        if count > 0 and thrown >= count:
                            return
                        # Newgy formula: wait * (100 + (100 - percent)) / 100
                        raw_wait = b.get("wait_ms", 1500)
                        adj_wait = max(min_wait_ms, int(raw_wait * (100 + (100 - percent)) / 100))
                        await self.set_ball(
                            b["top_speed"], b["bot_speed"],
                            b["oscillation"], b["height"],
                            b["rotation"], adj_wait,
                        )
                        await asyncio.sleep(0.15)
                        await self.throw()
                        thrown += 1
                        self._emit("drill_progress", {
                            "ball":       i + 1,
                            "total":      len(balls),
                            "run":        run + 1,
                            "max_repeat": repeat,
                            "thrown":     thrown,
                            "count":      count,
                            "percent":    percent,
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
                if not self.is_connected or self._usb.is_connected:
                    break
                await self._write("Z")
                await asyncio.sleep(3)
                if asyncio.get_event_loop().time() - self._last_notify > 30:
                    logger.warning("No response for 30s — resetting BLE")
                    await self.reset_ble()
                    break
        except asyncio.CancelledError:
            pass

    # ── internal ──────────────────────────────────────────────────────────────

    async def _handshake(self):
        # 1. Wake up — Z×3 + H (jak Android/iOS connectService)
        for _ in range(3):
            await self._write("Z")
            await asyncio.sleep(0.12)
        await self._write("H")
        await asyncio.sleep(0.4)
        # 2. InitializeRobot — F, I, ClearBall (H + W000)
        await self._write("F")         # GetFirmwareVersion
        await asyncio.sleep(0.5)
        await self._write("I")         # getRobotVersion (query)
        await asyncio.sleep(0.3)
        await self._write("J02")       # SetVersion Gen2
        await asyncio.sleep(0.2)
        await self._write("H")         # ClearBall
        await asyncio.sleep(0.1)
        await self._write("W000")      # SetAdjustment(0)
        await asyncio.sleep(0.2)
        logger.info("handshake complete")

    async def _write(self, cmd: str):
        # USB takes priority if connected
        if self._usb.is_connected:
            logger.debug("USB send: %s", cmd)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._usb.write, cmd)
            return
        # BLE fallback
        if not self._client or not self._client.is_connected:
            logger.warning("Cannot send '%s' — not connected", cmd)
            return
        data = (cmd if cmd.endswith("\r") else cmd + "\r").encode()
        logger.debug("BLE send: %s (%d bytes)", cmd, len(data))
        try:
            if len(data) <= 20:
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data, response=False)
            else:
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data[:20], response=False)
                await asyncio.sleep(0.2)
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data[20:], response=False)
                logger.debug("BLE send continued (%d bytes)", len(data) - 20)
        except BleakError as e:
            logger.error("BLE write failed: %s", e)

    def _on_notify(self, _sender, data: bytearray):
        text = data.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        self._last_notify = asyncio.get_event_loop().time()
        self._emit("robot_response", {"data": text})
        try:
            v = int(text)
            if 100 <= v <= 9999:
                self.firmware = v
                self._push_status()
        except ValueError:
            pass

    def _on_disconnect(self, _client):
        self._client = None
        self.firmware = 0
        self.device = ""
        self._stop_health_monitor()
        self._push_status()
        if self._auto_reconnect and self._last_addr:
            logger.info("BLE disconnected — reconnecting to %s", self._last_addr)
            self._reconnect = asyncio.create_task(self._reconnect_loop())

    def _push_status(self):
        self._emit("status", {
            "connected": self.is_connected,
            "firmware":  self.firmware,
            "device":    self.device,
            "transport": "usb" if self._usb.is_connected else "ble",
        })

    async def _reconnect_loop(self):
        delays = [2, 3, 5, 10, 15, 30, 30, 60]
        for delay in delays:
            await asyncio.sleep(delay)
            if not self._auto_reconnect:
                return
            if self.is_connected:
                return
            logger.info("Reconnecting to %s (attempt in %ds)", self._last_addr, delay)
            self._emit("reconnecting", {"address": self._last_addr})
            await asyncio.to_thread(_bt_disconnect, self._last_addr)
            await asyncio.sleep(1)
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
        """LEDS enum: None=0, 1-4=Bottom, 5-8=Top (oryginał: ratio=|diff|/360)"""
        diff = top - bot
        if diff == 0:
            return 0
        ratio = abs(diff) / 360.0
        if ratio <= 0.10:
            level = 1
        elif ratio <= 0.50:
            level = 2
        elif ratio <= 0.75:
            level = 3
        else:
            level = 4
        return level + 4 if diff > 0 else level  # top: 5-8, bottom: 1-4

    @property
    def is_connected(self) -> bool:
        if self._usb.is_connected:
            return True
        return self._client is not None and self._client.is_connected
