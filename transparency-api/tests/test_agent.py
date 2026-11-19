"""Восходящий агент: корреляции находятся от данных, ответ кэшируется."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_agent_report_has_correlations():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        resp = await client.get(f"/api/v1/entities/{entities[0]['id']}/agent-report")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["narrative"]) > 0
    assert isinstance(body["findings"], list)
    assert body["provider"] in ("offline", "gigachat", "ollama")
    # кэширование: повторный запрос тот же
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp2 = await client.get(f"/api/v1/entities/{entities[0]['id']}/agent-report")
    assert resp2.json()["narrative"] == body["narrative"]


@pytest.mark.asyncio
async def test_agent_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/agent/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entities_count"] > 0
    assert len(body["findings"]) > 0
    assert "человек" in body["narrative"]  # напоминание о человеке в контуре


@pytest.mark.asyncio
async def test_llm_settings_roundtrip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        cur = (await client.get("/api/v1/settings/llm")).json()
        resp = await client.post("/api/v1/settings/llm", json={
            "provider": "offline", "ollama_url": cur["ollama_url"],
            "ollama_model": cur["ollama_model"],
        })
        assert resp.status_code == 200
        assert resp.json()["provider"] == "offline"
        # невалидный провайдер отклоняется
        bad = await client.post("/api/v1/settings/llm", json={
            "provider": "chatgpt", "ollama_url": "x", "ollama_model": "y"})
        assert bad.status_code == 422


@pytest.mark.asyncio
async def test_pull_status_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/settings/llm/models/pulls")
    assert resp.status_code == 200
    assert "pulls" in resp.json()
