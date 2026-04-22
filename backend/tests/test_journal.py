"""Integration tests for match journal API."""

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_player(client, name="Tomek"):
    r = client.post("/api/players", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def make_opponent(client, pid, name="Jan Kowalski"):
    r = client.post(f"/api/players/{pid}/opponents", json={"name": name})
    assert r.status_code == 201
    return r.json()["id"]


def make_match(client, pid, oid, date="2026-04-20", sets_me=3, sets_op=1):
    r = client.post(f"/api/players/{pid}/journal", json={
        "opponent_id": oid, "match_date": date,
        "sets_me": sets_me, "sets_op": sets_op,
        "what_worked": ["krótki serwis"], "what_failed": ["BH push"],
        "mistakes": [{"category": "taktyczny", "description": "za wolno kończył"}],
        "opponent_tactics": [{"pattern": "push na BH", "frequency": "często"}],
        "next_plan": [{"text": "Praca nad BH top", "done": False}],
        "self_technical": 4, "self_tactical": 3, "self_mental": 4, "self_physical": 5,
        "opponent_difficulty": 3,
    })
    assert r.status_code == 201
    return r.json()["id"]


# ── Opponents ─────────────────────────────────────────────────────────────────

def test_create_opponent(client):
    pid = make_player(client)
    r = client.post(f"/api/players/{pid}/opponents", json={"name": "Jan Nowak", "style": "attacker"})
    assert r.status_code == 201
    assert r.json()["name"] == "Jan Nowak"
    assert r.json()["style"] == "attacker"
    assert r.json()["h2h"]["total"] == 0


def test_create_opponent_missing_name(client):
    pid = make_player(client)
    r = client.post(f"/api/players/{pid}/opponents", json={"style": "attacker"})
    assert r.status_code == 400


def test_list_opponents_empty(client):
    pid = make_player(client)
    r = client.get(f"/api/players/{pid}/opponents")
    assert r.status_code == 200
    assert r.json() == []


def test_list_opponents(client):
    pid = make_player(client)
    make_opponent(client, pid, "Ania")
    make_opponent(client, pid, "Bartek")
    r = client.get(f"/api/players/{pid}/opponents")
    assert len(r.json()) == 2
    assert [o["name"] for o in r.json()] == ["Ania", "Bartek"]


def test_opponents_per_player_isolation(client):
    p1 = make_player(client, "P1")
    p2 = make_player(client, "P2")
    make_opponent(client, p1, "Wspólny rywal")
    assert len(client.get(f"/api/players/{p2}/opponents").json()) == 0


def test_update_opponent(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    r = client.put(f"/api/players/{pid}/opponents/{oid}", json={"style": "defender", "rubber_fh": "Tenergy 05"})
    assert r.status_code == 200
    assert r.json()["style"] == "defender"
    assert r.json()["rubber_fh"] == "Tenergy 05"


def test_delete_opponent_cascades_matches(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    make_match(client, pid, oid)
    client.delete(f"/api/players/{pid}/opponents/{oid}")
    assert client.get(f"/api/players/{pid}/journal").json() == []


def test_search_opponents(client):
    pid = make_player(client)
    make_opponent(client, pid, "Jan Kowalski")
    make_opponent(client, pid, "Jan Nowak")
    make_opponent(client, pid, "Tomek X")
    r = client.get(f"/api/players/{pid}/opponents/search?q=jan")
    assert r.status_code == 200
    assert len(r.json()) == 2


# ── Match journal ─────────────────────────────────────────────────────────────

def test_create_match(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid)
    r = client.get(f"/api/players/{pid}/journal/{mid}")
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "win"
    assert data["sets_me"] == 3
    assert data["sets_op"] == 1
    assert data["opponent_name"] == "Jan Kowalski"
    assert data["what_worked"] == ["krótki serwis"]
    assert data["self_technical"] == 4


def test_create_match_missing_required(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    r = client.post(f"/api/players/{pid}/journal", json={"opponent_id": oid})
    assert r.status_code == 400


def test_result_computed_win(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid, sets_me=3, sets_op=1)
    assert client.get(f"/api/players/{pid}/journal/{mid}").json()["result"] == "win"


def test_result_computed_loss(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid, sets_me=1, sets_op=3)
    assert client.get(f"/api/players/{pid}/journal/{mid}").json()["result"] == "loss"


def test_list_matches_filter_result(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    make_match(client, pid, oid, date="2026-01-01", sets_me=3, sets_op=1)
    make_match(client, pid, oid, date="2026-01-02", sets_me=0, sets_op=3)
    wins = client.get(f"/api/players/{pid}/journal?result=win").json()
    losses = client.get(f"/api/players/{pid}/journal?result=loss").json()
    assert len(wins) == 1
    assert len(losses) == 1


def test_list_matches_filter_opponent(client):
    pid = make_player(client)
    oid1 = make_opponent(client, pid, "Rywal A")
    oid2 = make_opponent(client, pid, "Rywal B")
    make_match(client, pid, oid1)
    make_match(client, pid, oid2)
    r = client.get(f"/api/players/{pid}/journal?opponent_id={oid1}")
    assert len(r.json()) == 1
    assert r.json()[0]["opponent_id"] == oid1


def test_update_match(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid)
    r = client.put(f"/api/players/{pid}/journal/{mid}", json={
        "free_notes": "dobra forma", "self_technical": 5
    })
    assert r.status_code == 200
    assert r.json()["free_notes"] == "dobra forma"
    assert r.json()["self_technical"] == 5


def test_delete_match(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid)
    client.delete(f"/api/players/{pid}/journal/{mid}")
    assert client.get(f"/api/players/{pid}/journal/{mid}").status_code == 404


def test_duplicate_match(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    mid = make_match(client, pid, oid)
    r = client.post(f"/api/players/{pid}/journal/{mid}/duplicate")
    assert r.status_code == 201
    dup = r.json()
    assert dup["opponent_id"] == oid
    assert dup["match_date"] == ""
    assert dup["result"] == ""
    assert len(client.get(f"/api/players/{pid}/journal").json()) == 2


def test_journal_isolation_between_players(client):
    p1 = make_player(client, "P1")
    p2 = make_player(client, "P2")
    oid = make_opponent(client, p1)
    make_match(client, p1, oid)
    assert client.get(f"/api/players/{p2}/journal").json() == []


# ── H2H ───────────────────────────────────────────────────────────────────────

def test_h2h(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    make_match(client, pid, oid, sets_me=3, sets_op=1)
    make_match(client, pid, oid, sets_me=1, sets_op=3)
    make_match(client, pid, oid, sets_me=3, sets_op=2)
    r = client.get(f"/api/players/{pid}/opponents/{oid}/h2h")
    assert r.status_code == 200
    h = r.json()
    assert h["wins"] == 2
    assert h["losses"] == 1
    assert h["total"] == 3
    assert len(h["last_matches"]) == 3


def test_h2h_top_patterns(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    for _ in range(3):
        client.post(f"/api/players/{pid}/journal", json={
            "opponent_id": oid, "match_date": "2026-04-01",
            "sets_me": 3, "sets_op": 0,
            "what_worked": ["krótki serwis", "FH top"],
        })
    h = client.get(f"/api/players/{pid}/opponents/{oid}/h2h").json()
    assert h["top_worked"][0]["text"] == "krótki serwis"
    assert h["top_worked"][0]["count"] == 3


# ── Stats + audit ─────────────────────────────────────────────────────────────

def test_journal_stats_empty(client):
    pid = make_player(client)
    r = client.get(f"/api/players/{pid}/journal/stats")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_journal_stats(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    make_match(client, pid, oid, sets_me=3, sets_op=1)
    make_match(client, pid, oid, sets_me=3, sets_op=2)
    make_match(client, pid, oid, sets_me=0, sets_op=3)
    r = client.get(f"/api/players/{pid}/journal/stats")
    s = r.json()
    assert s["total"] == 3
    assert s["wins"] == 2
    assert s["losses"] == 1
    assert s["win_rate"] == 67


def test_journal_audit(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    for _ in range(5):
        client.post(f"/api/players/{pid}/journal", json={
            "opponent_id": oid, "match_date": "2026-04-01",
            "sets_me": 0, "sets_op": 3,
            "mistakes": [{"category": "taktyczny", "description": "zbyt wolne FH"}],
            "what_failed": ["BH push"],
        })
    r = client.get(f"/api/players/{pid}/journal/audit")
    a = r.json()
    assert a["analyzed_matches"] == 5
    assert a["top_mistakes"][0]["text"] == "zbyt wolne FH"
    assert a["top_mistakes"][0]["count"] == 5
    assert a["top_failed"][0]["text"] == "BH push"


def test_delete_player_cascades_journal(client):
    pid = make_player(client)
    oid = make_opponent(client, pid)
    make_match(client, pid, oid)
    client.delete(f"/api/players/{pid}")
    # Opponents and matches should be gone (no direct list endpoint for deleted player,
    # but a new player won't see them)
    p2 = make_player(client, "P2")
    assert client.get(f"/api/players/{p2}/journal").json() == []
