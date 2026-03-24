"""Tests for models.py Pydantic validation."""

import pytest
from pydantic import ValidationError
from models import Ball, ScenarioIn, DrillIn, TrainingStep


# ── Ball ─────────────────────────────────────────────────────────────────────

def test_ball_valid():
    b = Ball(top_speed=80, bot_speed=0, oscillation=150, height=150, rotation=150, wait_ms=1000)
    assert b.top_speed == 80
    assert b.wait_ms == 1000


def test_ball_defaults():
    b = Ball()
    assert b.top_speed == 80
    assert b.bot_speed == 0
    assert b.oscillation == 150
    assert b.height == 150
    assert b.rotation == 150
    assert b.wait_ms == 1000


def test_ball_negative_speed():
    b = Ball(top_speed=-100, bot_speed=-50)
    assert b.top_speed == -100
    assert b.bot_speed == -50


def test_ball_speed_too_high():
    with pytest.raises(ValidationError):
        Ball(top_speed=250)


def test_ball_speed_too_low():
    with pytest.raises(ValidationError):
        Ball(top_speed=-250)


def test_ball_oscillation_out_of_range():
    with pytest.raises(ValidationError):
        Ball(oscillation=256)


def test_ball_wait_ms_too_low():
    with pytest.raises(ValidationError):
        Ball(wait_ms=100)


def test_ball_wait_ms_too_high():
    with pytest.raises(ValidationError):
        Ball(wait_ms=20000)


def test_ball_boundary_values():
    b = Ball(top_speed=249, bot_speed=-249, oscillation=0, height=0, rotation=0, wait_ms=200)
    assert b.top_speed == 249
    b2 = Ball(top_speed=-249, bot_speed=249, oscillation=255, height=255, rotation=255, wait_ms=10000)
    assert b2.wait_ms == 10000


# ── ScenarioIn ───────────────────────────────────────────────────────────────

def test_scenario_valid():
    s = ScenarioIn(name="Test", balls=[Ball()], repeat=1)
    assert s.name == "Test"
    assert len(s.balls) == 1


def test_scenario_defaults():
    s = ScenarioIn(name="X", balls=[])
    assert s.description == ""
    assert s.repeat == 1


def test_scenario_invalid_repeat():
    with pytest.raises(ValidationError):
        ScenarioIn(name="X", balls=[], repeat=-1)


def test_scenario_empty_balls():
    s = ScenarioIn(name="Empty", balls=[])
    assert s.balls == []


def test_scenario_multiple_balls():
    s = ScenarioIn(name="Multi", balls=[Ball(), Ball(top_speed=120)], repeat=3)
    assert len(s.balls) == 2
    assert s.balls[1].top_speed == 120


# ── DrillIn ──────────────────────────────────────────────────────────────────

def test_drill_in_valid():
    d = DrillIn(name="My Drill", balls=[Ball()])
    assert d.name == "My Drill"
    assert d.folder_id is None
    assert d.sort_order == 0


def test_drill_in_with_folder():
    d = DrillIn(name="FH Loop", folder_id=1000, balls=[Ball()], repeat=5)
    assert d.folder_id == 1000
    assert d.repeat == 5


def test_drill_in_invalid_repeat():
    with pytest.raises(ValidationError):
        DrillIn(name="X", balls=[], repeat=-1)


def test_drill_in_invalid_sort_order():
    with pytest.raises(ValidationError):
        DrillIn(name="X", balls=[], sort_order=-1)


# ── TrainingStep ─────────────────────────────────────────────────────────────

def test_training_step_valid():
    ts = TrainingStep(drill_id=1001, count=60, percent=100, pause_after_sec=30)
    assert ts.drill_id == 1001
    assert ts.drill_name == ""


def test_training_step_defaults():
    ts = TrainingStep(drill_id=1)
    assert ts.count == 60
    assert ts.percent == 100
    assert ts.pause_after_sec == 30


def test_training_step_count_too_low():
    with pytest.raises(ValidationError):
        TrainingStep(drill_id=1, count=0)


def test_training_step_count_too_high():
    with pytest.raises(ValidationError):
        TrainingStep(drill_id=1, count=1000)


def test_training_step_percent_too_low():
    with pytest.raises(ValidationError):
        TrainingStep(drill_id=1, percent=49)


def test_training_step_percent_too_high():
    with pytest.raises(ValidationError):
        TrainingStep(drill_id=1, percent=151)


def test_training_step_pause_boundary():
    ts = TrainingStep(drill_id=1, pause_after_sec=0)
    assert ts.pause_after_sec == 0
    ts2 = TrainingStep(drill_id=1, pause_after_sec=600)
    assert ts2.pause_after_sec == 600


def test_training_step_pause_too_high():
    with pytest.raises(ValidationError):
        TrainingStep(drill_id=1, pause_after_sec=601)
