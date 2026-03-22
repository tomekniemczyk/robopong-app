from pydantic import BaseModel, Field
from typing import List


class Ball(BaseModel):
    top_speed:   int = Field(default=80,   ge=-249, le=249)
    bot_speed:   int = Field(default=80,   ge=-249, le=249)
    oscillation: int = Field(default=128,  ge=0,    le=255)
    height:      int = Field(default=128,  ge=0,    le=255)
    rotation:    int = Field(default=128,  ge=0,    le=255)
    wait_ms:     int = Field(default=1500, ge=200,  le=10000)


class ScenarioIn(BaseModel):
    name:        str
    description: str = ""
    balls:       List[Ball]
    repeat:      int = Field(default=1, ge=0)  # 0 = nieskończenie
