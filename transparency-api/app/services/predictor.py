"""Предиктивная модель риска: XGBoost + SHAP.

Обучение на синтетике с фиксированным seed=42: одинаковые входные данные и
условия → одинаковый результат (требование паспорта о детерминированности).
Метрики модели на тестовом наборе — в паспорте, блок 5.
"""
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

FEATURES = ["degree", "betweenness", "contracts_count", "weight_ratio"]


class RiskPredictor:
    _instance: "RiskPredictor | None" = None

    def __init__(self) -> None:
        self.model = self._train_on_synthetic()
        self.explainer = shap.TreeExplainer(self.model)

    @classmethod
    def get(cls) -> "RiskPredictor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _train_on_synthetic() -> xgb.XGBClassifier:
        rng = np.random.default_rng(42)
        n = 1000
        X = pd.DataFrame({
            "degree": rng.poisson(3, n).astype(float),
            "betweenness": rng.beta(2, 5, n),
            "contracts_count": rng.poisson(4, n).astype(float),
            "weight_ratio": np.abs(rng.normal(1.5, 0.8, n)) + 1.0,
        })
        # Калибровка под диапазоны мок-данных: крупные заказчики — высокий риск,
        # мелкие поставщики — низкий; распределение оценок не нулевое.
        y = (((X["contracts_count"] >= 6) & (X["weight_ratio"] > 1.4)) |
             (X["weight_ratio"] > 2.8) |
             ((X["degree"] >= 10) & (X["betweenness"] > 0.03))).astype(int)
        model = xgb.XGBClassifier(
            n_estimators=50, max_depth=3, random_state=42, tree_method="hist"
        )
        model.fit(X, y)
        return model

    def predict(self, features: dict) -> tuple[float, list[dict]]:
        """Возвращает (оценка риска 0..1, топ-3 фактора по модулю вклада SHAP)."""
        row = pd.DataFrame([{k: float(features.get(k, 0.0)) for k in FEATURES}])
        proba = float(self.model.predict_proba(row)[0][1])
        shap_values = self.explainer.shap_values(row)[0]
        factors = [
            {"name": name, "value": float(row[name].iloc[0]), "contribution": float(sv)}
            for name, sv in zip(FEATURES, shap_values)
        ]
        factors.sort(key=lambda f: abs(f["contribution"]), reverse=True)
        return proba, factors[:3]
