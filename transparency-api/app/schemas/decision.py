"""Схемы журнала решений."""
from datetime import datetime

from pydantic import BaseModel, Field


class DecisionIn(BaseModel):
    entity_id: int
    decision: str = Field(pattern="^(confirmed|rejected)$")
    comment: str = ""


class DecisionOut(BaseModel):
    id: int
    entity_id: int
    decision: str
    comment: str
    created_at: datetime

    model_config = {"from_attributes": True}
