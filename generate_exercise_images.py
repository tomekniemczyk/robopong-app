#!/usr/bin/env python3
"""Generate exercise animation frames using Vertex AI Imagen 3."""

import base64, json, time, urllib.request, urllib.error, os, sys

PROJECT = "tt-hub-pl-prod"
LOCATION = "us-central1"
MODEL = "imagen-3.0-generate-002"
OUTPUT_DIR = "/home/niemczyt/src/robopong-app/robopong-app-ex-rework/frontend/static/exercises/frames"
CREDS_FILE = "/home/niemczyt/.gemini/oauth_creds.json"

STYLE = (
    "flat design infographic illustration, exercise tutorial style, "
    "woman athlete with orange sports bra top and cobalt blue athletic leggings, "
    "white background, clean minimalist cartoon style, simple bold shapes, "
    "full body visible, no text or labels, high contrast"
)

# Frame definitions: (filename_base, [4 pose descriptions])
FRAMES = [
    # --- WARMUP ---
    ("jog", [
        "jogging in place, left foot on ground, right knee slightly raised, arms bent and pumping, athletic stance",
        "jogging in place, right foot raised high, knee at hip height, left arm forward, right arm back",
        "jogging in place, both feet briefly near ground, light on feet, active arm swing",
        "jogging in place, left knee raised high, right arm forward, leaning slightly forward",
    ]),
    ("highknees", [
        "high knees exercise, right knee raised to chest height, left arm raised, exaggerated knee lift",
        "high knees exercise, left knee raised very high to chest, right arm forward, explosive movement",
        "high knees exercise, right knee up even higher, arms pumping vigorously",
        "high knees, left knee pulled up to chest, standing on tiptoe on right foot",
    ]),
    ("arm_circle", [
        "arm circles exercise, standing upright, both arms extended straight out to sides at shoulder height",
        "arm circles exercise, both arms raised overhead making large circles, arms at 12 o'clock",
        "arm circles, arms crossed in front at shoulder level, continuing circular motion",
        "arm circles, arms lowered to 6 o'clock position, completing the circle downward",
    ]),
    ("wrist_rot", [
        "wrist rotation exercise, both arms extended forward at chest height, hands in loose fists",
        "wrist rotations, arms extended forward, wrists rotated clockwise, fists at 45 degrees",
        "wrist rotations, wrists at 6 o'clock position, fists pointing down",
        "wrist rotations, wrists rotated counterclockwise, fists at 9 o'clock",
    ]),
    ("trunk_rot", [
        "trunk rotation exercise, standing upright facing forward, arms relaxed at sides, ready position",
        "trunk rotation, upper body rotating to the right, arms swinging out to sides like windmill",
        "trunk rotation, facing center again, arms returning to sides",
        "trunk rotation, upper body rotating to the left, arms swinging freely, hips stable",
    ]),
    ("hip_circle", [
        "hip circles exercise, hands on hips, hips pushed to the right in wide circle",
        "hip circles, hands on hips, hips pushed forward, belly forward",
        "hip circles, hands on hips, hips shifted to the left",
        "hip circles, hands on hips, hips pushed backward, bottom out",
    ]),
    ("lunge", [
        "dynamic lunge exercise, standing upright, feet together, hands on hips, ready to step",
        "dynamic lunge, big step forward with right leg, deep lunge position, right knee above ankle, left knee near floor",
        "dynamic lunge, pushing back up from lunge, right leg driving up",
        "dynamic lunge, stepping forward with left leg into lunge, left knee bent at 90 degrees, torso upright",
    ]),
    ("shadow", [
        "table tennis shadow play, athletic ready stance, holding invisible paddle, knees bent, weight forward",
        "shadow play, preparing backhand stroke, rotating torso to left, invisible paddle pulled back",
        "shadow play, executing forehand topspin loop, racket arm swinging forward, hip rotation",
        "shadow play, forehand follow-through, racket hand raised, weight shifted forward, balanced recovery",
    ]),
    # --- FOOTWORK ---
    ("footwork", [
        "table tennis footwork drill, athletic low stance, feet wide apart, knees bent, ready position",
        "lateral shuffle to the right, pushing off left foot, stepping right, low center of gravity",
        "wide stance on right side, backhand ready position, feet planted, knees bent low",
        "shuffling back to center, both feet moving, explosive push off right foot",
    ]),
    # --- SPEED ---
    ("speed", [
        "fast counter-drive drill, at ping pong table, compact forehand stroke, short backswing",
        "fast hands drill, rapid backhand counter, elbow close to body, quick wrist snap",
        "speed drill, rapid forehand flick, minimal backswing, explosive short punch",
        "speed training, recover quickly after stroke, return to ready stance, paddle ready",
    ]),
    # --- AGILITY ---
    ("agility", [
        "agility ladder drill, stepping into ladder squares, fast feet, looking forward",
        "lateral agility through ladder, side-stepping pattern, quick precise footwork",
        "cone touch drill, sprinting to orange cone, reaching down to touch it",
        "explosive direction change, pivoting to sprint back, arms driving movement",
    ]),
    # --- STRENGTH ---
    ("boxjump", [
        "box jump exercise, standing in front of small plyo box, in quarter squat preparation, arms back",
        "box jump, jumping up explosively, airborne, arms swinging up, bent knees",
        "box jump, landing softly on box, both feet flat, absorbing impact in deep squat",
        "box jump, stepping down from box carefully, controlled descent",
    ]),
    ("squat", [
        "bodyweight squat exercise, standing upright, feet shoulder-width apart, arms at sides",
        "squat, lowering down, arms raised forward for balance, thighs beginning to parallel",
        "squat, deep squat position, thighs parallel to floor, arms extended forward, back straight",
        "squat, pushing up from squat, halfway risen, arms lowering, strong leg drive",
    ]),
    ("plank", [
        "forearm plank exercise, side view, body in straight diagonal line, on forearms and toes",
        "forearm plank, front view, both forearms on ground, head neutral, core engaged, flat back",
        "forearm plank hold, slight side angle view, hips level, spine neutral, breathing",
        "forearm plank, slight three-quarter view, strong straight body position head to heels",
    ]),
    ("sideplank", [
        "side plank exercise, left side, resting on left forearm, feet stacked, right arm pointing up",
        "side plank, right side, resting on right forearm, left arm raised straight up toward ceiling",
        "side plank on left side, hips dropping slightly then raising, working obliques",
        "side plank on right side, body straight, hips lifted high, strong plank position",
    ]),
    ("band", [
        "resistance band forehand exercise, holding band like racket grip, backswing preparation position",
        "resistance band forehand, pulling band forward, forehand stroke motion, band stretching",
        "resistance band, full forehand follow-through, arm extended, hip rotated through",
        "resistance band recovery, returning to starting ready position, elastic band at rest",
    ]),
    ("calf", [
        "calf raise exercise, standing flat on both feet, facing forward, hands at sides",
        "calf raise, rising up on balls of feet, heels lifting off ground, slight knee bend",
        "calf raise, peak position on tiptoes, maximum calf contraction, elevated",
        "calf raise, slowly lowering heels back down, controlled eccentric movement",
    ]),
    # --- COOLDOWN ---
    ("quad_stretch", [
        "quad stretch walk, standing on right foot, left foot pulled up to left glute with left hand, balancing",
        "quad stretch walk, holding stretch, right arm out for balance, left knee pointing down",
        "quad stretch walk, taking a step, switching legs, pulling right foot to right glute",
        "quad stretch walk, balanced on left foot, right foot held at glute, gentle pull, upright posture",
    ]),
    ("hamstring_stretch", [
        "hamstring stretch, right heel resting on low surface, leg straight, standing upright",
        "hamstring stretch, hinging forward at hips with straight back, reaching toward right toes",
        "hamstring stretch, deeper forward hinge, feeling hamstring pull, shoulders back",
        "hamstring stretch, switching to left leg elevated, beginning to hinge forward",
    ]),
    ("shoulder_stretch", [
        "shoulder stretch, right arm pulled straight across chest, left forearm pressing it, looking relaxed",
        "shoulder stretch, holding cross-body stretch, right arm held at chest level, head straight",
        "shoulder stretch, releasing and switching, left arm pulled across chest with right hand",
        "shoulder stretch other side, holding left shoulder stretch, both arms in front of chest",
    ]),
    ("wrist_stretch", [
        "wrist flexor stretch, right arm extended forward palm facing up, left hand gently pulling fingers back",
        "wrist stretch, holding the wrist extension, feeling stretch along forearm underside",
        "wrist flexor stretch, left arm extended palm up, right hand pulling left fingers back",
        "wrist stretch other side, holding left wrist stretch, both arms in front",
    ]),
    ("breathing", [
        "deep breathing exercise, standing relaxed, arms at sides, neutral calm posture, eyes forward",
        "deep breathing inhale, arms slowly rising to sides as breathing in, lifting outward",
        "deep breathing, arms fully open wide at shoulder height, full inhale, chest expanded",
        "deep breathing exhale, arms slowly lowering and coming in front, exhaling slowly through mouth",
    ]),
]


def get_token():
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET")
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': creds['refresh_token'],
        'grant_type': 'refresh_token',
    }
    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())['access_token']


def generate_image(token, prompt, filepath, retries=3):
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
        f"/publishers/google/models/{MODEL}:predict"
    )
    full_prompt = f"{STYLE}, {prompt}"
    payload = {
        "instances": [{"prompt": full_prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
            "safetyFilterLevel": "block_few",
        }
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=60)
            d = json.loads(resp.read())
            img_b64 = d['predictions'][0]['bytesBase64Encoded']
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(img_b64))
            return True
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  HTTP {e.code}: {body[:200]}")
            if e.code == 429:
                wait = 60 * (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 401:
                print("  Token expired, refreshing...")
                return None  # Signal to refresh token
            else:
                if attempt < retries - 1:
                    time.sleep(10)
                else:
                    return False
        except Exception as ex:
            print(f"  Error: {ex}")
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return False
    return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    token = get_token()
    token_refresh_time = time.time()

    total = sum(len(frames) for _, frames in FRAMES)
    done = 0
    skipped = 0
    failed = []

    for base_name, frame_prompts in FRAMES:
        for i, prompt in enumerate(frame_prompts, 1):
            filename = f"{base_name}_{i}.png"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(filepath):
                print(f"  skip {filename} (exists)")
                skipped += 1
                done += 1
                continue

            # Refresh token every 50 minutes
            if time.time() - token_refresh_time > 3000:
                print("Refreshing token...")
                token = get_token()
                token_refresh_time = time.time()

            print(f"[{done+1}/{total}] Generating {filename}...")
            result = generate_image(token, prompt, filepath)

            if result is None:  # Token expired
                token = get_token()
                token_refresh_time = time.time()
                result = generate_image(token, prompt, filepath)

            if result:
                size = os.path.getsize(filepath)
                print(f"  ✓ {filename} ({size//1024}KB)")
            else:
                print(f"  ✗ FAILED: {filename}")
                failed.append(filename)

            done += 1
            # Small delay to avoid rate limits
            time.sleep(2)

    print(f"\n=== Done: {done-len(failed)-skipped} generated, {skipped} skipped, {len(failed)} failed ===")
    if failed:
        print("Failed:", failed)


if __name__ == "__main__":
    main()
