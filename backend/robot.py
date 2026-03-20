import asyncio
import logging
from typing import Callable, Dict, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

logger = logging.getLogger(__name__)

MLDP_SERVICE   = "00035b03-58e6-07dd-021a-08123a000300"
MLDP_DATA_CHAR = "00035b03-58e6-07dd-021a-08123a000301"
MLDP_CTRL_CHAR = "00035b03-58e6-07dd-021a-08123a0003ff"


class Robot:
    def __init__(self, on_event: Optional[Callable] = None):
        self._client:      Optional[BleakClient] = None
        self._drill:       Optional[asyncio.Task] = None
        self._reconnect:   Optional[asyncio.Task] = None
        self.firmware:     int = 0
        self.device:       str = ""
        self._last_addr:   str = ""   # zapamiętany adres do auto-reconnect
        self._auto_reconnect: bool = False
        self._emit = on_event or (lambda *_: None)

    # ── discovery ─────────────────────────────────────────────────────────────

    async def scan(self, timeout: float = 8.0) -> List[Dict]:
        devices = await BleakScanner.discover(timeout=timeout)
        return [
            {"name": d.name or "(brak nazwy)", "address": d.address}
            for d in devices
        ]

    # ── connection ────────────────────────────────────────────────────────────

    async def connect(self, address: str) -> bool:
        self._last_addr = address
        self._auto_reconnect = True
        return await self._do_connect(address)

    async def _do_connect(self, address: str) -> bool:
        try:
            self._client = BleakClient(
                address,
                disconnected_callback=self._on_disconnect,
            )
            await self._client.connect(timeout=15.0)
            await self._client.start_notify(MLDP_DATA_CHAR, self._on_notify)
            self.device = address
            self._push_status()
            await self._handshake()
            return True
        except (BleakError, Exception) as e:
            logger.error("connect: %s", e)
            self._emit("error", {"message": str(e)})
            self._client = None
            return False

    async def disconnect(self):
        self._auto_reconnect = False
        self._stop_drill_nowait()
        if self._reconnect and not self._reconnect.done():
            self._reconnect.cancel()
        if self._client and self._client.is_connected:
            try:
                await self._write("H")
                await self._client.disconnect()
            except Exception:
                pass
        self._client = None
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
            await self._write(f"wTA{wait_ms // 10:03d}")
            await asyncio.sleep(0.08)
            cmd = f"A{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"
        else:
            cmd = f"B{dir_t}{spd_t:03d}{dir_b}{spd_b:03d}{osc:03d}{height:03d}{rotation:03d}{leds}"

        await self._write(cmd)

    async def throw(self):
        await self._write("T")

    async def stop(self):
        self._stop_drill_nowait()
        await self._write("H")

    # ── drill runner ──────────────────────────────────────────────────────────

    async def run_drill(self, balls: List[Dict], repeat: int = 1):
        if self._drill and not self._drill.done():
            self._drill.cancel()

        async def _loop():
            run = 0
            try:
                while repeat == 0 or run < repeat:
                    for i, b in enumerate(balls):
                        await self.set_ball(
                            b["top_speed"], b["bot_speed"],
                            b["oscillation"], b["height"],
                            b["rotation"], b.get("wait_ms", 1500),
                        )
                        await asyncio.sleep(0.15)
                        await self.throw()
                        self._emit("drill_progress", {
                            "ball":       i + 1,
                            "total":      len(balls),
                            "run":        run + 1,
                            "max_repeat": repeat,
                        })
                        await asyncio.sleep(max(0.3, b.get("wait_ms", 1500) / 1000 - 0.15))
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

    # ── internal ──────────────────────────────────────────────────────────────

    async def _handshake(self):
        for _ in range(3):
            await self._write("Z")
            await asyncio.sleep(0.12)
        await self._write("H")
        await asyncio.sleep(0.4)
        await self._write("F")   # firmware version query
        await asyncio.sleep(0.5)

    async def _write(self, cmd: str):
        if not self.is_connected:
            return
        data = (cmd if cmd.endswith("\r") else cmd + "\r").encode()
        try:
            if len(data) <= 20:
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data, response=False)
            else:
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data[:20], response=False)
                await asyncio.sleep(0.2)
                await self._client.write_gatt_char(MLDP_DATA_CHAR, data[20:], response=False)
        except BleakError as e:
            logger.error("write: %s", e)

    def _on_notify(self, _sender, data: bytearray):
        text = data.decode("utf-8", errors="ignore").strip()
        if not text:
            return
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
        self._push_status()
        if self._auto_reconnect and self._last_addr:
            logger.info("rozłączono — próba ponownego połączenia z %s", self._last_addr)
            self._reconnect = asyncio.create_task(self._reconnect_loop())

    def _push_status(self):
        self._emit("status", {
            "connected": self.is_connected,
            "firmware":  self.firmware,
            "device":    self.device,
        })

    async def _reconnect_loop(self):
        delays = [5, 10, 15, 30, 30, 60]
        for delay in delays:
            await asyncio.sleep(delay)
            if not self._auto_reconnect:
                return
            if self.is_connected:
                return
            logger.info("auto-reconnect → %s", self._last_addr)
            self._emit("reconnecting", {"address": self._last_addr})
            ok = await self._do_connect(self._last_addr)
            if ok:
                logger.info("auto-reconnect OK")
                return
        logger.warning("auto-reconnect wyczerpał próby")
        self._emit("error", {"message": "Nie udało się ponownie połączyć z robotem"})

    def _stop_drill_nowait(self):
        if self._drill and not self._drill.done():
            self._drill.cancel()

    @staticmethod
    def _spin_leds(top: int, bot: int) -> int:
        diff = abs(top) - abs(bot)
        for val, leds in ((60, 9), (40, 7), (20, 5), (10, 3), (1, 1)):
            if abs(diff) >= val:
                return leds
        return 0

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected
