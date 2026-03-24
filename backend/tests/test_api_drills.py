"""Integration tests for drill API endpoints."""

import drills


BALL = {"top_speed": 80, "bot_speed": 0, "oscillation": 150,
        "height": 150, "rotation": 150, "wait_ms": 1000}


# ── GET /api/drills/tree ─────────────────────────────────────────────────────

def test_get_drill_tree(client):
    r = client.get("/api/drills/tree")
    assert r.status_code == 200
    data = r.json()
    assert "folders" in data
    assert len(data["folders"]) >= 1


# ── POST /api/drills/folders ─────────────────────────────────────────────────

def test_create_folder(client):
    r = client.post("/api/drills/folders", json={"name": "My Folder"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "My Folder"
    assert data["id"] >= 90000


def test_create_folder_appears_in_tree(client):
    client.post("/api/drills/folders", json={"name": "Visible"})
    tree = client.get("/api/drills/tree").json()
    names = [f["name"] for f in tree["folders"]]
    assert "Visible" in names


# ── PUT /api/drills/folders/{id} ─────────────────────────────────────────────

def test_rename_folder(client):
    r = client.post("/api/drills/folders", json={"name": "Old"})
    fid = r.json()["id"]
    r2 = client.put(f"/api/drills/folders/{fid}", json={"name": "New"})
    assert r2.status_code == 200


def test_rename_folder_not_found(client):
    r = client.put("/api/drills/folders/99999", json={"name": "X"})
    assert r.status_code == 404


# ── DELETE /api/drills/folders/{id} ──────────────────────────────────────────

def test_delete_folder(client):
    r = client.post("/api/drills/folders", json={"name": "ToDelete"})
    fid = r.json()["id"]
    r2 = client.delete(f"/api/drills/folders/{fid}")
    assert r2.status_code == 204


# ── POST /api/drills ─────────────────────────────────────────────────────────

def test_create_drill(client):
    body = {"name": "Custom Drill", "balls": [BALL], "repeat": 0}
    r = client.post("/api/drills", json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Custom Drill"
    assert data["id"] >= 99001


# ── PUT /api/drills/{id} ────────────────────────────────────────────────────

def test_update_custom_drill(client):
    r = client.post("/api/drills", json={"name": "V1", "balls": [BALL], "repeat": 0})
    did = r.json()["id"]
    r2 = client.put(f"/api/drills/{did}", json={"name": "V2", "balls": [BALL]})
    assert r2.status_code == 200


def test_update_factory_drill_override(client):
    tree = client.get("/api/drills/tree").json()
    factory_drill = tree["folders"][0]["drills"][0]
    did = factory_drill["id"]
    new_balls = [{"top_speed": 200, "bot_speed": 10, "oscillation": 140,
                  "height": 120, "rotation": 160, "wait_ms": 1500}]
    r = client.put(f"/api/drills/{did}", json={"balls": new_balls, "repeat": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["balls"] == new_balls


# ── DELETE /api/drills/{id} ──────────────────────────────────────────────────

def test_delete_custom_drill(client):
    r = client.post("/api/drills", json={"name": "Del", "balls": [BALL], "repeat": 0})
    did = r.json()["id"]
    r2 = client.delete(f"/api/drills/{did}")
    assert r2.status_code == 204


# ── GET /api/drills/{id} ────────────────────────────────────────────────────

def test_get_drill(client):
    tree = client.get("/api/drills/tree").json()
    did = tree["folders"][0]["drills"][0]["id"]
    r = client.get(f"/api/drills/{did}")
    assert r.status_code == 200
    assert r.json()["id"] == did


def test_get_drill_not_found(client):
    r = client.get("/api/drills/99999")
    assert r.status_code == 404


# ── PUT /api/drills/{id}/count ───────────────────────────────────────────────

def test_set_drill_count(client):
    tree = client.get("/api/drills/tree").json()
    did = tree["folders"][0]["drills"][0]["id"]
    r = client.put(f"/api/drills/{did}/count", json={"count": 50})
    assert r.status_code == 200


# ── PUT /api/drills/{id}/reset ───────────────────────────────────────────────

def test_reset_drill(client):
    tree = client.get("/api/drills/tree").json()
    did = tree["folders"][0]["drills"][0]["id"]
    r = client.put(f"/api/drills/{did}/reset")
    assert r.status_code == 200


# ── POST /api/drills/reset-all ───────────────────────────────────────────────

def test_reset_all_drills(client):
    r = client.post("/api/drills/reset-all")
    assert r.status_code == 200
    assert r.json()["ok"] is True
