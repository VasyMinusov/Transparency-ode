"""Схема аналитического отчёта по сущности — один запрос = целая отчётная страница."""
from datetime import datetime

from pydantic import BaseModel

from app.schemas.entity import EntityOut
from app.schemas.risk import FactorOut


class CounterpartyOut(BaseModel):
    """Связанная сущность с агрегатами по связям — строка таблицы связей в отчёте."""
    entity: EntityOut
    relation_types: list[str]
    relation_count: int
    total_amount: float
    risk_score: float
    risk_level: str


class ReportOut(BaseModel):
    entity: EntityOut
    risk_score: float
    risk_level: str
    factors: list[FactorOut]
    hypothesis: str
    data_note: str
    counterparties: list[CounterpartyOut]
    sources: list[str]        # использованные источники данных (data_source)
    generated_at: datetime    # момент формирования отчёта
