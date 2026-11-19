"""Процедурный слой: тендеры, заявки, индикаторы сговора, методические основания."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_tenders_loaded_with_bids():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rows = (await client.get("/api/v1/tenders")).json()
    assert len(rows) > 0
    assert all("bids_count" in r and "winner" in r for r in rows)
    flagged = [r for r in rows if r["flags"]]
    assert len(flagged) > 0, "в мок-данных заложены паттерны C1–C3"


@pytest.mark.asyncio
async def test_signals_have_methodology():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        feed = (await client.get("/api/v1/signals")).json()
    assert len(feed) > 0
    assert all(s["methodology"] for s in feed), "у каждого сигнала — методическое основание"


@pytest.mark.asyncio
async def test_verdict_has_tender_rules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        rules_found = set()
        for e in entities:  # полный проход: R10 живёт на поставщиках из любой части алфавита
            v = (await client.get(f"/api/v1/entities/{e['id']}/verdict")).json()
            rules_found |= {i["rule"] for i in v["indicators"]}
    assert rules_found >= {"R1", "R10"}, f"ожидались контрактные и ЕГРЮЛ-правила, есть {rules_found}"
