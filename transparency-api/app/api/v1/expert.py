"""Эндпоинты экспертной системы: вердикт, лента сигналов, контракты, НПА."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.entity import Entity, Relation
from app.models.tender import Bid, Tender
from app.schemas.expert import ContractRow, FactOut, LawOut, SignalOut, TenderOut, VerdictOut
from app.services.expert import LAWS, LEVEL_LABELS, all_signals, analyze_entity

router = APIRouter(prefix="/api/v1", tags=["expert"])


@router.get("/entities/{entity_id}/verdict", response_model=VerdictOut)
async def verdict(entity_id: int, session: AsyncSession = Depends(get_session)):
    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    v = await analyze_entity(session, entity)
    return VerdictOut(
        entity_id=entity.id,
        level=v.level,
        level_label=LEVEL_LABELS[v.level],
        summary=v.summary,
        recommendation=v.recommendation,
        facts=[FactOut(name=f.name, value=f.value) for f in v.facts],
        indicators=v.indicators,
        signals=[SignalOut(entity_id=entity.id, entity_name=entity.name, **s.__dict__) for s in v.signals],
        laws=v.laws,
    )


@router.get("/signals", response_model=list[SignalOut])
async def signals_feed(session: AsyncSession = Depends(get_session)):
    return await all_signals(session)


@router.get("/contracts", response_model=list[ContractRow])
async def contracts(session: AsyncSession = Depends(get_session)):
    """Реестр контрактов: сейчас — макет, далее — данные подключённых реестров."""
    relations = (await session.execute(select(Relation))).scalars().all()
    entities = {e.id: e for e in (await session.execute(select(Entity))).scalars().all()}
    feed = await all_signals(session)
    sev_of: dict[int, str] = {}
    for sig in feed:
        cur = sev_of.get(sig["entity_id"], "none")
        if sig["severity"] == "high" or cur == "high":
            sev_of[sig["entity_id"]] = "high"
        elif sig["severity"] == "medium":
            sev_of[sig["entity_id"]] = "medium"

    def sev(r: Relation) -> str:
        levels = [sev_of.get(r.source_id, "none"), sev_of.get(r.target_id, "none")]
        return "high" if "high" in levels else "medium" if "medium" in levels else "none"

    STATUS = {"high": "высокая_степень", "medium": "средняя_степень", "none": "в_норме"}
    rows = []
    for r in relations:
        attrs = r.attributes or {}
        sv = sev(r)
        rows.append(ContractRow(
            contract_number=attrs.get("contract_number", "—"),
            date=attrs.get("date", ""),
            amount=float(attrs.get("amount", 0)),
            subject=attrs.get("subject", ""),
            customer={"id": r.source_id, "name": entities[r.source_id].name},
            supplier={"id": r.target_id, "name": entities[r.target_id].name},
            source=attrs.get("data_source", ""),
            check_status=STATUS[sv],
            severity=sv,
        ))
    rows.sort(key=lambda x: x.amount, reverse=True)
    return rows


@router.get("/laws", response_model=list[LawOut])
async def laws():
    """Нормативно-правовая база, на которую ссылается экспертная система."""
    return LAWS


@router.get("/tenders", response_model=list[TenderOut])
async def tenders_list(session: AsyncSession = Depends(get_session)):
    """Процедурный слой: тендеры с заявками и сработавшими индикаторами сговора."""
    tenders = (await session.execute(select(Tender).order_by(Tender.date.desc()))).scalars().all()
    bids = (await session.execute(select(Bid))).scalars().all()
    entities = {en.id: en for en in (await session.execute(select(Entity))).scalars().all()}
    by_tender: dict[int, list[Bid]] = {}
    for b in bids:
        by_tender.setdefault(b.tender_id, []).append(b)

    # C3: пары соучастников — глобально по всем тендерам
    pair_wins: dict[tuple[int, int], dict] = {}
    for t in tenders:
        tb = by_tender.get(t.id, [])
        if len(tb) < 2:
            continue
        winner = next((b.supplier_id for b in tb if b.is_winner), None)
        for b in tb:
            if b.supplier_id == winner:
                continue
            key = tuple(sorted((b.supplier_id, winner)))
            st = pair_wins.setdefault(key, {"together": 0, "wins": {winner: 0}})
            st["together"] += 1
            st["wins"][winner] = st["wins"].get(winner, 0) + 1
    colluding_pairs = {k for k, st in pair_wins.items()
                       if st["together"] >= 3 and max(st["wins"].values()) == st["together"]}

    competitive = {"открытый конкурс", "аукцион", "запрос котировок"}
    rows = []
    for t in tenders:
        tb = sorted(by_tender.get(t.id, []), key=lambda b: b.price)
        flags = []
        if t.procedure in competitive and len(tb) == 1:
            flags.append("C1: единственный участник")
        if len(tb) >= 2:
            if any(abs(tb[i].price - tb[i + 1].price) / max(tb[i].price, 1) < 0.005
                   for i in range(len(tb) - 1)) or (len(tb) >= 3 and all(b.price % 1000 == 0 for b in tb)):
                flags.append("C2: идентичные/кратные цены")
        winner_bid = next((b for b in tb if b.is_winner), None)
        if winner_bid and len(tb) >= 2:
            for b in tb:
                if b.supplier_id != winner_bid.supplier_id and                    tuple(sorted((b.supplier_id, winner_bid.supplier_id))) in colluding_pairs:
                    flags.append("C3: пара с постоянным победителем")
                    break
        winner = winner_bid and {"id": winner_bid.supplier_id,
                                 "name": entities[winner_bid.supplier_id].name}
        rows.append(TenderOut(
            id=t.id, subject=t.subject, procedure=t.procedure, date=t.date,
            submission_days=t.submission_days, start_price=t.start_price,
            customer={"id": t.customer_id, "name": entities[t.customer_id].name},
            bids_count=len(tb), winner=winner, flags=flags,
        ))
    return rows
