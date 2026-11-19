"""Схемы ответа эндпоинта риска."""
from pydantic import BaseModel

from app.schemas.entity import EntityOut


class FactorOut(BaseModel):
    name: str          # имя признака
    value: float       # значение признака
    contribution: float  # вклад признака в оценку (SHAP)


class RiskOut(BaseModel):
    entity: EntityOut
    risk_score: float   # 0..1
    risk_level: str     # low | medium | high
    factors: list[FactorOut]
    hypothesis: str
    data_note: str      # честная пометка о природе данных
