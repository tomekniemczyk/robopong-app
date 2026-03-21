import pytest
import db


BALLS = [{"top_speed": 50, "bot_speed": 50, "oscillation": 128,
          "height": 128, "rotation": 128, "wait_ms": 1500}]


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB", tmp_path / "test.db")
    db.init()


def test_empty():
    assert db.get_scenarios() == []


def test_save_and_get():
    id_ = db.save_scenario("Trening", "opis", BALLS, 1)
    s = db.get_scenario(id_)
    assert s["name"] == "Trening"
    assert s["description"] == "opis"
    assert s["balls"] == BALLS
    assert s["repeat"] == 1


def test_list_scenarios():
    db.save_scenario("A", "", BALLS, 1)
    db.save_scenario("B", "", BALLS, 2)
    lst = db.get_scenarios()
    assert len(lst) == 2
    assert {s["name"] for s in lst} == {"A", "B"}


def test_update():
    id_ = db.save_scenario("Stary", "", BALLS, 1)
    db.update_scenario(id_, "Nowy", "zmieniony", [], 3)
    s = db.get_scenario(id_)
    assert s["name"] == "Nowy"
    assert s["description"] == "zmieniony"
    assert s["repeat"] == 3
    assert s["balls"] == []


def test_delete():
    id_ = db.save_scenario("DoUsunięcia", "", BALLS, 1)
    db.delete_scenario(id_)
    assert db.get_scenario(id_) is None


def test_get_nonexistent():
    assert db.get_scenario(9999) is None
