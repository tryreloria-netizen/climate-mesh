"""Risk score calculator for Climate Mesh."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import (
    get_latest_readings_per_node, get_risk_scores, insert_risk_score, insert_alert
)
from ai.anomaly_model import AnomalyDetector


def _temp_sub_score(temp: float) -> float:
    """Temperature sub-score (0-25). Higher = more dangerous."""
    if temp > 45:
        return 25
    elif temp > 40:
        return 20 + (temp - 40) * 1
    elif temp > 35:
        return 12 + (temp - 35) * 1.6
    elif temp < -5:
        return 25
    elif temp < 0:
        return 15 + (0 - temp) * 2
    else:
        return max(0, (abs(temp - 25) / 20) * 10)


def _humidity_sub_score(humidity: float) -> float:
    """Humidity sub-score (0-25)."""
    if humidity > 95:
        return 25
    elif humidity > 85:
        return 15 + (humidity - 85) * 1
    elif humidity < 10:
        return 25
    elif humidity < 20:
        return 15 + (20 - humidity) * 1
    else:
        return max(0, (abs(humidity - 55) / 45) * 10)


def _aqi_sub_score(aqi: float) -> float:
    """Air quality sub-score (0-25). AQI scale."""
    if aqi > 300:
        return 25
    elif aqi > 200:
        return 20 + (aqi - 200) * 0.05
    elif aqi > 150:
        return 15 + (aqi - 150) * 0.1
    elif aqi > 100:
        return 8 + (aqi - 100) * 0.14
    elif aqi > 50:
        return (aqi - 50) * 0.16
    return 0


def _water_sub_score(level: float) -> float:
    """Water level sub-score (0-25)."""
    if level > 6:
        return 25
    elif level > 4:
        return 20 + (level - 4) * 2.5
    elif level > 3:
        return 12 + (level - 3) * 8
    elif level > 2:
        return 5 + (level - 2) * 7
    elif level > 1:
        return (level - 1) * 5
    return 0


def _risk_level(score: float) -> str:
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "warning"
    elif score >= 30:
        return "moderate"
    return "safe"


def calculate_risk(reading: dict, detector: AnomalyDetector) -> dict:
    """Calculate risk score for a single node reading."""
    temp = reading["temperature"]
    humidity = reading["humidity"]
    aqi = reading["air_quality"]
    water = reading["water_level"]

    # Sub-scores (each 0-25)
    t_sub = _temp_sub_score(temp)
    h_sub = _humidity_sub_score(humidity)
    a_sub = _aqi_sub_score(aqi)
    w_sub = _water_sub_score(water)

    base_score = t_sub + h_sub + a_sub + w_sub

    # AI anomaly multiplier (1.0x to 1.5x)
    ai_result = detector.predict(temp, humidity, aqi, water)
    multiplier = 1.0 + (ai_result["score"] * 0.5) if ai_result["is_anomaly"] else 1.0

    final_score = min(100, base_score * multiplier)
    level = _risk_level(final_score)

    return {
        "node_id": reading["node_id"],
        "score": round(final_score, 1),
        "level": level,
        "temp_sub": round(t_sub, 1),
        "humidity_sub": round(h_sub, 1),
        "aqi_sub": round(a_sub, 1),
        "water_sub": round(w_sub, 1),
        "ai_multiplier": round(multiplier, 2),
        "ai_result": ai_result,
    }


def _check_alerts(reading: dict, risk: dict):
    """Generate alerts when critical thresholds are crossed."""
    node_id = reading["node_id"]

    if reading["water_level"] > 4:
        insert_alert(node_id, "flood",
                     f"Water level critical at {reading['water_level']:.2f}m",
                     "critical")
    elif reading["water_level"] > 3:
        insert_alert(node_id, "flood",
                     f"Water level high at {reading['water_level']:.2f}m",
                     "warning")

    if reading["air_quality"] > 300:
        insert_alert(node_id, "air_quality",
                     f"Hazardous AQI: {reading['air_quality']:.0f}",
                     "critical")
    elif reading["air_quality"] > 200:
        insert_alert(node_id, "air_quality",
                     f"Very unhealthy AQI: {reading['air_quality']:.0f}",
                     "warning")

    if reading["temperature"] > 45:
        insert_alert(node_id, "temperature",
                     f"Extreme temperature: {reading['temperature']:.1f}°C",
                     "critical")
    elif reading["temperature"] > 40:
        insert_alert(node_id, "temperature",
                     f"High temperature: {reading['temperature']:.1f}°C",
                     "warning")

    if risk["level"] == "critical":
        insert_alert(node_id, "risk",
                     f"Risk score critical: {risk['score']}/100",
                     "critical")


async def run_risk_engine(detector: AnomalyDetector):
    """Main risk engine loop — calculates risk every 3 seconds."""
    print("[Risk Engine] Started")

    while True:
        readings = get_latest_readings_per_node()
        for reading in readings:
            risk = calculate_risk(reading, detector)
            insert_risk_score(
                node_id=risk["node_id"],
                score=risk["score"],
                level=risk["level"],
                temp_sub=risk["temp_sub"],
                humidity_sub=risk["humidity_sub"],
                aqi_sub=risk["aqi_sub"],
                water_sub=risk["water_sub"],
                ai_multiplier=risk["ai_multiplier"],
            )
            _check_alerts(reading, risk)

        if readings:
            all_risks = get_risk_scores()
            if all_risks:
                avg = sum(r["score"] for r in all_risks) / len(all_risks)
                print(f"[Risk Engine] Processed {len(readings)} nodes | avg risk: {avg:.1f}")

        await asyncio.sleep(3)
