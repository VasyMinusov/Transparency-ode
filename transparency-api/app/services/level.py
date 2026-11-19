"""Единая шкала уровней риска."""
def risk_level(score: float) -> str:
    return "high" if score > 0.7 else "medium" if score > 0.4 else "low"
