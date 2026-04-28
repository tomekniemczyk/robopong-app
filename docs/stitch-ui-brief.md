# AcePad — UI/UX Brief for Google Stitch

> Complete specification for generating screens for **AcePad** (by tthub.pl) — a web app that controls a Donic Robopong 3050XL table tennis ball-launcher robot. Use this document as input to Stitch to generate every screen listed below.

---

## 1. Product summary (the pitch Stitch should internalize)

**AcePad** is a premium, training-grade companion app for table-tennis robot owners. It replaces the original Newgy/Donic mobile controller with a faster, multi-user, multi-language experience optimized for **court-side use on a phone** and **coaching sessions on a tablet / laptop**.

The user is an athlete (or coach) who:
1. Connects to a physical robot via Bluetooth LE or USB.
2. Calibrates the motors and head position for their specific robot.
3. Runs **drills** (preset ball sequences) and structured **trainings** (drills + physical exercises + rest, in order).
4. Records sessions with a ceiling camera and reviews/compares videos.
5. Tracks personal progress per player: streaks, ball counts, completion rates, 30-day challenges.

Multiple devices can be connected to one robot simultaneously: one is **Controller**, others are **Observers**. Control can be requested and handed over between sessions.

---

## 2. Target audience & use context

| Who | Environment | Device | Posture |
|-----|-------------|--------|---------|
| Amateur / hobby player | Home basement, garage | Phone (one-handed) | Standing next to table, wet hands |
| Coach | Club hall | Tablet mounted on cart | Seated, looking up from 2–3 m |
| Pro player | Training center | Phone + laptop observer | Walking around table |

**Critical context:** during a drill, the user is **3 meters away from the screen, sweating, holding a paddle**. The running-drill overlay must be readable with a glance — counters and timers at ≥28 px, high contrast, no fine print. This is the single most important UX constraint in the app.

---

## 3. Design language — "precision, performance, a clean court"

### 3.1 Mood

- **Light and airy**, not dark — move away from the current dark theme toward a bright, optimistic, premium look that reads as "sports tech" rather than "gaming app."
- **Minimal ornamentation.** Flat panels, generous whitespace, thin dividers. Think Apple Fitness + Linear + a modern pro-sports brand site.
- **Confidently sport-flavored**, not cartoonish. Table-tennis cues are suggested through color, geometry, and micro-details, never through literal illustrations of paddles on every screen.

### 3.2 Color palette (light theme)

| Token | Hex | Use |
|-------|-----|-----|
| `--bg` | `#F6F7FB` | App background |
| `--surface` | `#FFFFFF` | Cards, sheets, modals |
| `--surface-alt` | `#EEF1F7` | Pressed / secondary surfaces, subtle zebra |
| `--border` | `#E3E7EF` | Hairlines, dividers, input borders |
| `--text` | `#0C1220` | Primary text |
| `--text-2` | `#475069` | Secondary text |
| `--muted` | `#8B93A8` | Tertiary / placeholder / captions |
| `--accent` | `#1D4F91` | Primary — "ITTF blue", the color of a tournament table |
| `--accent-ink` | `#FFFFFF` | Text on accent |
| `--accent-soft` | `#E8EEF8` | Accent-tinted backgrounds, selected chips |
| `--ball` | `#FF6A13` | Secondary — "match-ball orange" (the color of an ITTF ball) |
| `--ball-soft` | `#FFF1E6` | Secondary-tinted surfaces |
| `--success` | `#12A150` | Completed, confirmed, positive deltas |
| `--warning` | `#F59E0B` | Paused, stopped, cautions |
| `--danger` | `#E5484D` | Recording dot, destructive actions, errors |
| `--topspin` | `#FF6A13` | Topspin ball indicator |
| `--backspin` | `#2A86E3` | Backspin ball indicator |
| `--nospin` | `#F2C94C` | No-spin ball indicator |

**Dark mode variant** exists in parallel — flip `--bg` to `#0C1220`, `--surface` to `#161B2B`, `--accent` stays, text inverts. Auto-switches from system preference; manual override in Settings.

### 3.3 Typography

- **Display / headings:** Inter, 700, tight tracking (`-0.01em`). Optional variable-font weight transitions on hover.
- **Body:** Inter, 400/500, normal tracking.
- **Numeric / counters / timers:** JetBrains Mono or SF Mono, 700, tabular-nums. **Always** tabular for anything that ticks.
- **Scale** (mobile baseline, +2 px on desktop):
  - Display-XL (big counters on training overlay): 72 / 700 / mono
  - Display-L (drill counter overlay): 48 / 700 / mono
  - H1 (page title): 22 / 700
  - H2 (card title): 16 / 700
  - Body: 14 / 400
  - Caption: 12 / 500 / muted
  - Micro (labels, tags): 10 / 600 / uppercase / letter-spacing .06em

### 3.4 Shape, elevation, motion

- **Radius scale:** 8 (inputs), 12 (cards), 20 (sheets, modals), 999 (pills & chips).
- **Shadows:** soft and single-layer. `0 1px 2px rgba(12,18,32,.04), 0 8px 24px rgba(12,18,32,.06)`. Reserved for cards and floating sheets.
- **Motion:** 180 ms `ease-out` for enter, 140 ms `ease-in` for exit. A single "elastic" pop (240 ms, cubic-bezier(.2,.9,.25,1.25)) is used **only** on ball-counter increments and new-preset confirmations.
- **Focus ring:** 2 px `--accent` outline offset by 2 px, visible on keyboard focus only.

### 3.5 Iconography

- 1.5 px stroke line icons (Lucide-style). Filled variants reserved for active navigation state.
- App has four proprietary SVG marks that must stay: **drill** (paddle + blue table), **training** (red stick-figure at a table), **calibration** (red-white target), **robot** (abstract unit above a net). Stitch should reuse or restyle these four, not redesign them from scratch.

### 3.6 Table-tennis visual cues

The "tennis feel" comes from four recurring elements, not from literal decoration:

1. **Table plan diagrams** — a blue (`--accent`) rectangle with a white center line and a gray net strip at the top, used anywhere ball positions are shown.
2. **Ball dots** — colored circles (`--topspin`, `--backspin`, `--nospin`) with a thin white stroke and a centered index number.
3. **Court-line white hairlines** — 1 px white strokes on accent-colored blocks used as section breaks on hero sections.
4. **Counter chips** — rounded pills with a small circle on the left (ball icon) that spin once when they tick up.

---

## 4. Responsive rules

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | 360–679 | Single column, `max-width 100%`, bottom tab bar fixed. Page max-width = viewport. |
| Tablet | 680–1023 | Single column **centered at `max-width: 720px`**, bottom tab bar still fixed. Cards get internal 2-column grids (e.g., stats). |
| Desktop / Laptop | ≥1024 | Two-pane: left rail (240 px) replaces the bottom tab bar; right pane is the same 720 px content column centered in the remaining space, with a 320 px "context" panel on the right for Sessions / Device / Active Drill when relevant. |

**One golden rule:** the **running drill / training overlay** uses the **entire screen** at every breakpoint. No navigation chrome, no paddings below 16 px. When a drill is running, the layout is replaced wholesale.

**Safe-area insets** must be honored on iOS PWA — bottom nav respects `env(safe-area-inset-bottom)`, top bar respects `env(safe-area-inset-top)`.

---

## 5. Global chrome (appears on every normal page)

### 5.1 Top bar (56 px)

From left to right:
1. **Brand mark** — small paddle-ball glyph + word "AcePad" in 14/700. No version string in production (version hidden behind long-press).
2. **Language picker** — five round 22 px chips: `PL EN DE FR ZH`. Active one is filled with `--accent`. On mobile it collapses to a single flag chip that opens a popover.
3. **Connection badge** — pill showing state: `Offline` (gray dot + muted text), `Simulation` (amber dot + "Sim"), `Connected • <robot name>` (green dot + robot name). Tapping it: opens **Device Info sheet** when connected, jumps to **Connect page** when not.
4. **Calibration shortcut** — red-white target icon, only visible when connected. Opens calibration wizard.
5. **Role pill** — shows current session role: `🎮 Controller` (green), `👁 Observer` (gray), `⏳ Pending` (amber pulsing).
6. **Sessions button** — `👥 <count>` chip; opens Sessions popover (anchored below).
7. **Active player avatar** — circular gradient chip with the player's initial + short name. Tapping it opens the player's profile. A tiny "switch player" arrow next to it opens Player Picker.

### 5.2 Bottom tab bar (mobile) / left rail (desktop)

Six items, all icon + label:

| Icon | Label | Destination |
|------|-------|-------------|
| Paddle + blue table | **Drills** | Drill library |
| Red stick-figure | **Training** | Training plans |
| Dumbbell | **Exercises** | Physical exercises |
| Chart | **History** | Session history & leaderboard |
| Camera | **Camera** | Live ceiling camera stream |
| Wrench | **Service** | Popover → Exploration, Logs |

Drills and Training tabs are **dimmed to 40 %** when connected but not calibrated; tapping them shows a toast and redirects to Calibration.

### 5.3 Persistent overlays

- **Observer / Pending banner** — full-width bar below top bar, amber, only when `role ≠ controller`. Contains "Take control" button (with a cooldown countdown) and optional "Force" variant.
- **Toast** — single floating pill at the bottom center above the tab bar, 3 s timeout, `--surface` background.

---

## 6. Screens — every view to generate

Each screen below gets a full Stitch generation. Specify **purpose, states, key components, flow, interactions**. Most screens have an `empty`, `loading`, `active`, and `error` state unless noted.

### Screen 1 — Onboarding / Welcome

**Purpose:** First-run screen. User lands here if no player exists in the database.

**Layout:**
- Full-bleed accent-blue hero with white center-line hairlines in the background.
- Paddle-ball brand mark (64 px) centered.
- "AcePad" wordmark (28/800) + tagline: *"Your private coach for Donic Robopong."*
- Language picker pill-row.
- Single primary CTA: **Create your profile →**.

**Flow:** CTA opens Screen 1b — *Create Profile* (name input, handedness toggle: Right/Left, language already inherited from picker, optional avatar color). Save → lands on `Connect`.

### Screen 2 — Connect (Robot pairing)

**Purpose:** Let the user pair with a real robot via BLE or USB, or enable Simulation mode.

**States:** `idle`, `scanning`, `results`, `connecting`, `connected`, `error`, `permission_denied`.

**Layout:**
- Page title: **Connect your robot** with muted subtitle "Bluetooth, USB, or simulation".
- Three tab-cards in a row (wraps on narrow): **Bluetooth (BLE)**, **USB cable**, **Simulation**.
- **BLE card:** big "Scan" button, list of found devices (rows: icon, name, MAC, RSSI bars, "Connect"). Hint line: *"Only Donic / Newgy robots will appear."* "Last device" row at top when present, with quick-reconnect.
- **USB card:** list of serial ports with "Search" button; each row has a port name and "Connect".
- **Simulation card:** explanatory text *"Drills and training without a robot — visualization and sounds only"* + large toggle.
- Bottom of screen: small "Forget this device" ghost link when a last device is remembered.

**Flow:** Connect → handshake animation → on success route to Calibration if not yet calibrated for that device address, otherwise to Drills.

### Screen 3 — Calibration wizard

**Purpose:** Tune motor speeds, head position, oscillation and wait time for a specific robot (stored per device address).

**Hard UX rule (non-negotiable):** motors **stop after each throw** — they must not keep spinning. Pressing the "Throw" button performs: `set_ball → 300 ms → T → 1500 ms → H`. Auto-warm-up on entering the screen is **forbidden**.

**Layout (wizard, 3 logical steps shown as a horizontal stepper at top):**

1. **Head position** (motors off): a top-down table SVG (same one as Drill detail) showing the current target. Two sliders: **Height** (75–210, center 150) and **Oscillation** (127–173, center 150). Rotation is locked at 150 and labeled 🔒. A "click to zoom" tabletop preview renders the current head vector.
2. **Motors + Throw:** two large numeric steppers labeled **Top** and **Bottom** (−50 to +50). A "Wait time (ms)" field (200–10000). Three buttons in a row: **⚡ Calibrate**, **🏓 Throw**, **⏹ Stop**.
3. **Save as preset:** input for preset name, list of existing presets with Load/Overwrite/Set default/Delete per row.

- Collapsible help card "How to calibrate?" above the wizard with explanatory diagrams and the procedure: *"Send → wait ~1.5 s for motors to spin up → Throw → evaluate → adjust → repeat. Save preset when satisfied."*

**States:** `disconnected` (big muted message "Connect a robot first"), `active` (wizard), `saving`, `presets_empty`.

### Screen 4 — Drills library

**Purpose:** Browse, search, edit, and launch pre-defined ball sequences. This is the daily workhorse screen.

**Layout:**
- Top row: page title **Drills**, right-aligned **⬇ Export** and **+ Folder** buttons.
- Search field (rounded, full width) with placeholder "Search drills…".
- **Folder list** — each folder is a collapsible accordion row: caret, folder name, count chip, action buttons (add drill, move up/down, rename, delete). Read-only system folders show the same row without edit actions.
- Inside a folder: **Drill rows** with name, description tooltip, move up/down, move-to-folder, edit, delete, and an inline star to favorite.
- Tapping a drill row expands a **Drill detail panel** in place (instead of opening a modal). The panel contains:
  - The blue half-table SVG with dots for every ball in the sequence, numbered, colored by spin type. Legend below: topspin / backspin / no-spin.
  - An optional second SVG below showing **historical landings** as translucent orange/blue dots — only when the current player has landing data.
  - Two side-by-side inputs: **Balls** (number, 1–999) and **Tempo** (25–200 % range slider with live percent).
  - Computed line: `⏱ ~<duration> · <count> balls`.
  - **Record training** toggle with a 🎥 icon (only when a player is selected).
  - Navigation row: `◀ Prev · Start · Next ▶`. Start is a large green pill, disabled when not connected or not Controller.
- Unfiled drills section at the bottom.
- Empty state: 📚 illustration and "No drills. Add a folder." CTA.

### Screen 5 — Drill editor (modal)

**Purpose:** Create or edit a drill — name, description, repetitions, and a **ball sequence**.

**Layout (sheet on mobile, centered modal on desktop, max-width 520 px):**
- Header: "New drill" / "Edit drill".
- Form rows: **Name**, **Description (optional)**, **Repetitions** (numeric stepper).
- **Balls** section — rows of ball cards with: drag handle, index, numeric inputs for Top, Bottom, Osc, Height, Rot, Wait (ms), and delete. "+ Add" at the bottom. If empty: "Add the first ball" button.
- Tip row explaining value ranges (Osc 127–173 center 150, Height 75–210, Rot 90–210 center 150).
- Footer: Cancel (ghost) + 💾 Save (primary). Save is disabled until name and at least one ball exist.

### Screen 6 — Running drill overlay

**Purpose:** Full-screen view while a drill is running. This is the **"3 meters away"** screen.

**Layout:**
- **Full bleed**, accent-blue gradient background with faint white court lines.
- Top-left: drill name + folder name (muted).
- Top-right: Close (X) — with "Stop drill?" confirm.
- **Center hero** — a giant mono counter: `<thrown>/<total>` (Display-XL), and under it `round <n>/<max>`. This number must be readable from 3 m.
- **Under the counter:** a horizontal progress bar with segment ticks for every ball. Current ball is highlighted in `--ball` orange.
- **Under the bar:** tempo % chip, remaining estimated time ⏱, current ball type icon (topspin/backspin/no-spin).
- **Bottom controls (fixed, safe area aware):** `⏸ Pause`, `▶ Resume`, `⏹ Stop`. Pause state replaces the hero with "⏸ PAUSED" in Display-XL.
- **Top-left corner during recording:** pulsing red dot + `REC` label.

**Accessibility:** large hit targets (64 px min), no tiny icons, haptic feedback on ball tick (mobile), sound on final ball.

### Screen 7 — Training library

**Purpose:** List and manage **training plans** — ordered sequences of drills, exercises, and rest steps.

**Layout:**
- Top row: page title **Trainings**, active player chip, **+ New** button.
- Filter tabs (pill row): **Upcoming · All · Past**.
- Training cards grouped by folder. Each card shows: title, description, count of steps, total duration estimate, favorite star, "Edit", "Duplicate", "Delete", and a large **Start** button on the right.
- Empty state: stick-figure icon + "No trainings yet. Create your first plan."

### Screen 8 — Training editor (modal)

**Purpose:** Build a training as a list of steps.

**Layout (wide sheet):**
- Header: "New training" / "Edit training".
- Form: **Name**, **Description**, **Countdown (sec)** — the "get ready" countdown before the first drill.
- **Steps** section — reorderable rows, each row has a type dropdown (`Drill`, `Exercise`, `Rest`) and type-specific inputs:
  - Drill: drill picker + count + tempo %
  - Exercise: exercise picker + duration
  - Rest: duration only
- Each row has ↑ ↓ ✕ controls. "+ Add step" at the bottom.
- Footer: Cancel + 💾 Save.

### Screen 9 — Running training overlay

**Purpose:** Full-screen view for a multi-step training. Extends the running-drill overlay.

**Layout (built on top of Screen 6):**
- **Top strip:** "Step 3 of 8 · Forehand topspin" with a linear progress through all steps.
- **Countdown state:** "Get ready…" Display-XL + giant 5-4-3-2-1 counter.
- **Drill-step state:** same as Running drill overlay (Screen 6), plus a ghost "Next: Rest 30 s" hint at the bottom.
- **Exercise-step state:** timer card with exercise name (e.g., "Plank"), a giant countdown, and a hero illustration of the exercise (load from `/static/img/exercises/<id>.png`).
- **Rest-step state:** calm blue overlay, "Rest" heading, large countdown, and "Next: <next step>" hint.
- **Bottom controls:** `⏸`, `▶`, `⏭ Skip`, `⏹ Stop`, plus a **"Percent"** stepper (−10 / +10) to adjust next drill's tempo on the fly, and a **📝 Note** button to attach a quick note to this step.

### Screen 10 — Exercises library

**Purpose:** Browse physical exercises that can be inserted into a training plan.

**Layout:**
- Grid of exercise cards (2 columns mobile, 3 tablet, 4 desktop).
- Each card: high-quality photo or illustration, name, default duration (editable inline), tap to open detail.
- Sticky "Reset all durations" text link at the bottom.

### Screen 11 — Exercise detail (sheet)

**Purpose:** Show how-to, set a custom duration, and run the exercise solo (without starting a training).

**Layout:**
- Hero image, name, category tag, default duration.
- Description block with short instructions.
- Numeric stepper for **custom duration** override.
- **▶ Start solo** button — opens a timer full-screen overlay identical to the training exercise state (Screen 9).

### Screen 12 — History

**Purpose:** Review completed training/drill sessions per player and across all players.

**Layout:**
- Top row: page title, player picker (dropdown: "All players" or a specific player).
- Search field.
- **Leaderboard card** (only when "All players" is selected): sortable table with columns: Player, Sessions, Time, Balls, %. Rows clickable — jumps to that player.
- **Hierarchical tree** of sessions:
  - Level 1: `Trainings` / `Drills`
  - Level 2: folder
  - Level 3: training or drill name
  - Level 4: session entries — each shows date, status icon (✅ completed, ⏹ stopped, ❌ failed), elapsed time `⏱`, balls `🏓`, optional REC dot.
  - Expanding a session reveals per-step rows with checkmarks and, if recordings exist, buttons to **Play**, **Download**, **Compare**.
- Stopped sessions show a "⏩ Resume" quick button.

### Screen 13 — Video player & comparison

**Purpose:** Playback recorded training videos, compare two recordings side by side.

**Layout (full-screen modal):**
- **Single video mode:** video element, scrubber, play/pause, speed (0.25x–2x), download, delete, close.
- **Compare mode:** two videos side by side (stacked on mobile), synced play, independent speed, swap, scrub both.
- A banner at the bottom labels each with date/player/drill.

### Screen 14 — Camera

**Purpose:** Live ceiling camera stream and spot-check framing.

**Layout:**
- Large video embed (motion MJPEG, port 8081).
- "Stream unavailable" fallback card with a retry button.
- Info footer: "Motion stream — port 8081".
- Auto-hide chrome after 3 s idle.

### Screen 15 — Players (profile dashboard)

**Purpose:** A player's home page — stats, streaks, challenges, favorites, management.

**Layout:**
- Header row: big circular initial avatar (gradient), name, "Trainings done: N", edit pencil, "Compare" button (when ≥ 2 players exist).
- **Settings row:** two segmented controls — Handedness (Right / Left) and Language (PL EN DE FR ZH).
- **30-Day Challenge** card (teal gradient): "🏆 30-Day Challenge · 12/30" with a progress bar.
- **Stats grid** — 6 colorful tiles (2x3 on mobile, 3x2 on desktop):
  - Sessions (indigo)
  - Total Time (sky)
  - Completion % (green)
  - Avg Duration (amber)
  - Streak (red / fire)
  - Total Balls (violet)
  Each tile: big icon, big value, small label, a ghost icon in the bottom-right corner.
- **Weekly activity** — expandable chart: one row per week with a stacked bar (completed + stopped) and a sessions count.
- **Favorites** — grouped by type (Trainings / Drills / Exercises) with quick "▶" launch buttons.
- Footer: destructive **Delete player** button (confirm dialog).

### Screen 16 — Player picker (modal)

**Purpose:** Switch active player quickly.

**Layout:**
- Sheet with a list of all players (avatar, name, last active).
- "+ Add player" at the bottom.

### Screen 17 — Drill Exploration (Service)

**Purpose:** Interactive laboratory to dial in ball parameters and tag "what this ball feels like" with rich metadata.

**Layout:**
- Top row: drill selector (`<optgroup>` by folder) and ball index chips ("Ball 1 · Ball 2 · …") plus **Save to drill** / **Create new** buttons.
- Two-pane:
  - **Left (params):** numeric steppers for `top_speed`, `bot_speed`, `oscillation`, `height`, `rotation`, `wait_ms`, `ball_count`, `interval`. Each has `−` / value / `+` with tap-and-hold. Large green **🎯 Throw (×N)** button at the bottom.
  - **Right (table):** **full** table SVG (robot half + player half, 1:1.8 proportions). The user taps **twice** to place bounce-1 and bounce-2 dots. A small caption guides them: "Click first bounce" → "Click second bounce".
- After both bounces are set, a **Describe ball** panel slides in:
  - Spin tags (multi-choice): topspin / backspin / sidespin-L / sidespin-R / no-spin / knuckle.
  - Arc: high / flat / low / bouncy.
  - Speed: slow / medium / fast / very-fast.
  - Useful for: block / topspin / push / flick / chop / rally.
  - Rating: 1–5 stars.
  - Optional comment field.
  - **💾 Save** and **Skip**.
- History row at the bottom: last 10 explorations with numeric summary, rating stars, comment snippet, delete.

### Screen 18 — Server logs (Service)

**Purpose:** Developer-facing screen. Log viewer for debugging the robot connection.

**Layout:**
- Filter input ("filter…") and **Clear** button.
- Virtualized scroll of timestamped lines, level-colored (info / warn / error).
- Auto-scroll lock toggle.

### Screen 19 — Device info sheet

**Purpose:** Quick info and actions for the currently-connected robot, opened from the top-bar connection badge.

**Layout (side sheet on desktop, bottom sheet on mobile):**
- Header: robot name (editable inline), transport (BLE / USB / Sim).
- Table:
  - Name (editable)
  - Port or MAC (monospace)
  - Transport
  - Firmware version
  - Calibration (✓ with preset count, or "no presets" muted)
- CTA stack:
  - **🎯 Go to calibration** (primary)
  - **📋 Copy diagnostic report** (ghost)
  - **Disconnect permanently** (danger, only when connected)
  - **Forget this device** (ghost muted)

### Screen 20 — Diagnostic report (modal)

**Purpose:** Copy/paste a diagnostic bundle to send to support.

**Layout:**
- Modal with a read-only monospace textarea preloaded with the report.
- Hint: "Select all (Ctrl+A) and copy (Ctrl+C)".
- Buttons: **Copy** (primary), **Close**.

### Screen 21 — Sessions panel

**Purpose:** See who else is connected to the same robot, and release/take control.

**Layout (popover anchored to top-bar sessions button):**
- Header: "Active sessions (N)".
- Rows: role pill, session id, "← You" tag, IP, short user-agent, age.
- Bottom: **🔄 Release control** (visible only when Controller).

### Screen 22 — Takeover request modal

**Purpose:** A modal prompted on the current Controller when another session requests control.

**Layout:**
- Title: "Control takeover request".
- Body: "Session <id> wants to take control of the robot."
- Footer: **✓ Accept** (primary) and **✕ Decline**.
- Caption: "No response = automatic decline".
- A 15 s countdown bar decays to danger color.

### Screen 23 — Presets manager

**Purpose:** Manage calibration presets, accessible from Calibration step 3.

**Layout:**
- Section title **PRESETS** + **+ Save as…** button.
- Rows: preset name, "default" badge when applicable, actions — Load, Overwrite, Set default, Delete.
- Empty state: "No saved presets."

### Screen 24 — Volume & audio settings

**Purpose:** Adjust server-side audio (beeps, countdowns) volume.

**Layout:**
- Card: "Server volume" with a horizontal slider and **Test** button that plays a short beep.

### Screen 25 — Voice notes list

**Purpose:** Review voice notes recorded during trainings.

**Layout:**
- List rows: player avatar, step label, duration, date, inline play button, delete.
- Per-row audio player uses native controls when expanded.

### Screen 26 — Generic confirm dialog

**Purpose:** Reused destructive action confirmation.

**Layout:**
- Modal, max-width 420 px.
- Icon (alert or trash), title, one-line body.
- Footer: Cancel (ghost) + Delete (danger) or Cancel + Continue (primary).

---

## 7. Component library Stitch should define once and reuse

| Component | Purpose | Notes |
|-----------|---------|-------|
| `TopBar` | Always mounted | Slots: brand, lang picker, conn badge, cal shortcut, role pill, sessions, player avatar |
| `BottomTabBar` | Mobile primary nav | Six slots, glowing underline on active |
| `SideRail` | Desktop primary nav | Same six items, vertical, with brand at top |
| `PageHeader` | Title + actions | Slot for title, subtitle, right buttons |
| `Card` | Content container | 12 px radius, 16 px padding, soft shadow |
| `Sheet` | Mobile bottom sheet | 20 px top radius, drag handle, backdrop |
| `Modal` | Desktop centered dialog | 20 px radius, soft shadow, backdrop |
| `TableSVG` | Reusable table plan | Props: balls[], landings[], half/full, leftHanded |
| `BallChip` | Colored ball indicator | Props: spin type, index, size |
| `StatTile` | Colorful stat block | Props: icon, value, label, gradient preset |
| `CounterHero` | Giant mono counter | Props: current, total, round, pace |
| `Stepper` | Numeric input − value + | Supports hold-to-accelerate |
| `RangeSlider` | Tempo slider | With tick marks at 25/50/100/150/200 |
| `SegmentedControl` | 2–5 options | Used for handedness, language, filter tabs |
| `PillRow` | Horizontal scrolling chips | Used for filters and spin tags |
| `RolePill` | Controller/Observer/Pending | Three variants, pulse on pending |
| `ConnBadge` | State badge | Offline / Sim / Connected |
| `EmptyState` | Illustration + CTA | Slot for icon, text, button |
| `Toast` | Floating pill notification | One at a time, 3 s |

---

## 8. Interaction & micro-behavior notes

- **Ball tick animation:** on every ball counter increment, the counter number pops (scale 1 → 1.08 → 1) and the progress bar segment fills with a 200 ms ease.
- **Drag-and-drop reordering** in Drill editor and Training editor uses native pointer events; reduced-motion mode replaces drag with ↑ ↓ buttons (always visible).
- **Calibration "Throw" button** shows a 300 ms orange ring expanding outward on tap to communicate "ball is going".
- **Recording indicator** (red dot) pulses at 1 Hz, never solid.
- **Pending takeover** role pill pulses amber.
- **Confirmation toasts** never cover the running-drill counter.
- **Scroll restoration:** tabs are kept mounted using `v-show`, so scroll positions **must** be preserved when the user flips between Drills / Training / History.
- **Haptics (mobile):** light tick on ball count, medium impact on session end, heavy on takeover granted.

---

## 9. Accessibility requirements

- WCAG AA contrast on every text/background pair. The running-drill counter targets AAA (7:1) because of the 3 m viewing distance.
- All interactive elements ≥ 44×44 px on touch, ≥ 32×32 px on pointer.
- Visible keyboard focus ring on every focusable element.
- All icons paired with a text label or `aria-label`.
- **Reduced motion** setting disables the ball-pop, pulse, and drag animations.
- Screen-reader: live regions for ball counter (`aria-live="polite"`), takeover modal (`aria-live="assertive"`).

---

## 10. i18n constraints

- Five languages shipped: **PL, EN, DE, FR, ZH**. Default = PL.
- All UI strings go through `t(key)`; content strings (drill names, folder names, exercise names) go through `tc(type, key)`.
- Chinese font stack includes `"Noto Sans SC"`.
- **Layouts must tolerate +30 % German text expansion** on buttons. No truncation on primary CTAs.
- Numeric formatting is locale-aware (Polish uses comma decimal separators, Chinese uses the same digits).
- Right-to-left is **not** required (no Arabic / Hebrew in scope).

---

## 11. Light-design principles (Stitch heuristics)

1. **Whitespace first.** If a screen feels cramped, remove a divider before adding one. 16 px is the minimum gutter; 24 px is the default card padding on tablet/desktop.
2. **One accent per section.** Don't color more than one button blue in a row.
3. **No gradients except on stat tiles and the onboarding hero.** Everywhere else, flat.
4. **No text on images.** Exercise cards overlay text on a darkened top strip, not over the whole photo.
5. **Icons are monochrome** except the four brand marks (drill, training, calibration target, robot) and the spin-colored ball dots.
6. **Data first, chrome second.** The running-drill overlay contains exactly one thing at full size: the counter.

---

## 12. Out of scope for Stitch (don't generate)

- Marketing landing page (separate).
- Admin panel / server metrics dashboard.
- Any screen that isn't listed in section 6.

---

## 13. What Stitch should produce per screen

For each screen listed in section 6, Stitch should output:

1. **Mobile layout** (375 px width).
2. **Tablet layout** (768 px width).
3. **Desktop layout** (1280 px width).
4. **Light and dark theme** variants.
5. **Key states:** at minimum `default`, `empty`, `loading`, `active`, `error` where applicable.
6. **Component annotations** referencing the shared components in section 7.

Font stack: Inter (body) + JetBrains Mono (numeric).
Color tokens: exactly as defined in section 3.2 — do not introduce new hues.

---

## 14. Tone of voice for copy inside screens

- **Confident, short, coachy.** "Start drill", not "Click here to begin".
- **Second person.** "Your profile", not "User profile".
- **Polish is the default** — all screens must be generated first in Polish and then translated; if Stitch does not support Polish drafting, generate in English using the key names from `frontend/i18n.js` and mark strings with `t('key')` placeholders.
- **No jargon from the hardware protocol** on user-facing screens (no "command A/B", "MLDP", "FTDI" on normal pages — only on Device info, Diagnostic report, and Logs).

---

*End of brief. Feed this document into Google Stitch, then iterate screen by screen from section 6.*
