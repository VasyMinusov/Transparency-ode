"""Загрузка данных адаптеров в БД. Идемпотентна: повторный вызов — no-op."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import BaseAdapter
from app.adapters.tenders import TendersAdapter
from app.models.entity import Entity, Relation
from app.models.tender import Bid, Tender


async def _get_or_create_entity(
    session: AsyncSession,
    name: str,
    entity_type: str,
    external_id: str | None,
    attributes: dict | None = None,
) -> Entity:
    stmt = select(Entity).where(
        Entity.entity_type == entity_type, Entity.external_id == external_id
    )
    entity = (await session.execute(stmt)).scalar_one_or_none()
    if entity is None:
        entity = Entity(
            name=name,
            entity_type=entity_type,
            external_id=external_id,
            attributes=attributes or {},
        )
        session.add(entity)
        await session.flush()
    elif attributes:
        merged = dict(entity.attributes or {})
        for k, v in attributes.items():
            if v is not None and k not in merged:
                merged[k] = v
        entity.attributes = merged  # дозаполняем недостающие атрибуты (адрес, ЕГРЮЛ-признаки)
    return entity


async def seed_from_adapter(session: AsyncSession, adapter: BaseAdapter) -> dict:
    # Защита от дублирования: если связи уже загружены — ничего не делаем.
    existing = (await session.execute(select(func.count(Relation.id)))).scalar_one()
    if existing:
        await session.commit()
        return {"entities_created": 0, "relations_created": 0}

    known: set[tuple[str, str | None]] = set()
    created_entities = 0
    created_relations = 0

    for rel in adapter.load():
        for side in ("source", "target"):
            key = (rel[side]["type"], rel[side]["external_id"])
            if key not in known:
                await _get_or_create_entity(
                    session,
                    name=rel[side]["name"],
                    entity_type=rel[side]["type"],
                    external_id=rel[side]["external_id"],
                    attributes=rel[side].get("attributes"),
                )
                known.add(key)
                created_entities += 1

        source = await _get_or_create_entity(
            session, rel["source"]["name"], rel["source"]["type"],
            rel["source"]["external_id"],
        )
        target = await _get_or_create_entity(
            session, rel["target"]["name"], rel["target"]["type"],
            rel["target"]["external_id"],
        )
        session.add(Relation(
            source_id=source.id,
            target_id=target.id,
            relation_type=rel["relation_type"],
            weight=rel["weight"],
            attributes=rel["attributes"],
        ))
        created_relations += 1

    await session.commit()
    from app.services.datacache import bump
    bump()
    return {"entities_created": created_entities, "relations_created": created_relations}


async def seed_tenders(session: AsyncSession, adapter: TendersAdapter | None = None) -> dict:
    """Загрузка тендеров и заявок. Идемпотентна: повторный вызов — no-op."""
    from sqlalchemy import func as _func
    existing = (await session.execute(select(_func.count(Tender.id)))).scalar_one()
    if existing:
        await session.commit()
        return {"tenders_created": 0, "bids_created": 0}
    adapter = adapter or TendersAdapter()

    async def _ent(inn: str, name: str, etype: str = "org") -> Entity:
        return await _get_or_create_entity(session, name, etype, inn)

    tenders_created = bids_created = 0
    for t in adapter.load_tenders():
        customer = await _ent(t["customer_inn"], t["customer_name"])
        session.add(Tender(
            customer_id=customer.id, subject=t["subject"], procedure=t["procedure"],
            date=t["date"], submission_days=t["submission_days"], start_price=t["start_price"],
            attributes={"data_source": adapter.source_name},
        ))
        tenders_created += 1
    await session.flush()

    tenders_db = (await session.execute(select(Tender).order_by(Tender.id))).scalars().all()
    id_map = {t_data["id"]: t_db.id for t_data, t_db in
              zip(adapter.load_tenders(), tenders_db)}
    for b in adapter.load_bids():
        supplier = await _ent(b["supplier_inn"], b["supplier_name"])
        session.add(Bid(tender_id=id_map[b["tender_id"]], supplier_id=supplier.id,
                        price=b["price"], is_winner=b["is_winner"],
                        attributes={"data_source": adapter.source_name}))
        bids_created += 1
    await session.commit()
    return {"tenders_created": tenders_created, "bids_created": bids_created}
