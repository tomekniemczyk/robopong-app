"""Server-side audio playback via aplay."""

import subprocess
from pathlib import Path

SOUNDS = Path(__file__).parent / "sounds"


def play(name: str):
    path = SOUNDS / f"{name}.wav"
    if path.exists():
        subprocess.Popen(["aplay", "-q", str(path)])
