"""Tests for transport.py — SimulationTransport, ABC, USBTransport.list_ports."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from transport import RobotTransport, SimulationTransport, USBTransport


# ── SimulationTransport ──────────────────────────────────────────────────────

def test_simulation_connect():
    t = SimulationTransport()
    result = asyncio.run(t.connect("any"))
    assert result is True


def test_simulation_disconnect():
    async def _run():
        t = SimulationTransport()
        await t.connect("x")
        await t.disconnect()
    asyncio.run(_run())  # should not raise


def test_simulation_write():
    t = SimulationTransport()
    result = asyncio.run(t.write("B00100010015012815000"))
    assert result is None  # simulation always returns None


def test_simulation_is_connected():
    t = SimulationTransport()
    assert t.is_connected is True


def test_simulation_transport_type():
    t = SimulationTransport()
    assert t.transport_type == "simulation"


# ── RobotTransport ABC ──────────────────────────────────────────────────────

def test_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        RobotTransport()


# ── USBTransport.list_ports ──────────────────────────────────────────────────

def test_usb_list_ports_with_ftdi():
    mock_port = MagicMock()
    mock_port.vid = 0x0403
    mock_port.pid = 0x6001
    mock_port.manufacturer = "FTDI"
    mock_port.description = "USB Serial"
    mock_port.device = "/dev/ttyUSB0"

    with patch("serial.tools.list_ports.comports", return_value=[mock_port]):
        ports = USBTransport.list_ports()
        assert "/dev/ttyUSB0" in ports


def test_usb_list_ports_empty():
    with patch("serial.tools.list_ports.comports", return_value=[]), \
         patch("glob.glob", return_value=[]):
        ports = USBTransport.list_ports()
        assert ports == []


def test_usb_list_ports_fallback_glob():
    mock_port = MagicMock()
    mock_port.vid = None
    mock_port.pid = None
    mock_port.manufacturer = "Other"
    mock_port.description = "Something else"
    mock_port.device = "/dev/ttyACM0"

    with patch("serial.tools.list_ports.comports", return_value=[mock_port]), \
         patch("glob.glob", return_value=["/dev/ttyUSB0", "/dev/ttyUSB1"]):
        ports = USBTransport.list_ports()
        assert ports == ["/dev/ttyUSB0", "/dev/ttyUSB1"]


def test_usb_transport_type():
    t = USBTransport()
    assert t.transport_type == "usb"


def test_usb_not_connected_by_default():
    t = USBTransport()
    assert t.is_connected is False
