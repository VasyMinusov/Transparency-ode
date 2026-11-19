"""Статистические инструменты для правил экспертной системы.

Забор Тьюки: выброс — значение выше Q3 + 1.5*IQR по распределению самого
заказчика (а не по фиксированному порогу). Методика применения red flags
в закупках (Open Contracting Partnership, библиотека Cardinal): пороги
правил считаются от данных, поэтому правило адаптируется к масштабу
конкретного заказчика и не даёт ложных срабатываний на крупных организациях.
"""
import numpy as np


def tukey_fence(values: list[float]) -> float | None:
    """Верхний забор Тьюки Q3 + 1.5*IQR. None — если данных недостаточно."""
    vals = [float(v) for v in values if v and v > 0]
    if len(vals) < 4:
        return None
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    fence = q3 + 1.5 * iqr
    return float(fence) if fence > 0 else None


def is_outlier(values: list[float], x: float) -> bool:
    """x — статистический выброс относительно распределения values."""
    fence = tukey_fence(values)
    return fence is not None and x > fence
