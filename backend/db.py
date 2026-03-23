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
