"""Integration tests for training API endpoints."""

import json


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


# ── Readonly trainings (defaults) ────────────────────────────────────────────

def _setup_defaults(client, tmp_path):
    """Write a minimal defaults file and reload."""
    import training
    defaults = {
        "folders": [{
            "name": "Test Program",
            "icon": "🏆",
            "trainings": [{
                "name": "Day 01",
                "description": "Test",
                "countdown_sec": 20,
                "steps": [{"drill_id": 1, "drill_name": "FH Warmup", "count": 30, "percent": 100, "pause_after_sec": 15}]
            }]
        }]
    }
    training.DEFAULTS_FILE.write_text(json.dumps(defaults))


def test_list_trainings_with_defaults(client, tmp_path):
    _setup_defaults(client, tmp_path)
    r = client.get("/api/trainings")
    data = r.json()
    assert any(t.get("readonly") for t in data)
    default = [t for t in data if t.get("readonly")]
    assert len(default) == 1
    assert default[0]["name"] == "Day 01"
    assert default[0]["folder"] == "Test Program"


def test_delete_readonly_training_returns_403(client, tmp_path):
    _setup_defaults(client, tmp_path)
    r = client.get("/api/trainings")
    readonly_id = [t for t in r.json() if t.get("readonly")][0]["id"]
    r2 = client.delete(f"/api/trainings/{readonly_id}")
    assert r2.status_code == 403


def test_update_readonly_training_returns_403(client, tmp_path):
    _setup_defaults(client, tmp_path)
    r = client.get("/api/trainings")
    readonly_id = [t for t in r.json() if t.get("readonly")][0]["id"]
    r2 = client.put(f"/api/trainings/{readonly_id}", json={"name": "Hacked", "steps": []})
    assert r2.status_code == 403


def test_duplicate_readonly_training(client, tmp_path):
    _setup_defaults(client, tmp_path)
    r = client.get("/api/trainings")
    readonly_id = [t for t in r.json() if t.get("readonly")][0]["id"]
    r2 = client.post(f"/api/trainings/{readonly_id}/duplicate")
    assert r2.status_code == 201
    copy = r2.json()
    assert "kopia" in copy["name"]
    assert not copy.get("readonly")


# ── Training History ─────────────────────────────────────────────────────────

def test_training_history_empty(client):
    r = client.get("/api/training-history")
    assert r.status_code == 200
    assert r.json() == []


def test_training_history_after_record(client):
    import training
    training.record_run(1, None, 120, "completed", 5, 5)
    r = client.get("/api/training-history")
    data = r.json()
    assert len(data) == 1
    assert data[0]["status"] == "completed"
    assert data[0]["elapsed_sec"] == 120


def test_training_history_filter_by_training(client):
    import training
    training.record_run(1, None, 60, "completed", 3, 3)
    training.record_run(2, None, 90, "stopped", 2, 5)
    r = client.get("/api/training-history?training_id=1")
    data = r.json()
    assert len(data) == 1
    assert data[0]["training_id"] == 1


def test_training_history_filter_by_player(client):
    import training
    training.record_run(1, 1, 60, "completed", 3, 3)
    training.record_run(1, 2, 90, "stopped", 2, 5)
    r = client.get("/api/training-history?player_id=1")
    data = r.json()
    assert len(data) == 1
    assert data[0]["player_id"] == 1


# ── Players API ──────────────────────────────────────────────────────────────

def test_list_players_empty(client):
    r = client.get("/api/players")
    assert r.status_code == 200
    assert r.json() == []


def test_create_player(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    assert r.status_code == 201
    assert r.json()["name"] == "Tomek"
    assert "id" in r.json()


def test_create_player_empty_name(client):
    r = client.post("/api/players", json={"name": ""})
    assert r.status_code == 400


def test_update_player(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.put(f"/api/players/{pid}", json={"name": "Tomasz"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "Tomasz"


def test_delete_player(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.delete(f"/api/players/{pid}")
    assert r2.status_code == 204
    assert client.get(f"/api/players/{pid}").status_code == 404


def test_player_history(client):
    import training
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    training.record_run(1, pid, 120, "completed", 5, 5)
    r2 = client.get(f"/api/players/{pid}/history")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


def test_player_recordings_empty(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/players/{pid}/recordings")
    assert r2.status_code == 200
    assert r2.json() == []


# ── Favorites API ────────────────────────────────────────────────────────────

def test_favorites_empty(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/players/{pid}/favorites")
    assert r2.status_code == 200
    assert r2.json() == []


def test_add_favorite(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.post(f"/api/players/{pid}/favorites", json={"item_type": "training", "item_id": 101})
    assert r2.status_code == 201
    assert r2.json()["item_type"] == "training"
    assert r2.json()["item_id"] == 101


def test_add_favorite_duplicate(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    client.post(f"/api/players/{pid}/favorites", json={"item_type": "drill", "item_id": 1001})
    client.post(f"/api/players/{pid}/favorites", json={"item_type": "drill", "item_id": 1001})
    favs = client.get(f"/api/players/{pid}/favorites").json()
    assert len(favs) == 1


def test_remove_favorite(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    client.post(f"/api/players/{pid}/favorites", json={"item_type": "exercise", "item_id": 101})
    r2 = client.delete(f"/api/players/{pid}/favorites?item_type=exercise&item_id=101")
    assert r2.status_code == 204
    assert client.get(f"/api/players/{pid}/favorites").json() == []


def test_favorites_per_player(client):
    r1 = client.post("/api/players", json={"name": "Tomek"})
    r2 = client.post("/api/players", json={"name": "Ania"})
    p1, p2 = r1.json()["id"], r2.json()["id"]
    client.post(f"/api/players/{p1}/favorites", json={"item_type": "training", "item_id": 101})
    client.post(f"/api/players/{p2}/favorites", json={"item_type": "training", "item_id": 102})
    assert len(client.get(f"/api/players/{p1}/favorites").json()) == 1
    assert client.get(f"/api/players/{p1}/favorites").json()[0]["item_id"] == 101


def test_add_favorite_invalid_type(client):
    r = client.post("/api/players", json={"name": "Tomek"})
    pid = r.json()["id"]
    r2 = client.post(f"/api/players/{pid}/favorites", json={"item_type": "invalid", "item_id": 1})
    assert r2.status_code == 400


# ── History detail endpoint ──────────────────────────────────────────────────

def test_get_history_entry(client):
    import training
    training.record_run(1, None, 120, "completed", 5, 5)
    history = client.get("/api/training-history").json()
    hid = history[0]["id"]
    r = client.get(f"/api/training-history/{hid}")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert "recordings" in r.json()


def test_get_history_entry_not_found(client):
    r = client.get("/api/training-history/99999")
    assert r.status_code == 404
