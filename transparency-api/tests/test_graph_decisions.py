"""Граф с оценками риска + журнал решений человека."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_graph_has_nodes_with_risk():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) > 0
    assert len(body["edges"]) > 0
    node = body["nodes"][0]
    assert 0.0 <= node["risk_score"] <= 1.0
    assert node["risk_level"] in ("low", "medium", "high")
    # Детерминированность: повторный запрос — тот же граф
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp2 = await client.get("/api/v1/graph")
    assert resp2.json()["nodes"] == body["nodes"]


@pytest.mark.asyncio
async def test_decision_roundtrip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        entity_id = entities[0]["id"]

        created = await client.post("/api/v1/decisions", json={
            "entity_id": entity_id, "decision": "confirmed", "comment": "проверено вручную"
        })
        assert created.status_code == 201

        decisions = (await client.get(f"/api/v1/decisions?entity_id={entity_id}")).json()
        assert any(d["decision"] == "confirmed" for d in decisions)


@pytest.mark.asyncio
async def test_decision_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/decisions", json={
            "entity_id": 1, "decision": "maybe"
        })
    assert resp.status_code == 422
