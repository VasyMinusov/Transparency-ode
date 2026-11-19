"""Провайдеры правового слоя.

Локальный корпус (конспекты статей, TF-IDF) — всегда активен.
Внешний провайдер: публикация правовых актов (publication.pravo.gov.ru).
У официального портала нет стабильного публичного API, поэтому контур устроен
честно: если задан APP_LEGAL_API_URL (прокси/внутренний сервис с полными
текстами), провайдер подключается; иначе система работает на локальном корпусе
и явно это показывает. Интерфейс позволяет добавить любой внешний источник.
"""
from app.core.config import settings


def providers() -> list[dict]:
    external_url = getattr(settings, "legal_api_url", "")
    return [
        {"id": "local-corpus", "title": "Локальный корпус НПА", "status": "active",
         "detail": "25 конспектов статей из 8 актов, поиск TF-IDF (детерминированно)"},
        {"id": "external-pravo", "title": "Внешний источник: publication.pravo.gov.ru",
         "status": "configured" if external_url else "not-configured",
         "detail": ("Подключён через APP_LEGAL_API_URL" if external_url
                    else "Задайте APP_LEGAL_API_URL (прокси с полными текстами) — "
                         "до тех пор работает локальный корпус")},
    ]
