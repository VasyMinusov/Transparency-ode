"""Эндпоинт аналитического отчёта: сущность + риск + связи + источники + DOCX."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entity import Entity, Relation
from app.schemas.report import CounterpartyOut, ReportOut
from app.services.explainer import hypothesis
from app.services.graph_builder import build_graph, entity_features
from app.services.level import risk_level
from app.services.expert import analyze_entity
from app.services.predictor import RiskPredictor
from app.services.report_docx import build_report_docx
from app.services.riskblend import blend_risk

router = APIRouter(prefix="/api/v1", tags=["report"])


@router.get("/entities/{entity_id}/report", response_model=ReportOut)
async def entity_report(entity_id: int, session: AsyncSession = Depends(get_session)):
    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    graph = await build_graph(session)
    predictor = RiskPredictor.get()
    proba_ml, factors = predictor.predict(entity_features(graph, entity_id))
    _verdict = await analyze_entity(session, entity)  # кэшировано
    score = blend_risk(proba_ml, _verdict.signals)

    # Связи с участием сущности → агрегаты по контрагентам
    rels = (
        await session.execute(
            select(Relation).where(
                (Relation.source_id == entity_id) | (Relation.target_id == entity_id)
            )
        )
    ).scalars().all()

    cp_acc: dict[int, dict] = {}
    sources: set[str] = set()
    for r in rels:
        cid = r.target_id if r.source_id == entity_id else r.source_id
        acc = cp_acc.setdefault(cid, {"types": set(), "count": 0, "amount": 0.0})
        acc["types"].add(r.relation_type)
        acc["count"] += 1
        acc["amount"] += float(r.attributes.get("amount", 0))
        if src := r.attributes.get("data_source"):
            sources.add(src)
    if src := (entity.attributes or {}).get("data_source"):
        sources.add(src)

    counterparties = []
    for cid, acc in cp_acc.items():
        cp = (
            await session.execute(select(Entity).where(Entity.id == cid))
        ).scalar_one()
        _proba, _ = predictor.predict(entity_features(graph, cid))
        _v = await analyze_entity(session, cp)  # кэшировано
        cp_score = blend_risk(_proba, _v.signals)
        counterparties.append(CounterpartyOut(
            entity=cp,
            relation_types=sorted(acc["types"]),
            relation_count=acc["count"],
            total_amount=round(acc["amount"], 2),
            risk_score=round(cp_score, 4),
            risk_level=risk_level(cp_score),
        ))
    counterparties.sort(key=lambda c: c.risk_score, reverse=True)

    return ReportOut(
        entity=entity,
        risk_score=round(score, 4),
        risk_level=risk_level(score),
        factors=factors,
        hypothesis=hypothesis(entity.name, score, factors),
        data_note="Оценка построена на синтетическом наборе данных (procurement_mock) "
                  "и носит характер сигнала для проверки человеком.",
        counterparties=counterparties,
        sources=sorted(sources),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/entities/{entity_id}/report.docx")
async def entity_report_docx(entity_id: int, session: AsyncSession = Depends(get_session)):
    """Скачивание отчёта по сущности в формате DOCX."""
    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    buf = await build_report_docx(session, entity)
    filename = f"otchet_{entity.external_id or entity_id}.docx"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
