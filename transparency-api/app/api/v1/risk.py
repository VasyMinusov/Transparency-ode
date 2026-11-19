"""Эндпоинт оценки риска: граф → признаки → модель → объяснение."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entity import Entity
from app.schemas.risk import RiskOut
from app.services.explainer import hypothesis
from app.services.graph_builder import build_graph, entity_features
from app.services.level import risk_level
from app.services.expert import analyze_entity
from app.services.predictor import RiskPredictor
from app.services.riskblend import blend_risk

router = APIRouter(prefix="/api/v1", tags=["risk"])


@router.get("/entities/{entity_id}/risk", response_model=RiskOut)
async def entity_risk(entity_id: int, session: AsyncSession = Depends(get_session)):
    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    graph = await build_graph(session)
    features = entity_features(graph, entity_id)
    proba, factors = RiskPredictor.get().predict(features)
    verdict = await analyze_entity(session, entity)  # кэшировано
    score = blend_risk(proba, verdict.signals)

    return RiskOut(
        entity=entity,
        risk_score=score,
        risk_level=risk_level(score),
        factors=factors,
        hypothesis=hypothesis(entity.name, score, factors),
        data_note="Оценка построена на синтетическом наборе данных "
                  "(procurement_mock) и носит характер сигнала для проверки человеком.",
    )
