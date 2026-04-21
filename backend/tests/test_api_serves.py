"""Integration tests for /api/serves/* endpoints."""


# ── GET /api/serves/tree ─────────────────────────────────────────────────────

def test_get_tree_returns_factory_groups(client):
    r = client.get("/api/serves/tree")
    assert r.status_code == 200
    data = r.json()
    assert "groups" in data
    assert len(data["groups"]) == 2
    assert data["groups"][0]["readonly"] is True


def test_get_tree_assigns_ids(client):
    data = client.get("/api/serves/tree").json()
    assert data["groups"][0]["id"] == 1000
    assert data["groups"][0]["serves"][0]["id"] == 1001


# ── GET /api/serves/{sid} ────────────────────────────────────────────────────

def test_get_single_serve(client):
    r = client.get("/api/serves/1001")
    assert r.status_code == 200
    sv = r.json()
    assert sv["name"] == "Pendulum Short BH"
    assert "responses" in sv


def test_get_nonexistent_serve_404(client):
    r = client.get("/api/serves/99999")
    assert r.status_code == 404


# ── PUT /api/serves/{sid}/duration ───────────────────────────────────────────

def test_set_duration_override(client):
    r = client.put("/api/serves/1001/duration", json={"duration_sec": 600})
    assert r.status_code == 200
    sv = client.get("/api/serves/1001").json()
    assert sv["duration_sec"] == 600
    assert sv["modified"] is True


def test_set_duration_for_nonexistent_404(client):
    r = client.put("/api/serves/99999/duration", json={"duration_sec": 300})
    assert r.status_code == 404


# ── PUT /api/serves/{sid}/reset ──────────────────────────────────────────────

def test_reset_duration(client):
    client.put("/api/serves/1001/duration", json={"duration_sec": 600})
    r = client.put("/api/serves/1001/reset")
    assert r.status_code == 200
    sv = client.get("/api/serves/1001").json()
    assert sv["duration_sec"] == 300
    assert sv["modified"] is False


# ── POST /api/serves/reset-all ───────────────────────────────────────────────

def test_reset_all_clears_overrides(client):
    client.put("/api/serves/1001/duration", json={"duration_sec": 500})
    client.put("/api/serves/1002/duration", json={"duration_sec": 400})
    r = client.post("/api/serves/reset-all")
    assert r.status_code == 200
    assert client.get("/api/serves/1001").json()["modified"] is False
    assert client.get("/api/serves/1002").json()["modified"] is False


# ── DELETE /api/serves/{sid} ─────────────────────────────────────────────────

def test_cannot_delete_factory_serve(client):
    r = client.delete("/api/serves/1001")
    assert r.status_code == 403


# ── POST /api/serves/groups ──────────────────────────────────────────────────

def test_create_custom_group(client):
    r = client.post("/api/serves/groups", json={"name": "My Group"})
    assert r.status_code == 201
    g = r.json()
    assert g["id"] >= 90001
    assert g["name"] == "My Group"


def test_rename_custom_group(client):
    g = client.post("/api/serves/groups", json={"name": "Old"}).json()
    r = client.put(f"/api/serves/groups/{g['id']}", json={"name": "New"})
    assert r.status_code == 200
    tree = client.get("/api/serves/tree").json()
    assert any(grp["name"] == "New" for grp in tree["groups"])


def test_cannot_delete_factory_group(client):
    r = client.delete("/api/serves/groups/1000")
    assert r.status_code == 403


def test_delete_custom_group(client):
    g = client.post("/api/serves/groups", json={"name": "Tmp"}).json()
    r = client.delete(f"/api/serves/groups/{g['id']}")
    assert r.status_code == 204


# ── POST /api/serves (custom) ────────────────────────────────────────────────

def test_create_custom_serve_in_custom_group(client):
    g = client.post("/api/serves/groups", json={"name": "Mine"}).json()
    payload = {
        "group_id": g["id"],
        "name": "Test Serve",
        "description": "Desc",
        "technique": "pendulum",
        "spin_type": "sidespin",
        "spin_strength": 2,
        "length": "short",
        "placement": {"x": 0.5, "y": 0.8},
        "duration_sec": 200,
        "responses": [],
    }
    r = client.post("/api/serves", json=payload)
    assert r.status_code == 201
    sv = r.json()
    assert sv["name"] == "Test Serve"
    assert sv["readonly"] is False


def test_create_serve_in_factory_group_400(client):
    r = client.post("/api/serves", json={"group_id": 1000, "name": "X"})
    assert r.status_code == 400


def test_update_custom_serve(client):
    g = client.post("/api/serves/groups", json={"name": "G"}).json()
    sv = client.post("/api/serves", json={"group_id": g["id"], "name": "Old", "duration_sec": 100}).json()
    r = client.put(f"/api/serves/{sv['id']}", json={"name": "New", "duration_sec": 200})
    assert r.status_code == 200
    updated = client.get(f"/api/serves/{sv['id']}").json()
    assert updated["name"] == "New"
    assert updated["duration_sec"] == 200


def test_cannot_update_factory_serve(client):
    r = client.put("/api/serves/1001", json={"name": "Hacked"})
    assert r.status_code == 403


def test_delete_custom_serve(client):
    g = client.post("/api/serves/groups", json={"name": "G"}).json()
    sv = client.post("/api/serves", json={"group_id": g["id"], "name": "Doomed"}).json()
    r = client.delete(f"/api/serves/{sv['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/serves/{sv['id']}").status_code == 404


# ── Reorder ──────────────────────────────────────────────────────────────────

def test_reorder_custom_groups(client):
    g1 = client.post("/api/serves/groups", json={"name": "A"}).json()
    g2 = client.post("/api/serves/groups", json={"name": "B"}).json()
    r = client.put("/api/serves/groups/reorder",
                   json=[{"id": g2["id"], "sort_order": 0}, {"id": g1["id"], "sort_order": 1}])
    assert r.status_code == 200


def test_reorder_serves_between_groups(client):
    g1 = client.post("/api/serves/groups", json={"name": "G1"}).json()
    g2 = client.post("/api/serves/groups", json={"name": "G2"}).json()
    sv = client.post("/api/serves", json={"group_id": g1["id"], "name": "Movable"}).json()
    r = client.put("/api/serves/reorder",
                   json=[{"id": sv["id"], "sort_order": 0, "group_id": g2["id"]}])
    assert r.status_code == 200
    moved = client.get(f"/api/serves/{sv['id']}").json()
    assert moved["group_id"] == g2["id"]
