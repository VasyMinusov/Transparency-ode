"""Итоговая оценка риска = ML-модель + экспертные сигналы.

Модель (XGBoost+SHAP) оценивает структурные признаки графа; экспертная система —
конкретные схемы. Итог объединяется детерминированно (правило суммы вероятностей):
score = 1 - (1 - proba_ml) * (1 - score_правил).
Сигнал высокой степени даёт вклад 0.85, средней — 0.6; без сигналов остаётся
оценка модели. Это устраняет противоречие «вердикт критический, а оценка 0.00».
"""
from app.services.expert import Signal


def rule_score(signals: list[Signal]) -> float:
    sev = [s.severity for s in signals]
    if "high" in sev:
        return 0.85
    if "medium" in sev:
        return 0.60
    return 0.0


def blend_risk(proba_ml: float, signals: list[Signal]) -> float:
    rs = rule_score(signals)
    return round(1 - (1 - proba_ml) * (1 - rs), 4)
