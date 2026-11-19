"""Точка входа FastAPI-приложения."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.adapters.procurement import ProcurementAdapter
from app.api.v1.agent import router as agent_router
from app.api.v1.decisions import router as decisions_router
from app.api.v1.entities import router as entities_router
from app.api.v1.expert import router as expert_router
from app.api.v1.graph import router as graph_router
from app.api.v1.legal import router as legal_router
from app.api.v1.report import router as report_router
from app.api.v1.risk import router as risk_router
from app.core.config import settings
from app.core.db import async_session, init_db
from app.models.decision import Decision  # noqa: F401 — регистрация в metadata
from app.models.entity import Base
from app.models.tender import Bid, Tender  # noqa: F401 — регистрация в metadata
from app.services.seed import seed_from_adapter, seed_tenders


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(Base)
    # Первичное наполнение, если БД пустая (идемпотентно)
    async with async_session() as session:
        await seed_from_adapter(session, ProcurementAdapter())
        await seed_tenders(session)
    yield


app = FastAPI(
    title="Код прозрачности — API аналитики рисков",
    version="0.7.0",
    lifespan=lifespan,
)

# CORS: Tauri-окно (tauri://localhost) и Vite-dev (localhost:1420) обращаются к API
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
        "http://tauri.localhost",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entities_router)
app.include_router(risk_router)
app.include_router(graph_router)
app.include_router(report_router)
app.include_router(expert_router)
app.include_router(agent_router)
app.include_router(legal_router)
app.include_router(decisions_router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
