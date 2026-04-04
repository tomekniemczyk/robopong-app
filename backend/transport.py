import asyncio
import glob
import logging
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

logger = logging.getLogger(__name__)

MLDP_SERVICE   = "00035b03-58e6-07dd-021a-08123a000300"
MLDP_DATA_CHAR = "00035b03-58e6-07dd-021a-08123a000301"
MLDP_CTRL_CHAR = "00035b03-58e6-07dd-021a-08123a0003ff"


# ─── ABC ──────────────────────────────────────────────────────────────────────

class RobotTransport(ABC):
    @abstractmethod
    async def connect(self, target: str) -> bool: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def write(self, cmd: str) -> Optional[str]: ...

    def set_on_data(self, callback: Callable[[str], None]) -> None:
        pass  # default no-op, BLE overrides

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        pass  # default no-op, BLE overrides

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    @property
    @abstractmethod
    def transport_type(self) -> str: ...


# ─── BLE system helpers ──────────────────────────────────────────────────────

class BLETransport(RobotTransport):

    @staticmethod
    def _bt_cmd(*args, timeout=5) -> str:
        try:
            r = subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout)
            return r.stdout + r.stderr
        except Exception as e:
            logger.warning("Bluetooth command failed: %s", e)
            return ""

    @staticmethod
    def _bt_disconnect(address: str):
        BLETransport._bt_cmd("disconnect", address)

    @staticmethod
    def _bt_is_paired(address: str) -> bool:
        return "Paired: yes" in BLETransport._bt_cmd("info", address)

    _dbus_agent = None
    _dbus_bus = None

    @staticmethod
    def _bt_pair_dbus(address: str) -> bool:
        try:
            import dbus, dbus.mainloop.glib, dbus.service
            from gi.repository import GLib

            OBJ_PATH, AGENT_IF = "/robopong/agent", "org.bluez.Agent1"
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            bus = dbus.SystemBus()

            if BLETransport._dbus_agent is None:
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

                BLETransport._dbus_agent = Agent(bus, OBJ_PATH)
                BLETransport._dbus_bus = bus

            mgr = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.AgentManager1")
            try:
                mgr.RegisterAgent(OBJ_PATH, "NoInputNoOutput")
                mgr.RequestDefaultAgent(OBJ_PATH)
            except dbus.exceptions.DBusException as e:
                if "AlreadyExists" not in str(e):
                    raise

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
            return result["ok"]
        except Exception as e:
            logger.error("Pairing system error: %s", e)
            return False

    def __init__(self):
        self._client: Optional[BleakClient] = None
        self._on_data: Optional[Callable[[str], None]] = None
        self._on_disconnect_cb: Optional[Callable[[], None]] = None
        self.last_notify: float = 0

    async def connect(self, address: str) -> bool:
        if self._client:
            try: await self._client.disconnect()
            except Exception: pass
            self._client = None
        await asyncio.to_thread(self._bt_disconnect, address)
        await asyncio.sleep(1)

        if not await asyncio.to_thread(self._bt_is_paired, address):
            logger.info("Pairing with %s...", address)
            try: await BleakScanner.find_device_by_address(address, timeout=10)
            except Exception: pass
            if not await asyncio.to_thread(self._bt_pair_dbus, address):
                return False
            logger.info("Paired with %s", address)
            await asyncio.to_thread(self._bt_disconnect, address)
            await asyncio.sleep(2)

        try:
            dev = await BleakScanner.find_device_by_address(address, timeout=12)
            if not dev:
                return False
            self._client = BleakClient(dev, disconnected_callback=self._on_disconnect_raw)
            await self._client.connect(timeout=15.0)
            if not self._client or not self._client.is_connected:
                return False
            await self._client.start_notify(MLDP_DATA_CHAR, self._on_notify_raw)
            self.last_notify = asyncio.get_event_loop().time()
            return True
        except (BleakError, Exception) as e:
            logger.error("BLE connection failed: %s", e)
            self._client = None
            return False

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None

    async def write(self, cmd: str) -> Optional[str]:
        if not self._client or not self._client.is_connected:
            logger.warning("Cannot send '%s' — not connected", cmd)
            return None
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
        return None

    def set_on_data(self, callback: Callable[[str], None]) -> None:
        self._on_data = callback

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        self._on_disconnect_cb = callback

    def _on_notify_raw(self, _sender, data: bytearray):
        text = data.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        self.last_notify = asyncio.get_event_loop().time()
        if self._on_data:
            self._on_data(text)

    def _on_disconnect_raw(self, _client):
        self._client = None
        if self._on_disconnect_cb:
            self._on_disconnect_cb()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def transport_type(self) -> str:
        return "ble"


# ─── USB transport (FTDI via pyserial) ───────────────────────────────────────

class USBTransport(RobotTransport):

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
                   vid_pid == USBTransport.FTDI_VID_PID or \
                   "newgy" in (p.description or "").lower() or \
                   "usb serial" in (p.description or "").lower():
                    ports.append(p.device)
            if not ports:
                ports = sorted(glob.glob("/dev/ttyUSB*"))
            return ports
        except Exception:
            return sorted(glob.glob("/dev/ttyUSB*"))

    def _sync_connect(self, port: str) -> bool:
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

    async def connect(self, port: str) -> bool:
        return await asyncio.to_thread(self._sync_connect, port)

    def _sync_disconnect(self):
        with self._lock:
            if self._ser:
                try:
                    self._ser.write(b"H\r\n")
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None
            self.port = ""

    async def disconnect(self) -> None:
        await asyncio.to_thread(self._sync_disconnect)

    def _sync_write(self, cmd: str) -> Optional[str]:
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

    async def write(self, cmd: str) -> Optional[str]:
        logger.debug("USB send: %s", cmd)
        return await asyncio.to_thread(self._sync_write, cmd)

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._ser is not None and self._ser.is_open

    @property
    def transport_type(self) -> str:
        return "usb"


# ─── Simulation ──────────────────────────────────────────────────────────────

class SimulationTransport(RobotTransport):

    async def connect(self, target: str) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def write(self, cmd: str) -> Optional[str]:
        logger.debug("SIM → %s", cmd)
        return None

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def transport_type(self) -> str:
        return "simulation"
