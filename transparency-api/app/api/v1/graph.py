"""Эндпоинт графа: все узлы с оценками риска + рёбра — для визуализации."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entity import Entity, Relation
from app.schemas.graph import GraphEdge, GraphNode, GraphPayload
from app.services.graph_builder import build_graph, entity_features
from app.services.level import risk_level
from app.services.predictor import RiskPredictor

router = APIRouter(prefix="/api/v1", tags=["graph"])


@router.get("/graph", response_model=GraphPayload)
async def graph(session: AsyncSession = Depends(get_session)):
    entities = (
        await session.execute(select(Entity).order_by(Entity.id))
    ).scalars().all()
    relations = (await session.execute(select(Relation))).scalars().all()

    g = await build_graph(session)
    predictor = RiskPredictor.get()

    nodes = []
    for e in entities:
        score, _ = predictor.predict(entity_features(g, e.id))
        nodes.append(GraphNode(
            id=e.id,
            name=e.name,
            entity_type=e.entity_type,
            risk_score=round(score, 4),
            risk_level=risk_level(score),
        ))

    edges = [
        GraphEdge(
            source=r.source_id, target=r.target_id,
            relation_type=r.relation_type, weight=r.weight,
        )
        for r in relations
    ]
    return GraphPayload(nodes=nodes, edges=edges)
