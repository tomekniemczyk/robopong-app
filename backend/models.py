from pydantic import BaseModel, Field, model_validator
from typing import List, Literal, Optional


class Ball(BaseModel):
    # Zakresy dopasowane do Robot.SAFE_* (robot.py:158-165) — fail fast w 422
    # zamiast runtime SafetyError. Źródło: RE oryginalnej appki Newgy.
    top_speed:   int = Field(default=80,   ge=-210, le=210)
    bot_speed:   int = Field(default=0,    ge=-210, le=210)
    oscillation: int = Field(default=150,  ge=127,  le=173)
    height:      int = Field(default=150,  ge=75,   le=210)
    rotation:    int = Field(default=150,  ge=90,   le=210)
    wait_ms:     int = Field(default=1000, ge=200,  le=10000)


class ScenarioIn(BaseModel):
    name:        str
    description: str = ""
    balls:       List[Ball]
    repeat:      int = Field(default=1, ge=0)


class FolderIn(BaseModel):
    name:        str
    description: str = ""


class FolderUpdate(BaseModel):
    name:        Optional[str] = None
    description: Optional[str] = None
    sort_order:  Optional[int] = None


class DrillIn(BaseModel):
    folder_id:   Optional[int] = None
    name:        str
    description: str = ""
    youtube_id:  str = ""
    delay_s:     float = 0
    balls:       List[Ball]
    repeat:      int = Field(default=0, ge=0)
    sort_order:  int = Field(default=0, ge=0)


class ReorderItem(BaseModel):
    id:          int
    sort_order:  int


class DrillReorderItem(BaseModel):
    id:          int
    sort_order:  int
    folder_id:   Optional[int] = None


class ServeResponse(BaseModel):
    name:        str
    description: str = ""
    balls:       List[Ball]


class ServePlacement(BaseModel):
    x: float = Field(default=0.5, ge=0.0, le=1.0)
    y: float = Field(default=0.8, ge=0.0, le=1.0)


class ServeGroupIn(BaseModel):
    name:        str
    icon:        str = ""
    description: str = ""


class ServeIn(BaseModel):
    group_id:       Optional[int] = None
    name:           str
    description:    str = ""
    technique:      Literal["pendulum", "reverse_pendulum", "tomahawk", "backhand", "shovel", "squat", "other"] = "other"
    spin_type:      Literal["sidespin", "backspin", "topspin", "sidespin_backspin", "sidespin_topspin", "no_spin"] = "no_spin"
    spin_strength:  int = Field(default=0, ge=0, le=5)
    length:         Literal["short", "half_long", "long"] = "short"
    placement:      ServePlacement = Field(default_factory=ServePlacement)
    duration_sec:   int = Field(default=1200, ge=60, le=3600)
    responses:      List[ServeResponse] = Field(default_factory=list)
    youtube_id:     str = ""
    sort_order:     int = Field(default=0, ge=0)


class ServeReorderItem(BaseModel):
    id:         int
    sort_order: int
    group_id:   Optional[int] = None


class TrainingStep(BaseModel):
    drill_id:         Optional[int] = None
    drill_name:       str = ""
    exercise_id:      Optional[int] = None
    exercise_name:    str = ""
    serve_id:         Optional[int] = None
    serve_name:       str = ""
    serve_mode:       Literal["timer", "response"] = "timer"
    response_filter:  Optional[List[int]] = None
    random_responses: bool = False
    interval_sec:     Optional[int] = Field(default=None, ge=3, le=10)
    duration_sec:     Optional[int] = Field(default=None, ge=1, le=3600)
    count:            int = Field(default=60, ge=1, le=999)
    percent:          int = Field(default=100, ge=50, le=150)
    pause_after_sec:  int = Field(default=30, ge=0, le=600)

    @model_validator(mode="after")
    def _exactly_one_ref(self):
        refs = [self.drill_id, self.exercise_id, self.serve_id]
        if sum(1 for r in refs if r is not None) != 1:
            raise ValueError("Exactly one of drill_id/exercise_id/serve_id must be set")
        return self


class TrainingScenarioIn(BaseModel):
    name:           str
    description:    str = ""
    countdown_sec:  int = Field(default=5, ge=3, le=120)
    steps:          List[TrainingStep]
