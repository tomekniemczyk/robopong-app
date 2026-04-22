"""
Match journal — opponents CRUD + match_journal CRUD + H2H stats.
"""

import json
import sqlite3
import db as _db


# ── Helpers ───────────────────────────────────────────────────────────────────

def _j(v, default="[]"):
    """Parse JSON field; return default on error."""
    if not v:
        return json.loads(default)
    try:
        return json.loads(v)
    except Exception:
        return json.loads(default)


def _opponent_row(r):
    if not r:
        return None
    return {
        "id": r[0], "created_by_player_id": r[1], "name": r[2],
        "handedness": r[3], "grip": r[4], "style": r[5],
        "rubber_fh": r[6], "rubber_bh": r[7], "rating_level": r[8],
        "general_notes": r[9], "created_at": r[10], "updated_at": r[11],
    }


def _journal_row(r):
    if not r:
        return None
    return {
        "id": r[0], "player_id": r[1], "opponent_id": r[2],
        "match_date": r[3], "match_type": r[4], "tournament_name": r[5],
        "duration_min": r[6], "sets_me": r[7], "sets_op": r[8],
        "set_scores": _j(r[9]), "result": r[10],
        "what_worked": _j(r[11]), "what_failed": _j(r[12]),
        "mistakes": _j(r[13]), "opponent_tactics": _j(r[14]),
        "next_plan": _j(r[15]),
        "self_technical": r[16], "self_tactical": r[17],
        "self_mental": r[18], "self_physical": r[19],
        "opponent_difficulty": r[20],
        "free_notes": r[21] or "",
        "video_paths": _j(r[22]), "recording_ids": _j(r[23]),
        "created_at": r[24], "updated_at": r[25],
    }


_OPPONENT_COLS = "id, created_by_player_id, name, handedness, grip, style, rubber_fh, rubber_bh, rating_level, general_notes, created_at, updated_at"
_JOURNAL_COLS = ("id, player_id, opponent_id, match_date, match_type, tournament_name, duration_min, "
                 "sets_me, sets_op, set_scores, result, what_worked, what_failed, mistakes, "
                 "opponent_tactics, next_plan, self_technical, self_tactical, self_mental, "
                 "self_physical, opponent_difficulty, free_notes, video_paths, recording_ids, "
                 "created_at, updated_at")


# ── Opponents ─────────────────────────────────────────────────────────────────

def list_opponents(player_id: int) -> list:
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(
            f"SELECT {_OPPONENT_COLS} FROM opponents WHERE created_by_player_id=? ORDER BY name",
            (player_id,)
        ).fetchall()
        result = [_opponent_row(r) for r in rows]
        for opp in result:
            opp["h2h"] = _h2h_quick(c, player_id, opp["id"])
        return result


def get_opponent(player_id: int, opponent_id: int) -> dict | None:
    with sqlite3.connect(_db.DB) as c:
        r = c.execute(
            f"SELECT {_OPPONENT_COLS} FROM opponents WHERE id=? AND created_by_player_id=?",
            (opponent_id, player_id)
        ).fetchone()
        if not r:
            return None
        opp = _opponent_row(r)
        opp["h2h"] = _h2h_full(c, player_id, opponent_id)
        return opp


def create_opponent(player_id: int, data: dict) -> dict:
    with sqlite3.connect(_db.DB) as c:
        cur = c.execute(
            "INSERT INTO opponents (created_by_player_id, name, handedness, grip, style, "
            "rubber_fh, rubber_bh, rating_level, general_notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (player_id, data["name"], data.get("handedness", "right"),
             data.get("grip", "shakehand"), data.get("style", "allround"),
             data.get("rubber_fh", ""), data.get("rubber_bh", ""),
             data.get("rating_level", ""), data.get("general_notes", ""))
        )
        r = c.execute(f"SELECT {_OPPONENT_COLS} FROM opponents WHERE id=?", (cur.lastrowid,)).fetchone()
    opp = _opponent_row(r)
    opp["h2h"] = {"wins": 0, "losses": 0, "total": 0, "last_matches": []}
    return opp


def update_opponent(player_id: int, opponent_id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if k in (
        "name", "handedness", "grip", "style", "rubber_fh",
        "rubber_bh", "rating_level", "general_notes"
    )}
    if not fields:
        return get_opponent(player_id, opponent_id)
    sets = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values()) + [opponent_id, player_id]
    with sqlite3.connect(_db.DB) as c:
        c.execute(f"UPDATE opponents SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=? AND created_by_player_id=?", vals)
    return get_opponent(player_id, opponent_id)


def delete_opponent(player_id: int, opponent_id: int):
    with sqlite3.connect(_db.DB) as c:
        c.execute("DELETE FROM match_journal WHERE player_id=? AND opponent_id=?", (player_id, opponent_id))
        c.execute("DELETE FROM opponents WHERE id=? AND created_by_player_id=?", (opponent_id, player_id))


def search_opponents(player_id: int, q: str) -> list:
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(
            f"SELECT {_OPPONENT_COLS} FROM opponents WHERE created_by_player_id=? AND name LIKE ? ORDER BY name LIMIT 10",
            (player_id, f"%{q}%")
        ).fetchall()
        return [_opponent_row(r) for r in rows]


# ── H2H helpers ───────────────────────────────────────────────────────────────

def _h2h_quick(c, player_id: int, opponent_id: int) -> dict:
    rows = c.execute(
        "SELECT result, match_date, sets_me, sets_op FROM match_journal "
        "WHERE player_id=? AND opponent_id=? ORDER BY match_date DESC",
        (player_id, opponent_id)
    ).fetchall()
    wins = sum(1 for r in rows if r[0] == "win")
    losses = sum(1 for r in rows if r[0] == "loss")
    return {
        "wins": wins, "losses": losses, "total": len(rows),
        "last_matches": [{"result": r[0], "date": r[1], "sets_me": r[2], "sets_op": r[3]} for r in rows[:5]],
    }


def _h2h_full(c, player_id: int, opponent_id: int) -> dict:
    rows = c.execute(
        "SELECT id, result, match_date, sets_me, sets_op, what_worked, what_failed, mistakes, opponent_tactics "
        "FROM match_journal WHERE player_id=? AND opponent_id=? ORDER BY match_date DESC",
        (player_id, opponent_id)
    ).fetchall()
    wins = sum(1 for r in rows if r[1] == "win")
    losses = sum(1 for r in rows if r[1] == "loss")

    # Aggregate patterns
    worked_counts: dict = {}
    failed_counts: dict = {}
    mistake_counts: dict = {}
    tactics_counts: dict = {}

    for r in rows:
        for item in _j(r[5]):
            worked_counts[item] = worked_counts.get(item, 0) + 1
        for item in _j(r[6]):
            failed_counts[item] = failed_counts.get(item, 0) + 1
        for m in _j(r[7]):
            desc = m.get("description", "") if isinstance(m, dict) else str(m)
            mistake_counts[desc] = mistake_counts.get(desc, 0) + 1
        for t in _j(r[8]):
            pattern = t.get("pattern", "") if isinstance(t, dict) else str(t)
            tactics_counts[pattern] = tactics_counts.get(pattern, 0) + 1

    def top(d, n=5):
        return sorted([{"text": k, "count": v} for k, v in d.items()], key=lambda x: -x["count"])[:n]

    # Streak
    streak = 0
    if rows:
        last_result = rows[0][1]
        for r in rows:
            if r[1] == last_result:
                streak += 1
            else:
                break

    return {
        "wins": wins, "losses": losses, "total": len(rows),
        "streak": {"result": last_result, "count": streak} if rows else None,
        "last_matches": [{"id": r[0], "result": r[1], "date": r[2], "sets_me": r[3], "sets_op": r[4]} for r in rows[:10]],
        "top_worked": top(worked_counts),
        "top_failed": top(failed_counts),
        "top_mistakes": top(mistake_counts),
        "top_tactics": top(tactics_counts),
    }


def get_h2h(player_id: int, opponent_id: int) -> dict:
    with sqlite3.connect(_db.DB) as c:
        return _h2h_full(c, player_id, opponent_id)


# ── Match journal CRUD ────────────────────────────────────────────────────────

def list_matches(player_id: int, opponent_id: int | None = None,
                 result: str | None = None, match_type: str | None = None,
                 from_date: str | None = None, to_date: str | None = None,
                 limit: int = 50, offset: int = 0) -> list:
    q = f"SELECT {_JOURNAL_COLS} FROM match_journal WHERE player_id=?"
    params: list = [player_id]
    if opponent_id:
        q += " AND opponent_id=?"; params.append(opponent_id)
    if result:
        q += " AND result=?"; params.append(result)
    if match_type:
        q += " AND match_type=?"; params.append(match_type)
    if from_date:
        q += " AND match_date>=?"; params.append(from_date)
    if to_date:
        q += " AND match_date<=?"; params.append(to_date)
    q += " ORDER BY match_date DESC, id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(q, params).fetchall()
        entries = [_journal_row(r) for r in rows]
        # Attach opponent name
        opp_cache: dict = {}
        for e in entries:
            oid = e["opponent_id"]
            if oid not in opp_cache:
                orow = c.execute("SELECT name FROM opponents WHERE id=?", (oid,)).fetchone()
                opp_cache[oid] = orow[0] if orow else f"#{oid}"
            e["opponent_name"] = opp_cache[oid]
        return entries


def get_match(player_id: int, match_id: int) -> dict | None:
    with sqlite3.connect(_db.DB) as c:
        r = c.execute(
            f"SELECT {_JOURNAL_COLS} FROM match_journal WHERE id=? AND player_id=?",
            (match_id, player_id)
        ).fetchone()
        if not r:
            return None
        entry = _journal_row(r)
        orow = c.execute("SELECT name FROM opponents WHERE id=?", (entry["opponent_id"],)).fetchone()
        entry["opponent_name"] = orow[0] if orow else f"#{entry['opponent_id']}"
        return entry


def _compute_result(sets_me, sets_op) -> str:
    if sets_me is None or sets_op is None:
        return ""
    return "win" if sets_me > sets_op else "loss"


def create_match(player_id: int, data: dict) -> dict:
    sets_me = data.get("sets_me")
    sets_op = data.get("sets_op")
    result = _compute_result(sets_me, sets_op)
    with sqlite3.connect(_db.DB) as c:
        cur = c.execute(
            "INSERT INTO match_journal (player_id, opponent_id, match_date, match_type, tournament_name, "
            "duration_min, sets_me, sets_op, set_scores, result, what_worked, what_failed, mistakes, "
            "opponent_tactics, next_plan, self_technical, self_tactical, self_mental, self_physical, "
            "opponent_difficulty, free_notes, video_paths, recording_ids) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (player_id, data["opponent_id"], data["match_date"],
             data.get("match_type", "sparing"), data.get("tournament_name", ""),
             data.get("duration_min"), sets_me, sets_op,
             json.dumps(data.get("set_scores", [])), result,
             json.dumps(data.get("what_worked", [])), json.dumps(data.get("what_failed", [])),
             json.dumps(data.get("mistakes", [])), json.dumps(data.get("opponent_tactics", [])),
             json.dumps(data.get("next_plan", [])),
             data.get("self_technical"), data.get("self_tactical"),
             data.get("self_mental"), data.get("self_physical"),
             data.get("opponent_difficulty"),
             data.get("free_notes", ""),
             json.dumps(data.get("video_paths", [])), json.dumps(data.get("recording_ids", [])))
        )
        mid = cur.lastrowid
        r = c.execute(f"SELECT {_JOURNAL_COLS} FROM match_journal WHERE id=?", (mid,)).fetchone()
        entry = _journal_row(r)
        orow = c.execute("SELECT name FROM opponents WHERE id=?", (entry["opponent_id"],)).fetchone()
        entry["opponent_name"] = orow[0] if orow else f"#{entry['opponent_id']}"
        return entry


def update_match(player_id: int, match_id: int, data: dict) -> dict | None:
    existing = get_match(player_id, match_id)
    if not existing:
        return None
    sets_me = data.get("sets_me", existing["sets_me"])
    sets_op = data.get("sets_op", existing["sets_op"])
    result = _compute_result(sets_me, sets_op)

    json_fields = {"set_scores", "what_worked", "what_failed", "mistakes", "opponent_tactics", "next_plan", "video_paths", "recording_ids"}
    scalar_fields = {
        "opponent_id", "match_date", "match_type", "tournament_name", "duration_min",
        "sets_me", "sets_op", "self_technical", "self_tactical",
        "self_mental", "self_physical", "opponent_difficulty", "free_notes"
    }
    sets_clause = []
    vals = []
    for k in scalar_fields:
        if k in data:
            sets_clause.append(f"{k}=?")
            vals.append(data[k])
    for k in json_fields:
        if k in data:
            sets_clause.append(f"{k}=?")
            vals.append(json.dumps(data[k]))
    sets_clause.append("result=?"); vals.append(result)
    sets_clause.append("sets_me=?"); vals.append(sets_me)
    sets_clause.append("sets_op=?"); vals.append(sets_op)
    sets_clause.append("updated_at=CURRENT_TIMESTAMP")

    with sqlite3.connect(_db.DB) as c:
        c.execute(
            f"UPDATE match_journal SET {', '.join(sets_clause)} WHERE id=? AND player_id=?",
            vals + [match_id, player_id]
        )
    return get_match(player_id, match_id)


def delete_match(player_id: int, match_id: int):
    with sqlite3.connect(_db.DB) as c:
        c.execute("DELETE FROM match_journal WHERE id=? AND player_id=?", (match_id, player_id))


def duplicate_match(player_id: int, match_id: int) -> dict | None:
    """Clone match as template for a rematch — clears date and result, keeps opponent."""
    src = get_match(player_id, match_id)
    if not src:
        return None
    data = {k: src[k] for k in src if k not in ("id", "created_at", "updated_at", "opponent_name")}
    data["match_date"] = ""
    data["sets_me"] = None; data["sets_op"] = None; data["set_scores"] = []
    data["result"] = ""
    data["what_worked"] = []; data["what_failed"] = []; data["mistakes"] = []
    data["free_notes"] = ""
    # Carry over next_plan items as starting point
    return create_match(player_id, data)


# ── Audit / stats ─────────────────────────────────────────────────────────────

def get_journal_stats(player_id: int) -> dict:
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(
            "SELECT result, match_date, opponent_id FROM match_journal WHERE player_id=? ORDER BY match_date DESC",
            (player_id,)
        ).fetchall()
        if not rows:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "monthly": [], "opponents_with_issues": []}

        wins = sum(1 for r in rows if r[0] == "win")
        losses = sum(1 for r in rows if r[0] == "loss")

        monthly: dict = {}
        for r in rows:
            month = r[1][:7] if r[1] else "?"
            if month not in monthly:
                monthly[month] = {"wins": 0, "losses": 0}
            if r[0] == "win":
                monthly[month]["wins"] += 1
            elif r[0] == "loss":
                monthly[month]["losses"] += 1
        monthly_list = [{"month": k, **v} for k, v in sorted(monthly.items(), reverse=True)][:12]

        # Opponents with negative W-L
        opp_records: dict = {}
        for r in rows:
            oid = r[2]
            if oid not in opp_records:
                opp_records[oid] = {"wins": 0, "losses": 0}
            if r[0] == "win":
                opp_records[oid]["wins"] += 1
            elif r[0] == "loss":
                opp_records[oid]["losses"] += 1

        issues = []
        for oid, rec in opp_records.items():
            total = rec["wins"] + rec["losses"]
            rec["total"] = total
            if total >= 3 and rec["losses"] > rec["wins"]:
                    orow = c.execute("SELECT name FROM opponents WHERE id=?", (oid,)).fetchone()
                    issues.append({
                        "opponent_id": oid,
                        "opponent_name": orow[0] if orow else f"#{oid}",
                        **rec,
                    })

        return {
            "total": len(rows),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(rows) * 100) if rows else 0,
            "monthly": monthly_list,
            "opponents_with_issues": sorted(issues, key=lambda x: x["losses"] - x["wins"], reverse=True),
        }


def get_journal_audit(player_id: int, last_n: int = 20) -> dict:
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(
            "SELECT mistakes, what_failed, what_worked FROM match_journal "
            "WHERE player_id=? ORDER BY match_date DESC, id DESC LIMIT ?",
            (player_id, last_n)
        ).fetchall()

    mistake_counts: dict = {}
    failed_counts: dict = {}
    worked_counts: dict = {}

    for r in rows:
        for m in _j(r[0]):
            desc = m.get("description", "") if isinstance(m, dict) else str(m)
            if desc:
                mistake_counts[desc] = mistake_counts.get(desc, 0) + 1
        for item in _j(r[1]):
            if item:
                failed_counts[item] = failed_counts.get(item, 0) + 1
        for item in _j(r[2]):
            if item:
                worked_counts[item] = worked_counts.get(item, 0) + 1

    def ranked(d, n=10):
        return sorted([{"text": k, "count": v} for k, v in d.items()], key=lambda x: -x["count"])[:n]

    return {
        "analyzed_matches": len(rows),
        "top_mistakes": ranked(mistake_counts),
        "top_failed": ranked(failed_counts),
        "top_worked": ranked(worked_counts),
    }


def export_journal(player_id: int) -> list:
    with sqlite3.connect(_db.DB) as c:
        rows = c.execute(
            f"SELECT {_JOURNAL_COLS} FROM match_journal WHERE player_id=? ORDER BY match_date DESC",
            (player_id,)
        ).fetchall()
        entries = [_journal_row(r) for r in rows]
        opp_cache: dict = {}
        for e in entries:
            oid = e["opponent_id"]
            if oid not in opp_cache:
                orow = c.execute("SELECT name FROM opponents WHERE id=?", (oid,)).fetchone()
                opp_cache[oid] = orow[0] if orow else f"#{oid}"
            e["opponent_name"] = opp_cache[oid]
        return entries
