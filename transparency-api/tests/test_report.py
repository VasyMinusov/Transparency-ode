"""Отчёт по сущности: риск, контрагенты с агрегатами, источники данных."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_report_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        resp = await client.get(f"/api/v1/entities/{entities[0]['id']}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert 0.0 <= body["risk_score"] <= 1.0
    assert body["risk_level"] in ("low", "medium", "high")
    assert len(body["factors"]) <= 3
    # Контрагенты отсортированы по убыванию риска
    scores = [c["risk_score"] for c in body["counterparties"]]
    assert scores == sorted(scores, reverse=True)
    # Источники данных явно перечислены
    assert "procurement_mock" in body["sources"]
    # Честная пометка о природе данных
    assert "синтетическ" in body["data_note"]


@pytest.mark.asyncio
async def test_report_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/entities/999999/report")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_report_docx_download():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        entities = (await client.get("/api/v1/entities")).json()
        resp = await client.get(f"/api/v1/entities/{entities[0]['id']}/report.docx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert resp.content[:2] == b"PK"  # DOCX — это zip-контейнер
