"""Адаптер реестра закупок. MVP читает мок-файл; дальше — замена на zakupki.gov.ru."""
import json
from pathlib import Path

from app.adapters.base import BaseAdapter


def _find_data_dir() -> Path:
    """Ищет data/mock_registries вверх от файла — работает при любом уровне вложения."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data" / "mock_registries"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("data/mock_registries не найден относительно проекта")


DATA_DIR = _find_data_dir()


class ProcurementAdapter(BaseAdapter):
    source_name = "procurement_mock"

    def load(self) -> list[dict]:
        raw = json.loads((DATA_DIR / "procurement.json").read_text(encoding="utf-8"))
        relations = []
        for rec in raw:
            relations.append({
                "source": {
                    "name": rec["customer_name"],
                    "type": "org",
                    "external_id": rec["customer_inn"],
                    "attributes": {
                        "founder_id": rec.get("customer_founder_id"),
                        "director_id": rec.get("customer_director_id"),
                        "data_source": self.source_name,
                    },
                },
                "target": {
                    "name": rec["supplier_name"],
                    "type": "org",
                    "external_id": rec["supplier_inn"],
                    "attributes": {
                        "address": rec["supplier_address"],
                        "registration_date": rec.get("registration_date"),
                        "capital": rec.get("capital"),
                        "director_id": rec.get("director_id"),
                        "founder_id": rec.get("founder_id"),
                        "data_source": self.source_name,  # синтетика явно помечена
                    },
                },
                "relation_type": "заключен_контракт",
                "weight": round(rec["amount"] / 1_000_000, 4),  # вес ~ масштаб контракта, млн ₽
                "attributes": {
                    "contract_number": rec["contract_number"],
                    "amount": rec["amount"],
                    "date": rec["date"],
                    "subject": rec["subject"],
                    "advance_share": rec.get("advance_share", 0.3),
                    "data_source": self.source_name,
                },
            })
        return relations
