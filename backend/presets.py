import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "presets.db"


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_presets():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS presets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                is_default  INTEGER NOT NULL DEFAULT 0,
                top_speed   INTEGER NOT NULL,
                bot_speed   INTEGER NOT NULL,
                oscillation INTEGER NOT NULL,
                height      INTEGER NOT NULL,
                rotation    INTEGER NOT NULL,
                wait_ms     INTEGER NOT NULL
            )
        """)


def get_presets() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM presets ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def save_preset(name: str, data: dict, is_default: bool = False) -> int:
    with _conn() as c:
        if is_default:
            c.execute("UPDATE presets SET is_default=0")
        cur = c.execute(
            "INSERT INTO presets (name, is_default, top_speed, bot_speed, oscillation, height, rotation, wait_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, int(is_default), data["top_speed"], data["bot_speed"],
             data["oscillation"], data["height"], data["rotation"], data["wait_ms"]),
        )
        return cur.lastrowid


def set_default(preset_id: int):
    with _conn() as c:
        c.execute("UPDATE presets SET is_default=0")
        c.execute("UPDATE presets SET is_default=1 WHERE id=?", (preset_id,))


def delete_preset(preset_id: int):
    with _conn() as c:
        c.execute("DELETE FROM presets WHERE id=?", (preset_id,))


def get_default_preset() -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM presets WHERE is_default=1 LIMIT 1").fetchone()
    return dict(row) if row else None
