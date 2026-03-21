"""
REST API — testy integracyjne.
Robot jest mockowany, więc nie wymagamy BLE/USB.
"""
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

import db
import presets


BALL = {"top_speed": 50, "bot_speed": 50, "oscillation": 128,
        "height": 128, "rotation": 128, "wait_ms": 1500}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    monkeypatch.setattr(presets, "DB", tmp_path / "presets.db")

    mock_robot = MagicMock()
    mock_robot.is_connected = False
    mock_robot.firmware = ""
    mock_robot.device = ""

    with patch("main.Robot", return_value=mock_robot), \
         patch("main._load_last_addr", return_value=""):
        import main
        with TestClient(main.app) as c:
            yield c


# ── Scenariusze ───────────────────────────────────────────────────────────────

def test_list_scenarios_empty(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert r.json() == []


def test_create_scenario(client):
    body = {"name": "Trening", "description": "opis", "balls": [BALL], "repeat": 1}
    r = client.post("/api/scenarios", json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Trening"
    assert data["balls"] == [BALL]
    assert "id" in data


def test_get_scenario(client):
    r = client.post("/api/scenarios",
                    json={"name": "X", "description": "", "balls": [BALL], "repeat": 2})
    id_ = r.json()["id"]
    r2 = client.get(f"/api/scenarios/{id_}")
    assert r2.status_code == 200
    assert r2.json()["id"] == id_


def test_get_scenario_404(client):
    assert client.get("/api/scenarios/9999").status_code == 404


def test_update_scenario(client):
    r = client.post("/api/scenarios",
                    json={"name": "Stary", "description": "", "balls": [BALL], "repeat": 1})
    id_ = r.json()["id"]
    body = {"name": "Nowy", "description": "zmieniony", "balls": [], "repeat": 3}
    r2 = client.put(f"/api/scenarios/{id_}", json=body)
    assert r2.status_code == 200
    assert r2.json()["name"] == "Nowy"


def test_delete_scenario(client):
    r = client.post("/api/scenarios",
                    json={"name": "Del", "description": "", "balls": [BALL], "repeat": 1})
    id_ = r.json()["id"]
    assert client.delete(f"/api/scenarios/{id_}").status_code == 204
    assert client.get(f"/api/scenarios/{id_}").status_code == 404


# ── Kalibracja ────────────────────────────────────────────────────────────────

def test_get_calibration(client):
    r = client.get("/api/calibration")
    assert r.status_code == 200
    data = r.json()
    assert "top_speed" in data and "bot_speed" in data


def test_save_calibration(client):
    body = {"top_speed": 30, "bot_speed": 40, "oscillation": 100,
            "height": 150, "rotation": 90, "wait_ms": 1200}
    r = client.put("/api/calibration", json=body)
    assert r.status_code == 200
    assert r.json()["top_speed"] == 30


# ── Presety ───────────────────────────────────────────────────────────────────

def test_list_presets_empty(client):
    r = client.get("/api/presets")
    assert r.status_code == 200
    assert r.json() == []


def test_create_preset(client):
    body = {"name": "Serwis", **BALL}
    r = client.post("/api/presets", json=body)
    assert r.status_code == 201
    assert r.json()["name"] == "Serwis"


def test_set_default_preset(client):
    r = client.post("/api/presets", json={"name": "P1", **BALL})
    id_ = r.json()["id"]
    assert client.put(f"/api/presets/{id_}/default").status_code == 204


def test_delete_preset(client):
    r = client.post("/api/presets", json={"name": "Temp", **BALL})
    id_ = r.json()["id"]
    assert client.delete(f"/api/presets/{id_}").status_code == 204
    lst = client.get("/api/presets").json()
    assert all(p["id"] != id_ for p in lst)
