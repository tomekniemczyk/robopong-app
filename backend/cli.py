#!/usr/bin/env python3
"""CLI do sterowania Robopong 3050XL przez BLE."""
import asyncio
import random
import readline
import sys

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

MLDP_DATA = "00035b03-58e6-07dd-021a-08123a000301"
DEFAULTS = dict(top=75, bot=75, osc=150, height=170, rot=150, wait=1500)


class RoboCLI:
    def __init__(self):
        self.client = None
        self.addr = ""
        self.firmware = 0
        self.params = dict(DEFAULTS)

    def on_notify(self, _sender, data: bytearray):
        text = data.decode("utf-8", errors="ignore").strip()
        if not text:
            return
        print(f"  << {text}")
        try:
            v = int(text)
            if 100 <= v <= 9999:
                self.firmware = v
        except ValueError:
            pass

    async def write(self, cmd: str):
        if not self.client or not self.client.is_connected:
            print("  ! nie połączono")
            return
        data = (cmd + "\r").encode()
        try:
            if len(data) <= 20:
                await self.client.write_gatt_char(MLDP_DATA, data, response=False)
            else:
                await self.client.write_gatt_char(MLDP_DATA, data[:20], response=False)
                await asyncio.sleep(0.2)
                await self.client.write_gatt_char(MLDP_DATA, data[20:], response=False)
        except BleakError as e:
            print(f"  ! write error: {e}")

    async def cmd_scan(self, _args):
        """Skanuj urządzenia BLE"""
        print("Skanowanie (8s)...")
        devices = await BleakScanner.discover(timeout=8)
        for d in devices:
            name = d.name or ""
            marker = "**" if "NWGY" in name.upper() or "NEWGY" in name.upper() else "  "
            print(f"  {marker} {d.address}  {name or '(brak nazwy)'}")
            if marker == "**":
                self.addr = d.address

    async def cmd_connect(self, args):
        """Połącz z robotem. Użycie: connect [adres]"""
        addr = args or self.addr
        if not addr:
            print("  Podaj adres lub najpierw 'scan'")
            return
        self.addr = addr
        import subprocess
        subprocess.run(["bluetoothctl", "disconnect", addr], capture_output=True, timeout=5)
        await asyncio.sleep(1)
        dev = await BleakScanner.find_device_by_address(addr, timeout=12)
        if not dev:
            print("  ! nie znaleziono")
            return
        self.client = BleakClient(dev)
        await self.client.connect(timeout=15)
        await self.client.start_notify(MLDP_DATA, self.on_notify)
        print(f"Połączono z {dev.name}")
        for _ in range(3):
            await self.write("Z")
            await asyncio.sleep(0.1)
        await self.write("H")
        await asyncio.sleep(1)
        await self.write("F")
        await asyncio.sleep(1)
        await self.write("J02")
        await asyncio.sleep(0.3)
        print(f"Firmware: {self.firmware or '(brak)'}")

    async def cmd_disconnect(self, _):
        """Rozłącz"""
        if self.client and self.client.is_connected:
            await self.write("H")
            await self.client.disconnect()
        self.client = None
        self.firmware = 0
        print("Rozłączono")

    async def cmd_set(self, args):
        """Ustaw parametry: set top=80 height=180"""
        if not args:
            self._pp()
            return
        for part in args.split():
            if "=" in part:
                k, v = part.split("=", 1)
                try: self.params[k.strip()] = int(v)
                except ValueError: print(f"  ! {part}")
        self._pp()

    async def cmd_send(self, _):
        """Wyślij parametry do robota"""
        p = self.params
        dt = 1 if p["top"] < 0 else 0
        db = 1 if p["bot"] < 0 else 0
        st = min(843, round(abs(p["top"]) * 4.016))
        sb = min(843, round(abs(p["bot"]) * 4.016))
        if self.firmware >= 701:
            await self.write(f"wTA{p['wait']//10:03d}")
            await asyncio.sleep(0.5)
            await self.write(f"A{dt}{st:03d}{db}{sb:03d}{p['osc']:03d}{p['height']:03d}{p['rot']:03d}0")
        else:
            await self.write(f"B{dt}{st:03d}{db}{sb:03d}{p['osc']:03d}{p['height']:03d}{p['rot']:03d}0")

    async def cmd_throw(self, args):
        """Wyrzuć piłkę: throw [n]"""
        n = int(args) if args else 1
        await self.cmd_send(None)
        await asyncio.sleep(0.5)
        await self.write(f"END{n:03d}{random.randint(1,255):03d}000")
        print(f"  Wyrzucam {n} piłek...")
        await asyncio.sleep(2 + n * 1.5)

    async def cmd_quick(self, args):
        """Szybki wyrzut: quick top bot osc height rot"""
        parts = (args or "").split()
        if len(parts) >= 5:
            for k, v in zip(["top","bot","osc","height","rot"], parts):
                self.params[k] = int(v)
        await self.cmd_throw("1")

    async def cmd_stop(self, _):
        """Zatrzymaj"""
        await self.write("H")

    async def cmd_ping(self, _):
        """Ping (Z)"""
        await self.write("Z")

    async def cmd_fw(self, _):
        """Firmware"""
        await self.write("F")
        await asyncio.sleep(1)
        print(f"  Firmware: {self.firmware}")

    async def cmd_raw(self, args):
        """Surowa komenda: raw Z"""
        if args: await self.write(args)

    async def cmd_reset(self, _):
        """Reset domyślnych parametrów"""
        self.params = dict(DEFAULTS)
        self._pp()

    async def cmd_status(self, _):
        """Status"""
        c = self.client and self.client.is_connected
        print(f"  Połączony: {'tak' if c else 'nie'}, Adres: {self.addr or '-'}, FW: {self.firmware or '-'}")
        self._pp()

    async def cmd_help(self, _):
        """Pomoc"""
        print("\nKomendy:")
        for n in sorted(self.commands):
            print(f"  {n:12s} {self.commands[n].__doc__ or ''}")
        print(f"  q/exit       Wyjście\n")

    def _pp(self):
        p = self.params
        print(f"  top={p['top']} bot={p['bot']} osc={p['osc']} h={p['height']} rot={p['rot']} wait={p['wait']}ms")

    @property
    def commands(self):
        return {k[4:]: getattr(self, k) for k in dir(self) if k.startswith("cmd_")}

    async def run(self):
        print("RoboPong 3050XL CLI — wpisz 'help'")
        while True:
            try:
                c = self.client and self.client.is_connected
                line = await asyncio.to_thread(input, f"robopong {'●' if c else '○'}> ")
            except (EOFError, KeyboardInterrupt):
                break
            line = line.strip()
            if not line: continue
            if line in ("q", "exit", "quit"): break
            parts = line.split(None, 1)
            handler = self.commands.get(parts[0].lower())
            if handler:
                try: await handler(parts[1] if len(parts) > 1 else "")
                except Exception as e: print(f"  ! {e}")
            else:
                print(f"  ! nieznana: {parts[0]}")
        if self.client and self.client.is_connected:
            await self.write("H")
            await self.client.disconnect()

if __name__ == "__main__":
    try: asyncio.run(RoboCLI().run())
    except KeyboardInterrupt: print()
