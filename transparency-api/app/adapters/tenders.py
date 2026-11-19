"""Адаптер тендеров: читает мок tenders.json; дальше — замена на ЕИС при наличии доступа."""
import json
from pathlib import Path

from app.adapters.base import BaseAdapter


def _find_data_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "mock_registries"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("data/mock_registries не найден")


class TendersAdapter(BaseAdapter):
    source_name = "tenders_mock"

    def load_tenders(self) -> list[dict]:
        raw = json.loads((_find_data_dir() / "tenders.json").read_text(encoding="utf-8"))
        return raw["tenders"]

    def load_bids(self) -> list[dict]:
        raw = json.loads((_find_data_dir() / "tenders.json").read_text(encoding="utf-8"))
        return raw["bids"]

    def load(self) -> list[dict]:  # контрактный контракт BaseAdapter здесь не используется
        return []
