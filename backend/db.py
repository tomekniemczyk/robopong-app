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
        count = c.execute("SELECT COUNT(*) FROM drill_folders").fetchone()[0]
        if count == 0 and DRILLS_DEFAULT.exists():
            _seed_drills(c)


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

def get_players():
    with sqlite3.connect(DB) as c:
        rows = c.execute("SELECT id, name, created_at FROM players ORDER BY name").fetchall()
        return [{"id": r[0], "name": r[1], "created_at": r[2]} for r in rows]


def get_player(pid: int):
    with sqlite3.connect(DB) as c:
        r = c.execute("SELECT id, name, created_at FROM players WHERE id=?", (pid,)).fetchone()
        return {"id": r[0], "name": r[1], "created_at": r[2]} if r else None


def create_player(name: str) -> dict:
    with sqlite3.connect(DB) as c:
        cur = c.execute("INSERT INTO players (name) VALUES (?)", (name,))
        pid = cur.lastrowid
        r = c.execute("SELECT id, name, created_at FROM players WHERE id=?", (pid,)).fetchone()
        return {"id": r[0], "name": r[1], "created_at": r[2]}


def update_player(pid: int, name: str) -> dict | None:
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE players SET name=? WHERE id=?", (name, pid))
        r = c.execute("SELECT id, name, created_at FROM players WHERE id=?", (pid,)).fetchone()
        return {"id": r[0], "name": r[1], "created_at": r[2]} if r else None


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
                        steps_completed, steps_total, steps_skipped=None, step_notes=None):
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT INTO training_history (training_id, player_id, elapsed_sec, status, "
            "steps_completed, steps_total, steps_skipped, step_notes) VALUES (?,?,?,?,?,?,?,?)",
            (training_id, player_id, elapsed_sec, status, steps_completed, steps_total,
             json.dumps(steps_skipped or []), json.dumps(step_notes or []))
        )


def get_training_history(training_id=None, player_id=None):
    with sqlite3.connect(DB) as c:
        q = "SELECT id, training_id, player_id, started_at, elapsed_sec, status, steps_completed, steps_total, steps_skipped, step_notes, session_comment FROM training_history WHERE 1=1"
        params = []
        if training_id is not None:
            q += " AND training_id=?"; params.append(training_id)
        if player_id is not None:
            q += " AND player_id=?"; params.append(player_id)
        q += " ORDER BY started_at DESC"
        rows = c.execute(q, params).fetchall()
        return [{"id": r[0], "training_id": r[1], "player_id": r[2], "started_at": r[3],
                 "elapsed_sec": r[4], "status": r[5], "steps_completed": r[6],
                 "steps_total": r[7], "steps_skipped": json.loads(r[8] or "[]"),
                 "step_notes": json.loads(r[9] or "[]"),
                 "session_comment": r[10] or ""} for r in rows]


def update_session_comment(history_id: int, comment: str):
    with sqlite3.connect(DB) as c:
        c.execute("UPDATE training_history SET session_comment=? WHERE id=?", (comment, history_id))


# ── Recordings Meta ───────────────────────────────────────────────────────

def save_recording_meta(player_id, training_id, training_name, step_idx,
                        step_name, filename, duration_sec, size_bytes):
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT INTO recordings_meta (player_id, training_id, training_name, step_idx, "
            "step_name, filename, duration_sec, size_bytes) VALUES (?,?,?,?,?,?,?,?)",
            (player_id, training_id, training_name, step_idx, step_name,
             filename, duration_sec, size_bytes)
        )


def get_recordings_meta(player_id=None):
    with sqlite3.connect(DB) as c:
        q = "SELECT id, player_id, training_id, training_name, step_idx, step_name, filename, started_at, duration_sec, size_bytes FROM recordings_meta"
        params = []
        if player_id is not None:
            q += " WHERE player_id=?"; params.append(player_id)
        q += " ORDER BY started_at DESC"
        rows = c.execute(q, params).fetchall()
        return [{"id": r[0], "player_id": r[1], "training_id": r[2], "training_name": r[3],
                 "step_idx": r[4], "step_name": r[5], "filename": r[6], "started_at": r[7],
                 "duration_sec": r[8], "size_bytes": r[9]} for r in rows]


def delete_recording_meta(filename: str):
    with sqlite3.connect(DB) as c:
        c.execute("DELETE FROM recordings_meta WHERE filename=?", (filename,))
