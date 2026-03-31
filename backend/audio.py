"""Server-side audio playback via aplay + amixer volume control."""

import subprocess
from pathlib import Path

SOUNDS = Path(__file__).parent / "sounds"


def play(name: str):
    path = SOUNDS / f"{name}.wav"
    if path.exists():
        subprocess.Popen(["aplay", "-q", str(path)])


def get_volume() -> int:
    """Return current ALSA master volume (0-100)."""
    try:
        out = subprocess.check_output(
            ["amixer", "get", "Master"], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "[" in line and "%" in line:
                pct = line.split("[")[1].split("%")[0]
                return int(pct)
    except Exception:
        pass
    return 50


def set_volume(pct: int) -> int:
    """Set ALSA master volume (0-100). Returns actual level."""
    pct = max(0, min(100, pct))
    try:
        subprocess.run(
            ["amixer", "set", "Master", f"{pct}%"],
            check=True, capture_output=True,
        )
    except Exception:
        pass
    return get_volume()
