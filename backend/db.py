import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent / "robopong.db"
DRILLS_DEFAULT = Path(__file__).parent / "drills_default.json"


def init():
    with sqlite3.connect(DB) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                balls       TEXT NOT NULL,
                repeat      INTEGER DEFAULT 1,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS drill_folders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                sort_order  INTEGER DEFAULT 0,
                readonly    INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS drills (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id   INTEGER REFERENCES drill_folders(id) ON DELETE SET NULL,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                youtube_id  TEXT DEFAULT '',
                delay_s     REAL DEFAULT 0,
                balls       TEXT NOT NULL DEFAULT '[]',
                repeat      INTEGER DEFAULT 0,
                sort_order  INTEGER DEFAULT 0,
                readonly    INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_trainings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                countdown_sec INTEGER DEFAULT 20,
                steps       TEXT NOT NULL DEFAULT '[]',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS training_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                training_id     INTEGER NOT NULL,
                player_id       INTEGER,
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                elapsed_sec     INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'completed',
                steps_completed INTEGER DEFAULT 0,
                steps_total     INTEGER DEFAULT 0,
                steps_skipped   TEXT DEFAULT '[]',
                step_notes      TEXT DEFAULT '[]',
                session_comment TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS recordings_meta (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id       INTEGER NOT NULL,
                training_id     INTEGER,
                training_name   TEXT DEFAULT '',
                step_idx        INTEGER DEFAULT 0,
                step_name       TEXT DEFAULT '',
                filename        TEXT NOT NULL,
                started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_sec    INTEGER DEFAULT 0,
                size_bytes      INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS voice_notes (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id           INTEGER NOT NULL,
                training_history_id INTEGER,
                step_idx            INTEGER DEFAULT 0,
                filename            TEXT NOT NULL,
                started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms         INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ball_landings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id   INTEGER NOT NULL,
                drill_id    INTEGER NOT NULL,
                x           REAL NOT NULL,
                y           REAL NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        count = c.execute("SELECT COUNT(*) FROM drill_folders").fetchone()[0]
        if count == 0 and DRILLS_DEFAULT.exists():
            _seed_drills(c)
        c.execute("""
            CREATE TABLE IF NOT EXISTS ball_exploration (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id       INTEGER,
                firmware        INTEGER,
                top_speed       INTEGER,
                bot_speed       INTEGER,
                oscillation     INTEGER,
                height          INTEGER,
                rotation        INTEGER,
                wait_ms         INTEGER,
                cal_top         INTEGER,
                cal_bot         INTEGER,
                cal_osc         INTEGER,
                cal_h           INTEGER,
                cal_rot         INTEGER,
                bounce1_x       REAL,
                bounce1_y       REAL,
                bounce2_x       REAL,
                bounce2_y       REAL,
                spin            TEXT,
                arc             TEXT,
                perceived_speed TEXT,
                useful_for      TEXT,
                rating          INTEGER,
                comment         TEXT DEFAULT '',
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id   INTEGER NOT NULL,
                item_type   TEXT NOT NULL,
                item_id     INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, item_type, item_id)
            )
        """)
        # ── Migrations ──────────────────────────────────────────
        _migrate(c)


def _migrate(c):
    """Add columns that may be missing on older databases."""
    cols = {r[1] for r in c.execute("PRAGMA table_info(training_history)").fetchall()}
    if "session_comment" not in cols:
        c.execute("ALTER TABLE training_history ADD COLUMN session_comment TEXT DEFAULT ''")
    if "solo_drill_id" not in cols:
        c.execute("ALTER TABLE training_history ADD COLUMN solo_drill_id INTEGER")
    if "solo_exercise_id" not in cols:
        c.execute("ALTER TABLE training_history ADD COLUMN solo_exercise_id INTEGER")
    if "total_balls" not in cols:
        c.execute("ALTER TABLE training_history ADD COLUMN total_balls INTEGER")
    player_cols = {r[1] for r in c.execute("PRAGMA table_info(players)").fetchall()}
    if "handedness" not in player_cols:
        c.execute("ALTER TABLE players ADD COLUMN handedness TEXT DEFAULT 'right'")
    if "lang" not in player_cols:
        c.execute("ALTER TABLE players ADD COLUMN lang TEXT DEFAULT 'pl'")
    rec_cols = {r[1] for r in c.execute("PRAGMA table_info(recordings_meta)").fetchall()}
    if "drill_id" not in rec_cols:
        c.execute("ALTER TABLE recordings_meta ADD COLUMN drill_id INTEGER")
    if "exercise_id" not in rec_cols:
        c.execute("ALTER TABLE recordings_meta ADD COLUMN exercise_id INTEGER")


def _seed_drills(c):
    data = json.loads(DRILLS_DEFAULT.read_text())
    for folder in data["folders"]:
        cur = c.execute(
            "INSERT INTO drill_folders (name, description, sort_order, readonly) VALUES (?,?,?,1)",
            (folder["name"], folder.get("description", ""), folder["sort_order"])
        )
        fid = cur.lastrowid
        for drill in folder["drills"]:
            c.execute(
                "INSERT INTO drills (folder_id, name, description, youtube_id, delay_s, balls, repeat, sort_order, readonly)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (fid, drill["name"], drill.get("description", ""), drill.get("youtube_id", ""),
                 drill.get("delay_s", 0), json.dumps(drill["balls"]),
                 drill.get("repeat", 0), drill["sort_order"])
            )


# ── Scenarios ──────────────────────────────────────────────────────────────

def get_scenarios():
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT id, name, description, balls, repeat FROM scenarios ORDER BY name"
        ).fetchall()
        return [_scenario_row(r) for r in rows]


def get_scenario(id: int):
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, name, description, balls, repeat FROM scenarios WHERE id=?", (id,)
        ).fetchone()
        return _scenario_row(r) if r else None


def save_scenario(name, description, balls, repeat=1) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO scenarios (name, description, balls, repeat) VALUES (?,?,?,?)",
            (name, description, json.dumps(balls), repeat),
        )
        return cur.lastrowid


def update_scenario(id, name, description, balls, repeat):
    with sqlite3.connect(DB) as c:
        c.execute(
            "UPDATE scenarios SET name=?, description=?, balls=?, repeat=? WHERE id=?",
            (name, description, json.dumps(balls), repeat, id),
        )


def delete_scenario(id):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM scenarios WHERE id=?", (id,))


def _scenario_row(r):
    return {"id": r[0], "name": r[1], "description": r[2], "balls": json.loads(r[3]), "repeat": r[4]}


# ── Drill folders ──────────────────────────────────────────────────────────

def get_drill_tree():
    with sqlite3.connect(DB) as c:
        folders = c.execute(
            "SELECT id, name, description, sort_order, readonly FROM drill_folders ORDER BY sort_order, name"
        ).fetchall()
        result = []
        for fid, fname, fdesc, fsort, fro in folders:
            drills = c.execute(
                "SELECT id, folder_id, name, description, youtube_id, delay_s, balls, repeat, sort_order, readonly"
                " FROM drills WHERE folder_id=? ORDER BY sort_order, name",
                (fid,)
            ).fetchall()
            result.append({
                "id": fid, "name": fname, "description": fdesc,
                "sort_order": fsort, "readonly": bool(fro),
                "drills": [_drill_row(d) for d in drills],
            })
        unfiled = c.execute(
            "SELECT id, folder_id, name, description, youtube_id, delay_s, balls, repeat, sort_order, readonly"
            " FROM drills WHERE folder_id IS NULL ORDER BY sort_order, name"
        ).fetchall()
        return {"folders": result, "unfiled": [_drill_row(d) for d in unfiled]}


def create_folder(name, description="") -> int:
    with sqlite3.connect(DB) as c:
        max_sort = c.execute("SELECT COALESCE(MAX(sort_order),0) FROM drill_folders").fetchone()[0]
        cur = c.execute(
            "INSERT INTO drill_folders (name, description, sort_order, readonly) VALUES (?,?,?,0)",
            (name, description, max_sort + 1)
        )
        return cur.lastrowid


def update_folder(id, **kwargs):
    with sqlite3.connect(DB) as c:
        allowed = {"name", "description", "sort_order"}
        sets, vals = [], []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k}=?"); vals.append(v)
        if sets:
            vals.append(id)
            c.execute(f"UPDATE drill_folders SET {','.join(sets)} WHERE id=?", vals)


def delete_folder(id):
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE drills SET folder_id=NULL WHERE folder_id=?", (id,))
        c.execute("DELETE FROM drill_folders WHERE id=?", (id,))


def reorder_folders(order):
    """order: list of {id, sort_order}"""
    with sqlite3.connect(DB) as c:
        for item in order:
            c.execute("UPDATE drill_folders SET sort_order=? WHERE id=?", (item["sort_order"], item["id"]))


# ── Drills ─────────────────────────────────────────────────────────────────

def get_drill(id):
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, folder_id, name, description, youtube_id, delay_s, balls, repeat, sort_order, readonly"
            " FROM drills WHERE id=?", (id,)
        ).fetchone()
        return _drill_row(r) if r else None


def create_drill(folder_id, name, description, youtube_id, delay_s, balls, repeat) -> int:
    with sqlite3.connect(DB) as c:
        max_sort = c.execute(
            "SELECT COALESCE(MAX(sort_order),0) FROM drills WHERE folder_id=?", (folder_id,)
        ).fetchone()[0]
        cur = c.execute(
            "INSERT INTO drills (folder_id, name, description, youtube_id, delay_s, balls, repeat, sort_order, readonly)"
            " VALUES (?,?,?,?,?,?,?,?,0)",
            (folder_id, name, description, youtube_id, delay_s, json.dumps(balls), repeat, max_sort + 1)
        )
        return cur.lastrowid


def update_drill(id, **kwargs):
    with sqlite3.connect(DB) as c:
        allowed = {"name", "description", "balls", "repeat", "folder_id", "sort_order", "delay_s", "youtube_id"}
        sets, vals = [], []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k}=?")
                vals.append(json.dumps(v) if k == "balls" else v)
        if sets:
            vals.append(id)
            c.execute(f"UPDATE drills SET {','.join(sets)} WHERE id=?", vals)


def delete_drill(id):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM drills WHERE id=?", (id,))


def reorder_drills(order):
    """order: list of {id, sort_order, folder_id}"""
    with sqlite3.connect(DB) as c:
        for item in order:
            c.execute("UPDATE drills SET sort_order=?, folder_id=? WHERE id=?",
                      (item["sort_order"], item.get("folder_id"), item["id"]))


def _drill_row(r):
    return {
        "id": r[0], "folder_id": r[1], "name": r[2], "description": r[3],
        "youtube_id": r[4], "delay_s": r[5], "balls": json.loads(r[6]),
        "repeat": r[7], "sort_order": r[8], "readonly": bool(r[9]),
    }


# ── Players ───────────────────────────────────────────────────────────────

def _player_row(r):
    return {"id": r[0], "name": r[1], "created_at": r[2],
            "handedness": r[3] if len(r) > 3 else "right",
            "lang": r[4] if len(r) > 4 else "pl"}

_PLAYER_COLS = "id, name, created_at, handedness, lang"


def get_players():
    with sqlite3.connect(DB) as c:
        rows = c.execute(f"SELECT {_PLAYER_COLS} FROM players ORDER BY name").fetchall()
        return [_player_row(r) for r in rows]


def get_player(pid: int):
    with sqlite3.connect(DB) as c:
        r = c.execute(f"SELECT {_PLAYER_COLS} FROM players WHERE id=?", (pid,)).fetchone()
        return _player_row(r) if r else None


def player_name_exists(name: str, exclude_id: int | None = None) -> bool:
    with sqlite3.connect(DB) as c:
        if exclude_id:
            return c.execute("SELECT 1 FROM players WHERE name=? AND id!=?", (name, exclude_id)).fetchone() is not None
        return c.execute("SELECT 1 FROM players WHERE name=?", (name,)).fetchone() is not None


def create_player(name: str, handedness: str = "right", lang: str = "pl") -> dict:
    with sqlite3.connect(DB) as c:
        cur = c.execute("INSERT INTO players (name, handedness, lang) VALUES (?,?,?)", (name, handedness, lang))
        pid = cur.lastrowid
        r = c.execute(f"SELECT {_PLAYER_COLS} FROM players WHERE id=?", (pid,)).fetchone()
        return _player_row(r)


def update_player(pid: int, name: str | None = None, handedness: str | None = None, lang: str | None = None) -> dict | None:
    with sqlite3.connect(DB) as c:
        updates, params = [], []
        if name is not None:
            updates.append("name=?"); params.append(name)
        if handedness is not None:
            updates.append("handedness=?"); params.append(handedness)
        if lang is not None:
            updates.append("lang=?"); params.append(lang)
        if updates:
            params.append(pid)
            c.execute(f"UPDATE players SET {','.join(updates)} WHERE id=?", params)
        r = c.execute(f"SELECT {_PLAYER_COLS} FROM players WHERE id=?", (pid,)).fetchone()
        return _player_row(r) if r else None


def delete_player(pid: int) -> bool:
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM players WHERE id=?", (pid,))
        return c.total_changes > 0


# ── User Trainings ────────────────────────────────────────────────────────

def get_user_trainings():
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT id, name, description, countdown_sec, steps FROM user_trainings ORDER BY id"
        ).fetchall()
        return [{"id": r[0], "name": r[1], "description": r[2],
                 "countdown_sec": r[3], "steps": json.loads(r[4])} for r in rows]


def get_user_training(tid: int):
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, name, description, countdown_sec, steps FROM user_trainings WHERE id=?", (tid,)
        ).fetchone()
        if not r:
            return None
        return {"id": r[0], "name": r[1], "description": r[2],
                "countdown_sec": r[3], "steps": json.loads(r[4])}


def save_user_training(data: dict) -> int:
    with sqlite3.connect(DB) as c:
        if "id" in data and data["id"]:
            c.execute(
                "UPDATE user_trainings SET name=?, description=?, countdown_sec=?, steps=? WHERE id=?",
                (data["name"], data.get("description", ""), data.get("countdown_sec", 20),
                 json.dumps(data.get("steps", [])), data["id"])
            )
            return data["id"]
        else:
            cur = c.execute(
                "INSERT INTO user_trainings (name, description, countdown_sec, steps) VALUES (?,?,?,?)",
                (data["name"], data.get("description", ""), data.get("countdown_sec", 20),
                 json.dumps(data.get("steps", [])))
            )
            return cur.lastrowid


def delete_user_training(tid: int):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM user_trainings WHERE id=?", (tid,))


# ── Training History ──────────────────────────────────────────────────────

def record_training_run(training_id, player_id, elapsed_sec, status,
                        steps_completed, steps_total, steps_skipped=None, step_notes=None,
                        solo_drill_id=None, solo_exercise_id=None,
                        total_balls=None) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO training_history (training_id, player_id, elapsed_sec, status, "
            "steps_completed, steps_total, steps_skipped, step_notes, solo_drill_id, solo_exercise_id, total_balls) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (training_id or 0, player_id, elapsed_sec, status, steps_completed, steps_total,
             json.dumps(steps_skipped or []), json.dumps(step_notes or []),
             solo_drill_id, solo_exercise_id, total_balls)
        )
        return cur.lastrowid


def get_training_history(training_id=None, player_id=None, limit=None, offset=0, solo_only=False):
    with sqlite3.connect(DB) as c:
        q = ("SELECT id, training_id, player_id, started_at, elapsed_sec, status, "
             "steps_completed, steps_total, steps_skipped, step_notes, session_comment, "
             "solo_drill_id, solo_exercise_id, total_balls FROM training_history WHERE 1=1")
        params = []
        if training_id is not None:
            q += " AND training_id=?"; params.append(training_id)
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        if solo_only:
            q += " AND (solo_drill_id IS NOT NULL OR solo_exercise_id IS NOT NULL)"
        q += " ORDER BY started_at DESC"
        if limit is not None:
            q += " LIMIT ? OFFSET ?"; params.extend([limit, offset])
        rows = c.execute(q, params).fetchall()
        return [_history_row(r) for r in rows]


def get_training_history_count(training_id=None, player_id=None):
    with sqlite3.connect(DB) as c:
        q = "SELECT COUNT(*) FROM training_history WHERE 1=1"
        params = []
        if training_id is not None:
            q += " AND training_id=?"; params.append(training_id)
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        return c.execute(q, params).fetchone()[0]


def get_history_entry(hid: int):
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, training_id, player_id, started_at, elapsed_sec, status, "
            "steps_completed, steps_total, steps_skipped, step_notes, session_comment, "
            "solo_drill_id, solo_exercise_id, total_balls FROM training_history WHERE id=?", (hid,)
        ).fetchone()
        return _history_row(r) if r else None


def _history_row(r):
    return {"id": r[0], "training_id": r[1], "player_id": r[2], "started_at": r[3],
            "elapsed_sec": r[4], "status": r[5], "steps_completed": r[6],
            "steps_total": r[7], "steps_skipped": json.loads(r[8] or "[]"),
            "step_notes": json.loads(r[9] or "[]"),
            "session_comment": r[10] or "",
            "solo_drill_id": r[11], "solo_exercise_id": r[12],
            "total_balls": r[13]}


def update_session_comment(history_id: int, comment: str):
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE training_history SET session_comment=? WHERE id=?", (comment, history_id))


def delete_history_entry(hid: int) -> bool:
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM training_history WHERE id=?", (hid,))
        return c.total_changes > 0


# ── Player Stats ─────────────────────────────────────────────────────────

def get_player_stats(player_id: int) -> dict:
    from datetime import datetime, timedelta
    with sqlite3.connect(DB) as c:
        # Totals
        r = c.execute(
            "SELECT COUNT(*), SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),"
            " SUM(elapsed_sec), AVG(elapsed_sec), COALESCE(SUM(total_balls), 0)"
            " FROM training_history WHERE player_id=?", (player_id,)
        ).fetchone()
        total = r[0] or 0
        completed = r[1] or 0
        total_sec = r[2] or 0
        total_balls = r[4] or 0
        avg_sec = int(r[3] or 0)

        # 30-Day Challenge (training_id 101-130)
        p30 = c.execute(
            "SELECT COUNT(DISTINCT training_id) FROM training_history"
            " WHERE player_id=? AND status='completed' AND training_id BETWEEN 101 AND 130",
            (player_id,)
        ).fetchone()[0] or 0

        # Streak (consecutive days from today)
        days = [row[0] for row in c.execute(
            "SELECT DISTINCT date(started_at) FROM training_history"
            " WHERE player_id=? ORDER BY date(started_at) DESC", (player_id,)
        ).fetchall()]

        today = datetime.now().date()
        current_streak = 0
        longest_streak = 0
        streak = 0
        for i, d in enumerate(days):
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            expected = today - timedelta(days=i)
            if dt == expected:
                streak += 1
                current_streak = streak
            else:
                break
        # longest streak from all days
        streak = 0
        for i, d in enumerate(days):
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            if i == 0:
                streak = 1
            else:
                prev = datetime.strptime(days[i - 1], "%Y-%m-%d").date()
                streak = streak + 1 if (prev - dt).days == 1 else 1
            longest_streak = max(longest_streak, streak)

        # Weekly activity (last 8 weeks)
        cutoff = (today - timedelta(days=55)).isoformat()
        weeks_raw = c.execute(
            "SELECT strftime('%%Y-%%W', started_at) as w, COUNT(*),"
            " SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END), SUM(elapsed_sec)"
            " FROM training_history WHERE player_id=? AND date(started_at) >= ?"
            " GROUP BY w ORDER BY w", (player_id, cutoff)
        ).fetchall()

        # Build 8-week grid with labels
        weekly = []
        for i in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            wk = week_start.strftime("%Y-%W")
            label = week_start.strftime("%d %b")
            match = next((r for r in weeks_raw if r[0] == wk), None)
            weekly.append({
                "week": wk, "week_label": label,
                "sessions": match[1] if match else 0,
                "completed": match[2] if match else 0,
                "total_sec": match[3] if match else 0,
            })

    return {
        "total_sessions": total,
        "completed_sessions": completed,
        "total_time_sec": total_sec,
        "avg_duration_sec": avg_sec,
        "completion_rate": round(completed / total * 100) if total else 0,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "program30_completed": p30,
        "total_balls": total_balls,
        "weekly_activity": weekly,
    }


# ── Favorites ─────────────────────────────────────────────────────────────

def get_favorites(player_id: int):
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT id, player_id, item_type, item_id, created_at FROM favorites WHERE player_id=? ORDER BY created_at DESC",
            (player_id,)
        ).fetchall()
        return [{"id": r[0], "player_id": r[1], "item_type": r[2], "item_id": r[3], "created_at": r[4]} for r in rows]


def add_favorite(player_id: int, item_type: str, item_id: int) -> dict:
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT OR IGNORE INTO favorites (player_id, item_type, item_id) VALUES (?,?,?)",
            (player_id, item_type, item_id)
        )
        r = c.execute(
            "SELECT id, player_id, item_type, item_id, created_at FROM favorites WHERE player_id=? AND item_type=? AND item_id=?",
            (player_id, item_type, item_id)
        ).fetchone()
        return {"id": r[0], "player_id": r[1], "item_type": r[2], "item_id": r[3], "created_at": r[4]}


def remove_favorite(player_id: int, item_type: str, item_id: int):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM favorites WHERE player_id=? AND item_type=? AND item_id=?",
                  (player_id, item_type, item_id))


# ── Recordings Meta ───────────────────────────────────────────────────────

def save_recording_meta(player_id, training_id, training_name, step_idx,
                        step_name, filename, duration_sec, size_bytes,
                        drill_id=None, exercise_id=None):
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT INTO recordings_meta (player_id, training_id, training_name, step_idx, "
            "step_name, filename, duration_sec, size_bytes, drill_id, exercise_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (player_id, training_id, training_name, step_idx, step_name,
             filename, duration_sec, size_bytes, drill_id, exercise_id)
        )


def get_recordings_meta(player_id=None):
    with sqlite3.connect(DB) as c:
        q = ("SELECT id, player_id, training_id, training_name, step_idx, step_name,"
             " filename, started_at, duration_sec, size_bytes, drill_id, exercise_id"
             " FROM recordings_meta")
        params = []
        if player_id is not None:
            q += " WHERE player_id=?"; params.append(player_id)
        q += " ORDER BY started_at DESC"
        rows = c.execute(q, params).fetchall()
        return [{"id": r[0], "player_id": r[1], "training_id": r[2], "training_name": r[3],
                 "step_idx": r[4], "step_name": r[5], "filename": r[6], "started_at": r[7],
                 "duration_sec": r[8], "size_bytes": r[9], "drill_id": r[10], "exercise_id": r[11]}
                for r in rows]


def get_comparable_recordings(training_id: int | None = None, step_idx: int | None = None,
                              drill_id: int | None = None, exercise_id: int | None = None,
                              exclude_filename: str | None = None):
    """Get comparable recordings — by drill_id/exercise_id or fallback to training_id+step_idx."""
    with sqlite3.connect(DB) as c:
        q = ("SELECT id, player_id, training_id, training_name, step_idx, step_name,"
             " filename, started_at, duration_sec, size_bytes, drill_id, exercise_id"
             " FROM recordings_meta WHERE 1=1")
        params = []
        if drill_id is not None:
            q += " AND drill_id=?"; params.append(drill_id)
        elif exercise_id is not None:
            q += " AND exercise_id=?"; params.append(exercise_id)
        elif training_id is not None and step_idx is not None:
            q += " AND training_id=? AND step_idx=?"; params.extend([training_id, step_idx])
        if exclude_filename:
            q += " AND filename != ?"; params.append(exclude_filename)
        q += " ORDER BY started_at DESC"
        rows = c.execute(q, params).fetchall()
        return [{"id": r[0], "player_id": r[1], "training_id": r[2], "training_name": r[3],
                 "step_idx": r[4], "step_name": r[5], "filename": r[6], "started_at": r[7],
                 "duration_sec": r[8], "size_bytes": r[9], "drill_id": r[10], "exercise_id": r[11]}
                for r in rows]


def delete_recording_meta(filename: str):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM recordings_meta WHERE filename=?", (filename,))


def get_recordings_stats(player_id: int | None = None, history_id: int | None = None) -> dict:
    """Return count + total_size for recordings matching criteria."""
    with sqlite3.connect(DB) as c:
        if history_id is not None:
            h = get_history_entry(history_id)
            if not h:
                return {"count": 0, "total_size": 0, "filenames": []}
            filenames = _get_session_filenames(c, h)
            if not filenames:
                return {"count": 0, "total_size": 0, "filenames": []}
            placeholders = ",".join("?" * len(filenames))
            r = c.execute(
                f"SELECT COUNT(*), COALESCE(SUM(size_bytes),0) FROM recordings_meta WHERE filename IN ({placeholders})",
                filenames
            ).fetchone()
            return {"count": r[0], "total_size": r[1], "filenames": filenames}
        q = "SELECT COUNT(*), COALESCE(SUM(size_bytes),0) FROM recordings_meta WHERE 1=1"
        params = []
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        r = c.execute(q, params).fetchone()
        fq = "SELECT filename FROM recordings_meta WHERE 1=1"
        if player_id is not None:
            fq += " AND player_id=?"; params_f = [player_id]
        else:
            params_f = []
        filenames = [row[0] for row in c.execute(fq, params_f).fetchall()]
        return {"count": r[0], "total_size": r[1], "filenames": filenames}


def _get_session_filenames(c, h: dict) -> list[str]:
    """Get recording filenames matching a history session by player_id + time window."""
    if not h.get("player_id"):
        return []
    q = ("SELECT filename FROM recordings_meta"
         " WHERE player_id=? AND started_at >= ? AND started_at <= datetime(?, '+' || ? || ' seconds')")
    rows = c.execute(q, (h["player_id"], h["started_at"], h["started_at"],
                         h["elapsed_sec"] + 60)).fetchall()
    return [r[0] for r in rows]


def delete_player_cascade(pid: int):
    """Delete player + all associated data (history, recordings meta, favorites, voice notes, landings)."""
    with sqlite3.connect(DB) as c:
        filenames = [r[0] for r in c.execute(
            "SELECT filename FROM recordings_meta WHERE player_id=?", (pid,)
        ).fetchall()]
        voice_files = [r[0] for r in c.execute(
            "SELECT filename FROM voice_notes WHERE player_id=?", (pid,)
        ).fetchall()]
        c.execute("DELETE FROM recordings_meta WHERE player_id=?", (pid,))
        c.execute("DELETE FROM training_history WHERE player_id=?", (pid,))
        c.execute("DELETE FROM voice_notes WHERE player_id=?", (pid,))
        c.execute("DELETE FROM ball_landings WHERE player_id=?", (pid,))
        c.execute("DELETE FROM favorites WHERE player_id=?", (pid,))
        c.execute("DELETE FROM players WHERE id=?", (pid,))
    return filenames, voice_files


def delete_history_cascade(hid: int) -> list[str]:
    """Delete history entry + associated recording metadata. Returns filenames to delete."""
    h = get_history_entry(hid)
    if not h:
        return []
    with sqlite3.connect(DB) as c:
        filenames = _get_session_filenames(c, h)
        if filenames:
            placeholders = ",".join("?" * len(filenames))
            c.execute(f"DELETE FROM recordings_meta WHERE filename IN ({placeholders})", filenames)
        c.execute("DELETE FROM training_history WHERE id=?", (hid,))
    return filenames


# ── Voice notes ───────────────────────────────────────────────────────────────

def save_voice_note(player_id: int, filename: str, step_idx: int = 0,
                    training_history_id: int | None = None, duration_ms: int = 0) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO voice_notes (player_id, training_history_id, step_idx, filename, duration_ms)"
            " VALUES (?,?,?,?,?)",
            (player_id, training_history_id, step_idx, filename, duration_ms)
        )
        return cur.lastrowid


def get_voice_notes(player_id: int | None = None, training_history_id: int | None = None) -> list:
    with sqlite3.connect(DB) as c:
        q = "SELECT id, player_id, training_history_id, step_idx, filename, started_at, duration_ms FROM voice_notes WHERE 1=1"
        params = []
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        if training_history_id is not None:
            q += " AND training_history_id=?"; params.append(training_history_id)
        q += " ORDER BY started_at DESC"
        return [_voice_note_row(r) for r in c.execute(q, params).fetchall()]


def get_voice_note(nid: int) -> dict | None:
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, player_id, training_history_id, step_idx, filename, started_at, duration_ms"
            " FROM voice_notes WHERE id=?", (nid,)
        ).fetchone()
        return _voice_note_row(r) if r else None


def delete_voice_note(nid: int):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM voice_notes WHERE id=?", (nid,))


# ── Ball exploration ─────────────────────────────────────────────────────────

def save_ball_exploration(data: dict) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO ball_exploration (player_id, firmware, top_speed, bot_speed, oscillation, height, rotation, wait_ms,"
            " cal_top, cal_bot, cal_osc, cal_h, cal_rot, bounce1_x, bounce1_y, bounce2_x, bounce2_y,"
            " spin, arc, perceived_speed, useful_for, rating, comment) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.get("player_id"), data.get("firmware"),
             data.get("top_speed"), data.get("bot_speed"), data.get("oscillation"),
             data.get("height"), data.get("rotation"), data.get("wait_ms"),
             data.get("cal_top"), data.get("cal_bot"), data.get("cal_osc"),
             data.get("cal_h"), data.get("cal_rot"),
             data.get("bounce1_x"), data.get("bounce1_y"),
             data.get("bounce2_x"), data.get("bounce2_y"),
             data.get("spin"), data.get("arc"), data.get("perceived_speed"),
             data.get("useful_for"), data.get("rating"), data.get("comment", ""))
        )
        return cur.lastrowid


def get_ball_explorations(player_id: int | None = None, limit: int = 50) -> list:
    with sqlite3.connect(DB) as c:
        q = ("SELECT id, player_id, firmware, top_speed, bot_speed, oscillation, height, rotation, wait_ms,"
             " cal_top, cal_bot, cal_osc, cal_h, cal_rot, bounce1_x, bounce1_y, bounce2_x, bounce2_y,"
             " spin, arc, perceived_speed, useful_for, rating, comment, created_at FROM ball_exploration WHERE 1=1")
        params = []
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        q += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cols = ["id", "player_id", "firmware", "top_speed", "bot_speed", "oscillation", "height", "rotation", "wait_ms",
                "cal_top", "cal_bot", "cal_osc", "cal_h", "cal_rot", "bounce1_x", "bounce1_y", "bounce2_x", "bounce2_y",
                "spin", "arc", "perceived_speed", "useful_for", "rating", "comment", "created_at"]
        return [dict(zip(cols, r)) for r in c.execute(q, params).fetchall()]


def delete_ball_exploration(eid: int):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM ball_exploration WHERE id=?", (eid,))


def _voice_note_row(r) -> dict:
    return {"id": r[0], "player_id": r[1], "training_history_id": r[2],
            "step_idx": r[3], "filename": r[4], "started_at": r[5], "duration_ms": r[6]}


# ── Ball landings ─────────────────────────────────────────────────────────────

def save_ball_landing(player_id: int, drill_id: int, x: float, y: float) -> int:
    with sqlite3.connect(DB) as c:
        cur = c.execute(
            "INSERT INTO ball_landings (player_id, drill_id, x, y) VALUES (?,?,?,?)",
            (player_id, drill_id, x, y)
        )
        return cur.lastrowid


def get_ball_landings(drill_id: int, player_id: int | None = None) -> list:
    with sqlite3.connect(DB) as c:
        q = "SELECT id, player_id, drill_id, x, y, created_at FROM ball_landings WHERE drill_id=?"
        params = [drill_id]
        if player_id is not None:
            q += " AND player_id=?"
            params.append(player_id)
        q += " ORDER BY created_at DESC"
        rows = c.execute(q, params).fetchall()
        return [{"id": r[0], "player_id": r[1], "drill_id": r[2], "x": r[3], "y": r[4], "created_at": r[5]}
                for r in rows]


def delete_ball_landing(lid: int):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM ball_landings WHERE id=?", (lid,))
