import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent / "robopong.db"


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


def get_scenarios():
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT id, name, description, balls, repeat FROM scenarios ORDER BY name"
        ).fetchall()
        return [_row(r) for r in rows]


def get_scenario(id: int):
    with sqlite3.connect(DB) as c:
        r = c.execute(
            "SELECT id, name, description, balls, repeat FROM scenarios WHERE id=?", (id,)
        ).fetchone()
        return _row(r) if r else None


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


def _row(r):
    return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "balls": json.loads(r[3]),
        "repeat": r[4],
    }
