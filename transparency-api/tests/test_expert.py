"""Экспертная система: вердикт объясним, сигналы опираются на факты и НПА."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_verdict_chain_is_explainable():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        resp = None
        for e in entities:
            r = await client.get(f"/api/v1/entities/{e['id']}/verdict")
            assert r.status_code == 200
            body = r.json()
            if body["signals"]:
                resp = body
                break
        assert resp is not None, "мок-данные должны давать хотя бы один сигнал"
        # цепочка объяснения: факты -> признаки -> сигналы -> вердикт
        assert len(resp["facts"]) > 0
        assert len(resp["indicators"]) == len(resp["signals"])
        assert resp["level"] in ("critical", "attention", "normal")
        assert len(resp["level_label"]) > 0
        assert len(resp["recommendation"]) > 0
        # каждый сигнал ссылается на НПА
        assert len(resp["laws"]) > 0


@pytest.mark.asyncio
async def test_signals_feed_sorted_by_severity():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        feed = (await client.get("/api/v1/signals")).json()
    assert len(feed) > 0
    assert feed[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_contracts_have_check_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        rows = (await client.get("/api/v1/contracts")).json()
    assert len(rows) > 0
    assert all(r["check_status"] in ("в_норме", "средняя_степень", "высокая_степень") for r in rows)
    assert all(r["severity"] in ("none", "medium", "high") for r in rows)
    assert all(r["source"] for r in rows)


@pytest.mark.asyncio
async def test_laws_reference_real_acts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        laws = (await client.get("/api/v1/laws")).json()
    ids = {l["id"] for l in laws}
    assert {"fz-44", "fz-273", "uk-178"} <= ids
    assert all(l["annotation"] for l in laws)
