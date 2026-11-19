"""Объяснения сигналов: гипотеза на естественном языке.

Принцип: система формирует гипотезу для проверки человеком, а не обвинение.
GigaChat — при наличии credentials; иначе офлайн-шаблон. Ответы кэшируются:
одинаковый вход → одинаковый текст.
"""
from app.core.config import settings

_cache: dict[tuple[str, float], str] = {}


_FACTOR_RU = {
    "degree": "число связей",
    "betweenness": "роль посредника в сети",
    "contracts_count": "число контрактов",
    "weight_ratio": "концентрация сумм (максимум к среднему)",
}


def _offline_hypothesis(entity_name: str, risk_score: float, factors: list[dict]) -> str:
    top = factors[0] if factors else {"name": "нет данных", "contribution": 0.0}
    factor_ru = _FACTOR_RU.get(top["name"], top["name"])
    return (
        f"Обнаружена повышенная активность сущности «{entity_name}» "
        f"(оценка риска {risk_score:.2f}). Ключевой фактор: {factor_ru} "
        f"(вклад {top['contribution']:+.3f}). Требуется проверка человеком."
    )


def _gigachat_hypothesis(entity_name: str, risk_score: float, factors: list[dict]) -> str:
    from gigachat import GigaChat  # ленивый импорт: SDK нужен только при credentials

    client = GigaChat(
        credentials=settings.gigachat_credentials,
        scope=settings.gigachat_scope,
        verify_ssl_certs=False,
    )
    prompt = (
        "Ты — аналитик антикоррупционного подразделения. "
        f"Сущность: {entity_name}. Оценка риска: {risk_score:.2f}. "
        f"Ключевые факторы: {factors}. "
        "Сформулируй краткую гипотезу (2-3 предложения) о возможном риске "
        "в формате «Обнаружена связь между…». Только гипотеза, без обвинений."
    )
    response = client.chat(prompt)
    return response.choices[0].message.content


def hypothesis(entity_name: str, risk_score: float, factors: list[dict]) -> str:
    key = (entity_name, round(risk_score, 4))
    if key not in _cache:
        text = _offline_hypothesis(entity_name, risk_score, factors)
        if settings.gigachat_credentials:
            try:
                text = _gigachat_hypothesis(entity_name, risk_score, factors)
            except Exception:
                pass  # fallback: офлайн-шаблон
        _cache[key] = text
    return _cache[key]
