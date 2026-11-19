"""Эндпоинты правового слоя: поиск по корпусу НПА на уровне статей."""
from fastapi import APIRouter, HTTPException, Query

from app.services.legal import acts_summary, article_by_id, search_articles
from app.services.legal_sources import providers

router = APIRouter(prefix="/api/v1", tags=["legal"])


@router.get("/legal/search")
async def legal_search(q: str = Query(min_length=2), top_k: int = 5):
    """Поиск релевантных статей по описанию нарушения (русский запрос)."""
    return {"query": q, "results": search_articles(q, top_k=top_k)}


@router.get("/legal/acts")
async def legal_acts():
    """Акты в корпусе с числом проиндексированных статей."""
    return {"acts": acts_summary()}


@router.get("/legal/articles/{article_id}")
async def legal_article(article_id: str):
    entry = article_by_id(article_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Статья не найдена")
    return entry


@router.get("/legal/providers")
async def legal_providers():
    """Провайдеры правового слоя и их статус."""
    return {"providers": providers()}
