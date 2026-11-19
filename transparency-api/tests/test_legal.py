"""Правовой слой: поиск статей по запросу, обогащение сигналов статьями."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_legal_search_finds_relevant_article():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/legal/search", params={"q": "дача взятки посредник"})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0
    titles = " ".join(r["title"] for r in results)
    assert "взят" in titles.lower()
    assert all(r["article"] and r["act"] for r in results)


@pytest.mark.asyncio
async def test_signals_enriched_with_articles():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        feed = (await client.get("/api/v1/signals")).json()
    assert len(feed) > 0
    with_articles = [s for s in feed if s["articles"]]
    assert with_articles, "сигналы должны быть обогащены статьями НПА"
    s = with_articles[0]
    assert all(a["article"] and a["title"] for a in s["articles"])


@pytest.mark.asyncio
async def test_legal_acts_and_article_by_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        acts = (await client.get("/api/v1/legal/acts")).json()["acts"]
        art = await client.get("/api/v1/legal/articles/uk-290")
        missing = await client.get("/api/v1/legal/articles/nope")
    assert len(acts) >= 5
    assert art.status_code == 200 and art.json()["article"] == "ст. 290"
    assert missing.status_code == 404
