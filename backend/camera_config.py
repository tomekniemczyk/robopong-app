"""Konfiguracja kamery (urządzenie, rozdzielczość, FPS) + sterowanie ustreamer.

Config jest trzymany w pliku JSON obok kodu; systemd unit czyta z
ustreamer.env (generowany z tego config), zmiana wymaga restartu ustreamera.
"""

import json
import re
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
CONFIG_FILE = BACKEND_DIR / "camera_config.json"
ENV_FILE = BACKEND_DIR / "ustreamer.env"

DEFAULT_CONFIG = {
    "device": "/dev/v4l/by-id/usb-EMEET_EMEET_SmartCam_C960_2K_A251206000301243-video-index0",
    "resolution": "640x360",
    "fps": 60,
}


# ── Config persistence ──────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        return {**DEFAULT_CONFIG, **cfg}
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    ENV_FILE.write_text(
        f'CAMERA_DEVICE={cfg["device"]}\n'
        f'CAMERA_RES={cfg["resolution"]}\n'
        f'CAMERA_FPS={cfg["fps"]}\n'
    )


# ── Device + format enumeration (v4l2-ctl) ──────────────────────────────────

def list_devices() -> list[dict]:
    """Lista kamer w systemie (tylko video-capture, bez touch/meta)."""
    try:
        out = subprocess.run(
            ["v4l2-ctl", "--list-devices"], capture_output=True, text=True, timeout=3
        ).stdout
    except Exception:
        return []
    devices = []
    current_name = None
    current_paths = []
    for line in out.splitlines():
        if line and not line.startswith("\t"):
            if current_name and current_paths:
                devices.append({"name": current_name, "paths": current_paths})
            current_name = line.rstrip(":").strip()
            current_paths = []
        elif line.startswith("\t"):
            p = line.strip()
            if p.startswith("/dev/video"):
                current_paths.append(p)
    if current_name and current_paths:
        devices.append({"name": current_name, "paths": current_paths})

    result = []
    for d in devices:
        if "touch" in d["name"].lower():
            continue
        capture_path = _first_capture_device(d["paths"])
        if not capture_path:
            continue
        stable = _to_stable_path(capture_path)
        result.append({"name": d["name"], "device": stable, "dev": capture_path})
    return result


def _first_capture_device(paths: list[str]) -> str | None:
    """Z kilku /dev/videoN w jednym urządzeniu wybierz ten który obsługuje Video Capture."""
    for p in paths:
        try:
            out = subprocess.run(
                ["v4l2-ctl", "-d", p, "--list-formats"],
                capture_output=True, text=True, timeout=2
            ).stdout
            if "Video Capture" in out or "MJPG" in out or "YUYV" in out:
                return p
        except Exception:
            continue
    return paths[0] if paths else None


def _to_stable_path(dev_path: str) -> str:
    """Zwróć /dev/v4l/by-id/... jeśli istnieje (stabilne po reboot), wpp dev_path."""
    by_id_dir = Path("/dev/v4l/by-id")
    if not by_id_dir.exists():
        return dev_path
    try:
        target = Path(dev_path).resolve()
        for link in by_id_dir.iterdir():
            if link.resolve() == target:
                return str(link)
    except Exception:
        pass
    return dev_path


def list_formats(device: str) -> list[dict]:
    """Lista MJPEG rozdzielczości + dostępnych FPS dla urządzenia."""
    try:
        out = subprocess.run(
            ["v4l2-ctl", "-d", device, "--list-formats-ext"],
            capture_output=True, text=True, timeout=3
        ).stdout
    except Exception:
        return []
    formats = []
    current_fmt = None
    current_size = None
    for line in out.splitlines():
        s = line.strip()
        m_fmt = re.search(r"'(\w+)'", s)
        if s.startswith("[") and m_fmt:
            current_fmt = m_fmt.group(1)
            continue
        m_size = re.match(r"Size:\s+\w+\s+(\d+)x(\d+)", s)
        if m_size and current_fmt == "MJPG":
            current_size = f"{m_size.group(1)}x{m_size.group(2)}"
            formats.append({"resolution": current_size, "fps_options": []})
            continue
        m_fps = re.search(r"\(([\d.]+)\s*fps\)", s)
        if m_fps and current_fmt == "MJPG" and formats:
            fps = round(float(m_fps.group(1)))
            if fps not in formats[-1]["fps_options"]:
                formats[-1]["fps_options"].append(fps)
    return [f for f in formats if f["fps_options"]]


# ── Restart ustreamer ──────────────────────────────────────────────────────

def restart_ustreamer() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["sudo", "-n", "/bin/systemctl", "restart", "ustreamer"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return True, ""
        return False, (r.stderr or r.stdout or "unknown error").strip()
    except Exception as e:
        return False, str(e)
