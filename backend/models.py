from pydantic import BaseModel, Field
from typing import List, Optional


class Ball(BaseModel):
    top_speed:   int = Field(default=80,   ge=-249, le=249)
    bot_speed:   int = Field(default=0,    ge=-249, le=249)
    oscillation: int = Field(default=150,  ge=0,    le=255)
    height:      int = Field(default=150,  ge=0,    le=255)
    rotation:    int = Field(default=150,  ge=0,    le=255)
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


class TrainingStep(BaseModel):
    drill_id:        int
    drill_name:      str = ""
    count:           int = Field(default=60, ge=1, le=999)
    percent:         int = Field(default=100, ge=50, le=150)
    pause_after_sec: int = Field(default=30, ge=0, le=600)


class TrainingScenarioIn(BaseModel):
    name:           str
    description:    str = ""
    countdown_sec:  int = Field(default=5, ge=3, le=120)
    steps:          List[TrainingStep]
