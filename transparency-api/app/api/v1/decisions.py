"""Журнал решений сотрудника: сигнал подтверждён или отклонён человеком."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.decision import Decision
from app.models.entity import Entity
from app.schemas.decision import DecisionIn, DecisionOut

router = APIRouter(prefix="/api/v1", tags=["decisions"])


@router.post("/decisions", response_model=DecisionOut, status_code=201)
async def create_decision(
    payload: DecisionIn, session: AsyncSession = Depends(get_session)
):
    entity = (
        await session.execute(select(Entity).where(Entity.id == payload.entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    decision = Decision(**payload.model_dump())
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return decision


@router.get("/decisions", response_model=list[DecisionOut])
async def list_decisions(
    entity_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Decision).order_by(Decision.created_at.desc())
    if entity_id is not None:
        stmt = stmt.where(Decision.entity_id == entity_id)
    return (await session.execute(stmt)).scalars().all()
