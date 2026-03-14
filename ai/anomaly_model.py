"""Isolation Forest anomaly detection for Climate Mesh."""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def generate_training_data(n_samples: int = 2000) -> np.ndarray:
    """Generate synthetic normal sensor data for training."""
    rng = np.random.default_rng(42)
    data = np.column_stack([
        rng.normal(25, 4, n_samples),      # temperature (°C)
        rng.normal(60, 12, n_samples),      # humidity (%)
        rng.normal(70, 30, n_samples),      # air_quality (AQI)
        rng.normal(1.0, 0.5, n_samples),    # water_level (m)
    ])
    # Clamp to reasonable ranges
    data[:, 0] = np.clip(data[:, 0], -10, 50)
    data[:, 1] = np.clip(data[:, 1], 0, 100)
    data[:, 2] = np.clip(data[:, 2], 0, 300)
    data[:, 3] = np.clip(data[:, 3], 0, 5)
    return data


class AnomalyDetector:
    """Wraps IsolationForest for sensor anomaly detection."""

    def __init__(self):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.trained = False

    def train(self):
        """Train on synthetic normal data."""
        data = generate_training_data()
        self.scaler.fit(data)
        self.model.fit(self.scaler.transform(data))
        self.trained = True
        print("[AI] Anomaly detector trained on 2000 synthetic samples")

    def predict(self, temperature: float, humidity: float,
                air_quality: float, water_level: float) -> dict:
        """Predict anomaly for a single reading.

        Returns dict with 'is_anomaly' (bool), 'score' (0-1), 'explanation' (str).
        """
        if not self.trained:
            return {"is_anomaly": False, "score": 0.0, "explanation": "Model not trained"}

        features = np.array([[temperature, humidity, air_quality, water_level]])
        scaled = self.scaler.transform(features)

        # decision_function: negative = anomaly, positive = normal
        raw_score = self.model.decision_function(scaled)[0]
        prediction = self.model.predict(scaled)[0]  # 1 = normal, -1 = anomaly

        is_anomaly = prediction == -1
        # Convert raw score to 0-1 range (higher = more anomalous)
        anomaly_score = max(0.0, min(1.0, 0.5 - raw_score))

        # Generate explanation
        explanations = []
        if temperature > 40:
            explanations.append(f"extreme high temperature ({temperature:.1f}°C)")
        elif temperature < 0:
            explanations.append(f"extreme low temperature ({temperature:.1f}°C)")
        if humidity > 90:
            explanations.append(f"very high humidity ({humidity:.1f}%)")
        elif humidity < 15:
            explanations.append(f"very low humidity ({humidity:.1f}%)")
        if air_quality > 200:
            explanations.append(f"dangerous air quality (AQI {air_quality:.0f})")
        elif air_quality > 150:
            explanations.append(f"unhealthy air quality (AQI {air_quality:.0f})")
        if water_level > 4:
            explanations.append(f"critical water level ({water_level:.2f}m)")
        elif water_level > 3:
            explanations.append(f"high water level ({water_level:.2f}m)")

        if is_anomaly and not explanations:
            explanations.append("unusual combination of sensor values")

        explanation = "; ".join(explanations) if explanations else "normal conditions"

        return {
            "is_anomaly": is_anomaly,
            "score": round(anomaly_score, 3),
            "explanation": explanation,
        }
