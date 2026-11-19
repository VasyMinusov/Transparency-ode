"""Общие фикстуры: изолированная тестовая БД + seed.

БД тестов — временный файл, рабочая transparency.db не затрагивается.
ASGITransport не запускает lifespan, поэтому инициализация и seed — здесь.
"""
import os
import tempfile

# До импорта app.*: переопределяем БД на временную
_TMP_DB = os.path.join(tempfile.mkdtemp(prefix="transparency-test-"), "test.db")
os.environ["APP_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"

import pytest_asyncio

from app.adapters.procurement import ProcurementAdapter
from app.core.db import async_session, init_db
from app.models.decision import Decision  # noqa: F401
from app.models.entity import Base
from app.models.tender import Bid, Tender  # noqa: F401
from app.services.seed import seed_from_adapter, seed_tenders


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_db():
    await init_db(Base)
    async with async_session() as session:
        await seed_from_adapter(session, ProcurementAdapter())
        await seed_tenders(session)
