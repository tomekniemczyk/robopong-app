#!/usr/bin/env python3
"""Convert drills_xml_v1.txt to drills_default.json with robot raw values."""

import xml.etree.ElementTree as ET
import json
import re

# Conversion formulas (from CLAUDE.md / protocol RE):
# Oscillation: % 0-100  -> raw 127-173 (center=150 at 50%)
# Height:      % 0-100  -> raw 75-210
# Rotation:    deg -90..+90 -> raw 90-210 (center=150 at 0)
# Motor:       % -100..+100 -> app -249..+249

def osc_to_raw(pct): return round(127 + (pct / 100) * 46)
def height_to_raw(pct): return round(75 + (pct / 100) * 135)
def rot_to_raw(deg): return round(150 + (deg / 90) * 60)
def motor_to_app(pct): return round(pct * 2.49)


def parse_ball(ball_el):
    btype = ball_el.get("Type", "AdvancedInterfaceBall")

    def gf(tag, default=0):
        el = ball_el.find(tag)
        return float(el.text) if el is not None and el.text else default

    def gi(tag, default=0):
        el = ball_el.find(tag)
        return int(float(el.text)) if el is not None and el.text else default

    wait_ms = gi("WaitTime", 1000)

    if btype == "AdvancedInterfaceBall":
        top = motor_to_app(gf("TopMotorSpeed"))
        bot = motor_to_app(gf("BottomMotorSpeed"))
        osc = osc_to_raw(gf("Oscillation"))
        h   = height_to_raw(gf("Height"))
        rot = rot_to_raw(gf("Rotation"))
    else:  # RandomInterfaceBall — use midpoint
        tl, th = gf("TopMotorLow"), gf("TopMotorHigh")
        bl, bh = gf("BottomMotorLow"), gf("BottomMotorHigh")
        ol, oh = gf("OscillationLow"), gf("OscillationHigh")
        hl, hh = gf("HeightLow"), gf("HeightHigh")
        rl, rh = gf("RotationLow"), gf("RotationHigh")

        top = motor_to_app((tl + th) / 2)
        bot = motor_to_app((bl + bh) / 2)
        osc = osc_to_raw((ol + oh) / 2)
        h   = height_to_raw((hl + hh) / 2)
        rot = rot_to_raw((rl + rh) / 2)

    # clamp
    top = max(-249, min(249, top))
    bot = max(-249, min(249, bot))
    osc = max(0, min(255, osc))
    h   = max(0, min(255, h))
    rot = max(0, min(255, rot))
    wait_ms = max(200, min(10000, wait_ms))

    return {"top_speed": top, "bot_speed": bot, "oscillation": osc,
            "height": h, "rotation": rot, "wait_ms": wait_ms}


def parse_drill(drill_el, folder_name, sort_order):
    name  = drill_el.get("Name", "")
    desc  = drill_el.get("Description", "")
    ytid  = drill_el.get("YouTubeVideoID", "")
    delay = float(drill_el.get("Delay", "0") or "0")
    balls = [parse_ball(b) for b in drill_el.findall("Ball")]

    return {
        "name": name,
        "description": desc,
        "youtube_id": ytid,
        "delay_s": delay,
        "balls": balls,
        "repeat": 0,          # 0 = infinite (like original app default)
        "sort_order": sort_order,
        "readonly": True,
    }


# Read the raw file and wrap in a root element for parsing
with open("drills_xml_v1.txt", encoding="utf-8") as f:
    raw = f.read()

# Remove embedded XML declarations
raw = re.sub(r'<\?xml[^?]*\?>', '', raw)
# Wrap all <Training> blocks in a root
xml_text = "<Root>\n" + raw + "\n</Root>"
root = ET.fromstring(xml_text)

CATEGORY_ORDER = ["Introductory", "Beginner", "Intermediate", "Advanced", "Bonus"]
folders = []

for cat_idx, cat_name in enumerate(CATEGORY_ORDER):
    training_el = root.find(f"Training[@Name='{cat_name}']")
    if training_el is None:
        continue
    desc = training_el.get("Description", "")
    drills = []
    for drill_idx, drill_el in enumerate(training_el.findall("Drill")):
        drills.append(parse_drill(drill_el, cat_name, drill_idx))
    folders.append({
        "name": cat_name,
        "description": desc,
        "sort_order": cat_idx,
        "readonly": True,
        "drills": drills,
    })

output = {"folders": folders}
total = sum(len(f["drills"]) for f in folders)
print(f"Converted {total} drills in {len(folders)} folders")

with open("../frontend/drills_default.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Written to ../frontend/drills_default.json")
