"""Integration tests for training API endpoints."""


TRAINING = {"name": "Morning Routine", "steps": [
    {"drill_id": 1, "count": 30, "percent": 100, "pause_after_sec": 15}
]}


# ── GET /api/trainings ──────────────────────────────────────────────────────

def test_list_trainings_empty(client):
    r = client.get("/api/trainings")
    assert r.status_code == 200
    assert r.json() == []


def test_list_trainings_populated(client):
    client.post("/api/trainings", json=TRAINING)
    r = client.get("/api/trainings")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── POST /api/trainings ─────────────────────────────────────────────────────

def test_create_training(client):
    r = client.post("/api/trainings", json=TRAINING)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Morning Routine"
    assert "id" in data


def test_create_multiple_trainings(client):
    client.post("/api/trainings", json=TRAINING)
    client.post("/api/trainings", json={"name": "Evening", "steps": []})
    r = client.get("/api/trainings")
    assert len(r.json()) == 2


# ── GET /api/trainings/{id} ─────────────────────────────────────────────────

def test_get_training(client):
    r = client.post("/api/trainings", json=TRAINING)
    tid = r.json()["id"]
    r2 = client.get(f"/api/trainings/{tid}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "Morning Routine"


def test_get_training_not_found(client):
    r = client.get("/api/trainings/9999")
    assert r.status_code == 404


# ── PUT /api/trainings/{id} ─────────────────────────────────────────────────

def test_update_training(client):
    r = client.post("/api/trainings", json=TRAINING)
    tid = r.json()["id"]
    updated = {"name": "Updated Routine", "steps": []}
    r2 = client.put(f"/api/trainings/{tid}", json=updated)
    assert r2.status_code == 200
    assert r2.json()["name"] == "Updated Routine"


def test_update_training_preserves_id(client):
    r = client.post("/api/trainings", json=TRAINING)
    tid = r.json()["id"]
    r2 = client.put(f"/api/trainings/{tid}", json={"name": "V2", "steps": []})
    assert r2.json()["id"] == tid


# ── DELETE /api/trainings/{id} ───────────────────────────────────────────────

def test_delete_training(client):
    r = client.post("/api/trainings", json=TRAINING)
    tid = r.json()["id"]
    r2 = client.delete(f"/api/trainings/{tid}")
    assert r2.status_code == 204
    assert client.get(f"/api/trainings/{tid}").status_code == 404


def test_delete_training_preserves_others(client):
    r1 = client.post("/api/trainings", json=TRAINING)
    r2 = client.post("/api/trainings", json={"name": "Keep", "steps": []})
    tid1 = r1.json()["id"]
    client.delete(f"/api/trainings/{tid1}")
    remaining = client.get("/api/trainings").json()
    assert len(remaining) == 1
    assert remaining[0]["name"] == "Keep"
