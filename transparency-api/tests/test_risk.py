"""Тесты эндпоинта риска и детерминированности."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_risk_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        entity_id = entities[0]["id"]
        resp = await client.get(f"/api/v1/entities/{entity_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["risk_score"] <= 1.0
    assert body["risk_level"] in ("low", "medium", "high")
    assert len(body["factors"]) <= 3
    assert "проверка человеком" in body["hypothesis"] or "Обнаружена" in body["hypothesis"]
    assert "синтетическ" in body["data_note"]


@pytest.mark.asyncio
async def test_determinism():
    """Одинаковый вход → одинаковый результат: повторный запрос даёт ту же оценку."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        entity_id = entities[0]["id"]
        r1 = await client.get(f"/api/v1/entities/{entity_id}/risk")
        r2 = await client.get(f"/api/v1/entities/{entity_id}/risk")
    assert r1.json()["risk_score"] == r2.json()["risk_score"]
    assert r1.json()["hypothesis"] == r2.json()["hypothesis"]


@pytest.mark.asyncio
async def test_risk_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/entities/999999/risk")
    assert resp.status_code == 404
