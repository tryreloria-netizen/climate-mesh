"""Isolation Forest anomaly detection for Climate Mesh.

Unlike fixed thresholds, an Isolation Forest learns the normal multivariate
shape of the data and flags readings that are easy to isolate — catching
*developing* anomalies (an unusual combination of values) before any single
channel crosses a hard limit. The model trains on synthetic normal samples at
startup, so no external data or internet is required.

The output is explainable: alongside the anomaly score it returns the channels
that deviate most from the learned baseline, which the risk engine folds into
its plain-English explanation.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Feature order used everywhere in this module.
FEATURES = ("temperature", "humidity", "air_quality", "water_level",
            "wind_speed", "barometric_pressure")

# Means/spreads of the synthetic "normal" London-ish distribution. Spreads are
# wide enough that ordinary seasonal variation (a warm summer day, a breezy
# afternoon) is NOT flagged as anomalous, while genuine scenario extremes still
# sit well outside the learned envelope.
_NORMAL = {
    "temperature": (16.0, 8.0),
    "humidity": (68.0, 15.0),
    "air_quality": (55.0, 30.0),
    "water_level": (0.7, 0.6),
    "wind_speed": (5.0, 3.0),
    "barometric_pressure": (1013.0, 9.0),
}
_HUMAN = {
    "temperature": "temperature",
    "humidity": "humidity",
    "air_quality": "air quality",
    "water_level": "water level",
    "wind_speed": "wind speed",
    "barometric_pressure": "pressure",
}


def generate_training_data(n_samples: int = 2000, seed: int = 42) -> np.ndarray:
    """Generate synthetic normal sensor data for training (deterministic)."""
    rng = np.random.default_rng(seed)
    cols = [rng.normal(_NORMAL[f][0], _NORMAL[f][1], n_samples) for f in FEATURES]
    data = np.column_stack(cols)
    clamps = [(-15, 55), (0, 100), (0, 500), (0, 12), (0, 60), (940, 1060)]
    for i, (lo, hi) in enumerate(clamps):
        data[:, i] = np.clip(data[:, i], lo, hi)
    return data


class AnomalyDetector:
    """Wraps IsolationForest for explainable sensor anomaly detection."""

    def __init__(self):
        self.model = IsolationForest(n_estimators=120, contamination=0.05, random_state=42)
        self.scaler = StandardScaler()
        self.trained = False

    def train(self, quiet: bool = False) -> "AnomalyDetector":
        data = generate_training_data()
        self.scaler.fit(data)
        self.model.fit(self.scaler.transform(data))
        self.trained = True
        if not quiet:
            print("[AI] Isolation Forest trained on 2000 synthetic normal samples")
        return self

    def _feature_vector(self, reading: dict) -> np.ndarray:
        return np.array([[float(reading.get(f, _NORMAL[f][0])) for f in FEATURES]])

    def top_factors(self, reading: dict, k: int = 3) -> list[str]:
        """Channels deviating most from the learned baseline (in sigma units)."""
        devs = []
        for f in FEATURES:
            mu, sd = _NORMAL[f]
            z = abs(float(reading.get(f, mu)) - mu) / sd if sd else 0.0
            devs.append((z, _HUMAN[f]))
        devs.sort(reverse=True)
        return [name for z, name in devs[:k] if z > 1.0]

    def predict(self, reading: dict) -> dict:
        """Score one reading. Returns is_anomaly, score (0-1), explanation, factors."""
        if not self.trained:
            return {"is_anomaly": False, "score": 0.0,
                    "explanation": "model not trained", "factors": []}

        scaled = self.scaler.transform(self._feature_vector(reading))
        raw = float(self.model.decision_function(scaled)[0])  # >0 normal, <0 anomaly
        is_anomaly = self.model.predict(scaled)[0] == -1
        score = max(0.0, min(1.0, 0.5 - raw))  # higher = more anomalous

        factors = self.top_factors(reading)
        if is_anomaly and not factors:
            factors = ["an unusual combination of readings"]
        explanation = (", ".join(factors) if factors else "normal conditions")
        return {
            "is_anomaly": bool(is_anomaly),
            "score": round(score, 3),
            "explanation": explanation,
            "factors": factors,
        }
