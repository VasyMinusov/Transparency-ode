"""Базовый интерфейс адаптера реестра.

Каждый источник (закупки, кадры, декларации) подключается через адаптер с единым
контрактом. Изменился контракт реестра — правится один файл, ядро не трогается.
"""
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    source_name: str = "base"

    @abstractmethod
    def load(self) -> list[dict]:
        """Возвращает нормализованные связи:

        {
            "source": {"name": ..., "type": "org", "external_id": ..., "attributes": {...}},
            "target": {"name": ..., "type": "org", "external_id": ..., "attributes": {...}},
            "relation_type": "заключен_контракт",
            "weight": 1.0,
            "attributes": {...},   # детали связи; всегда содержит data_source
        }
        """
        ...
