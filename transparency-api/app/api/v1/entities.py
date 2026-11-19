"""Эндпоинты работы с сущностями и связями."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.procurement import ProcurementAdapter
from app.core.db import get_session
from app.models.entity import Entity, Relation
from app.schemas.entity import EntityOut, LoadResult, RelationOut
from app.services.seed import seed_from_adapter

router = APIRouter(prefix="/api/v1", tags=["entities"])


@router.get("/entities", response_model=list[EntityOut])
async def list_entities(
    entity_type: str | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Entity)
    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
    if q:
        stmt = stmt.where(Entity.name.contains(q))
    return (await session.execute(stmt.order_by(Entity.name))).scalars().all()


@router.get("/entities/{entity_id}", response_model=EntityOut)
async def get_entity(entity_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(Entity).where(Entity.id == entity_id)
    result = (await session.execute(stmt)).scalar_one_or_none()
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Entity not found")
    return result


@router.get("/entities/{entity_id}/relations", response_model=list[RelationOut])
async def entity_relations(entity_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(Relation).where(
        (Relation.source_id == entity_id) | (Relation.target_id == entity_id)
    )
    return (await session.execute(stmt)).scalars().all()


@router.post("/load", response_model=LoadResult)
async def load_data(session: AsyncSession = Depends(get_session)):
    """Загрузка данных из адаптеров. Явно инициируется — детерминированный момент загрузки."""
    stats = await seed_from_adapter(session, ProcurementAdapter())
    from app.services import expert as _expert
    from app.services.datacache import bump
    _expert._verdict_cache.clear()
    _expert._signals_cache.clear()
    bump()  # граф и центральности пересчитаются при следующем запросе
    return LoadResult(source=ProcurementAdapter.source_name, **stats)
