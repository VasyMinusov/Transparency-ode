"""Эндпоинты восходящего агента: отчёт по сущности, сводка по сети, настройки LLM."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.models.entity import Entity
from app.services import agent as agent_service
from app.services.agent import agent_overview, agent_report

router = APIRouter(prefix="/api/v1", tags=["agent"])


class LLMSettingsIn(BaseModel):
    provider: str = Field(pattern="^(offline|gigachat|ollama)$")
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"


class LLMSettingsOut(BaseModel):
    provider: str
    ollama_url: str
    ollama_model: str
    gigachat_configured: bool


@router.get("/settings/llm", response_model=LLMSettingsOut)
async def get_llm_settings():
    return LLMSettingsOut(
        provider=settings.llm_provider,
        ollama_url=settings.ollama_url,
        ollama_model=settings.ollama_model,
        gigachat_configured=bool(settings.gigachat_credentials),
    )


@router.post("/settings/llm", response_model=LLMSettingsOut)
async def set_llm_settings(payload: LLMSettingsIn):
    settings.llm_provider = payload.provider
    settings.ollama_url = payload.ollama_url
    settings.ollama_model = payload.ollama_model
    agent_service._cache.clear()  # провайдер сменился — инвалидируем кэш агента
    return await get_llm_settings()


@router.get("/settings/llm/models")
async def list_local_models():
    """Установленные локальные модели (Ollama): имя, размер, дата изменения."""
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(f"{settings.ollama_url}/api/tags")
            resp.raise_for_status()
            return {"models": [
                {"name": m.get("name"), "size": m.get("size"), "modified_at": m.get("modified_at")}
                for m in resp.json().get("models", [])
            ]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ollama недоступен: {exc}")


_pulls: dict[str, dict] = {}


@router.post("/settings/llm/models/pull")
async def pull_model(payload: dict):
    """Скачивание модели в фоне. Проверка статуса: GET /settings/llm/models/pulls."""
    import asyncio
    model = (payload or {}).get("model", "").strip()
    if not model:
        raise HTTPException(status_code=422, detail="укажите model")
    cur = _pulls.get(model)
    if cur and cur["status"] == "running":
        return {"model": model, "status": "running"}

    async def _do():
        try:
            async with httpx.AsyncClient(timeout=3600) as http:
                resp = await http.post(f"{settings.ollama_url}/api/pull",
                                       json={"name": model, "stream": False})
                resp.raise_for_status()
                _pulls[model] = {"status": "done"}
        except Exception as exc:  # noqa: BLE001 — статус виден в pulls
            _pulls[model] = {"status": "error", "detail": str(exc)[:300]}

    _pulls[model] = {"status": "running"}
    asyncio.create_task(_do())
    return {"model": model, "status": "running"}


@router.get("/settings/llm/models/pulls")
async def pull_status():
    """Статусы фоновых загрузок моделей."""
    return {"pulls": _pulls}


@router.delete("/settings/llm/models/{name:path}")
async def delete_model(name: str):
    """Удаление локальной модели."""
    try:
        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.delete(f"{settings.ollama_url}/api/delete", json={"name": name})
            resp.raise_for_status()
            return {"deleted": name}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Не удалось удалить модель: {exc}")


@router.get("/entities/{entity_id}/agent-report")
async def report(entity_id: int, session: AsyncSession = Depends(get_session)):
    entity = (
        await session.execute(select(Entity).where(Entity.id == entity_id))
    ).scalar_one_or_none()
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return await agent_report(session, entity)


@router.get("/agent/overview")
async def overview(session: AsyncSession = Depends(get_session)):
    return await agent_overview(session)
