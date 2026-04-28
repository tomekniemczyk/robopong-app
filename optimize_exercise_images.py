#!/usr/bin/env python3
"""Resize and compress exercise PNGs to save space (target: 300x300 JPEG ~30KB each)."""

import os, subprocess, sys
from pathlib import Path

FRAMES_DIR = Path("/home/niemczyt/src/robopong-app/robopong-app-ex-rework/frontend/static/exercises/frames")

def optimize():
    pngs = sorted(FRAMES_DIR.glob("*.png"))
    if not pngs:
        print("No PNG files found")
        return

    # Check if convert (ImageMagick) or ffmpeg is available
    has_magick = subprocess.run(["which", "convert"], capture_output=True).returncode == 0
    has_python_pil = False
    try:
        from PIL import Image
        has_python_pil = True
    except ImportError:
        pass

    if not has_magick and not has_python_pil:
        print("Neither ImageMagick nor Pillow available, trying pip install...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
        try:
            from PIL import Image
            has_python_pil = True
        except ImportError:
            print("ERROR: Cannot install Pillow, skipping optimization")
            return

    total_before = sum(f.stat().st_size for f in pngs)
    count = 0

    for png_path in pngs:
        jpg_path = png_path.with_suffix('.jpg')
        if jpg_path.exists():
            # Already optimized
            continue

        if has_python_pil:
            from PIL import Image
            img = Image.open(png_path)
            # Resize to 400x400
            img = img.resize((400, 400), Image.LANCZOS)
            # Convert to RGB (remove alpha if any)
            if img.mode != 'RGB':
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    bg.paste(img, mask=img.split()[3])
                else:
                    bg.paste(img)
                img = bg
            img.save(jpg_path, 'JPEG', quality=82, optimize=True)
        elif has_magick:
            subprocess.run([
                "convert", str(png_path),
                "-resize", "400x400",
                "-quality", "82",
                str(jpg_path)
            ], capture_output=True)

        if jpg_path.exists():
            count += 1
            before = png_path.stat().st_size
            after = jpg_path.stat().st_size
            print(f"  {png_path.name} → {jpg_path.name}: {before//1024}KB → {after//1024}KB")

    print(f"\nOptimized {count} images")
    jpgs = sorted(FRAMES_DIR.glob("*.jpg"))
    total_after = sum(f.stat().st_size for f in jpgs)
    print(f"Total: {total_before//1024//1024}MB → {total_after//1024//1024}MB")


if __name__ == "__main__":
    optimize()
