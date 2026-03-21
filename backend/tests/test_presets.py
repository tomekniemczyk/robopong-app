import pytest
import presets


CAL = {"top_speed": 50, "bot_speed": 50, "oscillation": 128,
       "height": 128, "rotation": 128, "wait_ms": 1500}


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(presets, "DB", tmp_path / "presets.db")
    presets.init_presets()


def test_empty():
    assert presets.get_presets() == []
    assert presets.get_default_preset() is None


def test_save_and_list():
    id_ = presets.save_preset("Serwis", CAL)
    lst = presets.get_presets()
    assert len(lst) == 1
    assert lst[0]["id"] == id_
    assert lst[0]["name"] == "Serwis"
    assert lst[0]["top_speed"] == 50


def test_save_as_default():
    id_ = presets.save_preset("Default", CAL, is_default=True)
    d = presets.get_default_preset()
    assert d is not None
    assert d["id"] == id_


def test_only_one_default():
    presets.save_preset("A", CAL, is_default=True)
    id2 = presets.save_preset("B", CAL, is_default=True)
    # Tylko ostatni oznaczony jako default powinien nim być
    d = presets.get_default_preset()
    assert d["id"] == id2


def test_set_default():
    id1 = presets.save_preset("X", CAL)
    id2 = presets.save_preset("Y", CAL)
    presets.set_default(id1)
    assert presets.get_default_preset()["id"] == id1
    presets.set_default(id2)
    assert presets.get_default_preset()["id"] == id2


def test_delete():
    id_ = presets.save_preset("Temp", CAL)
    presets.delete_preset(id_)
    assert all(p["id"] != id_ for p in presets.get_presets())


def test_delete_default_clears():
    id_ = presets.save_preset("Solo", CAL, is_default=True)
    presets.delete_preset(id_)
    assert presets.get_default_preset() is None
