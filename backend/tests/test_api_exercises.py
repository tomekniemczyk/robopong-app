"""Integration tests for exercise API endpoints."""


# ── GET /api/exercises ───────────────────────────────────────────────────────

def test_list_exercises(client):
    r = client.get("/api/exercises")
    assert r.status_code == 200
    data = r.json()
    assert "categories" in data
    assert len(data["categories"]) >= 1


def test_list_exercises_has_ids(client):
    data = client.get("/api/exercises").json()
    cat = data["categories"][0]
    assert "id" in cat
    assert "id" in cat["exercises"][0]


def test_list_exercises_has_category_on_exercises(client):
    data = client.get("/api/exercises").json()
    ex = data["categories"][0]["exercises"][0]
    assert "category" in ex


# ── PUT /api/exercises/{id}/duration ─────────────────────────────────────────

def test_set_exercise_duration(client):
    data = client.get("/api/exercises").json()
    eid = data["categories"][0]["exercises"][0]["id"]
    r = client.put(f"/api/exercises/{eid}/duration", json={"duration_sec": 120})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_set_exercise_duration_persists(client):
    data = client.get("/api/exercises").json()
    eid = data["categories"][0]["exercises"][0]["id"]
    client.put(f"/api/exercises/{eid}/duration", json={"duration_sec": 90})
    # Re-fetch
    data2 = client.get("/api/exercises").json()
    ex = data2["categories"][0]["exercises"][0]
    assert ex["duration_sec"] == 90
    assert ex["modified"] is True


# ── POST /api/exercises/reset-all ────────────────────────────────────────────

def test_reset_all_exercises(client):
    data = client.get("/api/exercises").json()
    eid = data["categories"][0]["exercises"][0]["id"]
    client.put(f"/api/exercises/{eid}/duration", json={"duration_sec": 999})
    r = client.post("/api/exercises/reset-all")
    assert r.status_code == 200
    data2 = client.get("/api/exercises").json()
    ex = data2["categories"][0]["exercises"][0]
    assert ex["modified"] is False
