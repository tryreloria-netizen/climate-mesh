"""Sensor interface for Climate Mesh.

Supports Vernier Go Direct Weather (GDX-WTHR) for temperature/humidity,
MQ-7 Flying Fish via ADS1115 for CO-based air quality, and simulated
water level. Falls back gracefully to full simulation when hardware
is unavailable.
"""

import json
import os
import random
import time
import platform
import logging
from pathlib import Path

logger = logging.getLogger("climate_mesh.sensors")

CONFIG_PATH = Path(__file__).parent.parent / "data" / "sensor_config.json"

# --- Conditional hardware imports ---
_GDX_AVAILABLE = False
_GDX_ERROR = ""
_ADC_AVAILABLE = False
_ADC_ERROR = ""

try:
    from gdx import gdx as gdx_module
    _GDX_AVAILABLE = True
except ImportError as e:
    _GDX_ERROR = str(e)

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    _ADC_AVAILABLE = True
except ImportError as e:
    _ADC_ERROR = str(e)
except NotImplementedError as e:
    _ADC_ERROR = str(e)


def get_sensor_status() -> dict:
    """Return hardware detection results."""
    return {
        "gdx_available": _GDX_AVAILABLE,
        "adc_available": _ADC_AVAILABLE,
        "platform": platform.machine(),
        "gdx_error": _GDX_ERROR if not _GDX_AVAILABLE else None,
        "adc_error": _ADC_ERROR if not _ADC_AVAILABLE else None,
    }


class VernierMQ7SensorReader:
    """Reads real sensor data from GDX-WTHR (temp/humidity) and MQ-7 via ADS1115 (CO/air quality).

    Water level is simulated since neither sensor provides it.
    """

    def __init__(self, gdx_connection="usb", ads_channel=0):
        # --- Vernier GDX-WTHR setup ---
        self._gdx = gdx_module.gdx()
        self._gdx.open(connection=gdx_connection)
        # Channels: 1=Wind Speed, 3=Wind Chill, 4=Temperature, 5=Heat Index,
        # 7=Relative Humidity, 10=Barometric Pressure
        # Excluded: 2=Wind Direction, 6=Dew Point, 9=Station Pressure
        self._gdx.select_sensors([1, 3, 4, 5, 7, 10])
        self._gdx.start(2000)  # 2-second polling interval
        logger.info(f"GDX-WTHR connected via {gdx_connection}")

        # --- MQ-7 via ADS1115 setup ---
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        self._mq7 = AnalogIn(ads, getattr(ADS, f"P{ads_channel}"))
        logger.info(f"MQ-7 on ADS1115 channel {ads_channel}")

        self._last_good = {}

    def read_gdx(self) -> dict:
        """Read weather channels from GDX-WTHR.

        Channel order matches select_sensors([1, 3, 4, 5, 7, 10]):
        [0]=Wind Speed, [1]=Wind Chill, [2]=Temperature,
        [3]=Heat Index, [4]=Humidity, [5]=Barometric Pressure
        """
        try:
            measurements = self._gdx.read()
            if measurements is not None and len(measurements) >= 6:
                result = {
                    "wind_speed": round(measurements[0], 2),
                    "wind_chill": round(measurements[1], 2),
                    "temperature": round(measurements[2], 2),
                    "heat_index": round(measurements[3], 2),
                    "humidity": round(measurements[4], 2),
                    "barometric_pressure": round(measurements[5], 2),
                }
                self._last_good["gdx"] = result
                return result
        except Exception as e:
            logger.warning(f"GDX-WTHR read failed: {e}")
        return self._last_good.get("gdx", {
            "temperature": None, "humidity": None,
            "wind_speed": None, "wind_chill": None,
            "heat_index": None, "barometric_pressure": None,
        })

    def read_mq7(self) -> dict:
        """Read MQ-7 analog value via ADS1115 and convert to AQI estimate.

        The MQ-7 measures CO concentration. We map the voltage to a
        0-500 AQI-like scale for compatibility with the risk engine.
        """
        try:
            voltage = self._mq7.voltage
            # MQ-7 voltage to AQI approximation (0V=0, 3.3V=500)
            aqi = max(0, min(500, (voltage / 3.3) * 500))
            result = {"air_quality": round(aqi, 2)}
            self._last_good["mq7"] = result
            return result
        except Exception as e:
            logger.warning(f"MQ-7 read failed: {e}")
            return self._last_good.get("mq7", {"air_quality": None})

    def read_water_level(self) -> dict:
        """Simulate water level (no hardware sensor available)."""
        return {"water_level": round(1.0 + random.gauss(0, 0.2), 2)}

    def read_all(self) -> dict:
        """Read all sensors, returning combined dict with source metadata."""
        reading = {}
        reading.update(self.read_gdx())
        reading.update(self.read_mq7())
        reading.update(self.read_water_level())
        reading["source"] = "hardware"
        return reading

    def cleanup(self):
        """Release hardware resources."""
        try:
            self._gdx.stop()
            self._gdx.close()
        except Exception:
            pass


class SimulatedSensorReader:
    """Returns simulated sensor data (fallback when no hardware available)."""

    def read_all(self) -> dict:
        return {
            "temperature": round(22 + random.gauss(0, 2), 2),
            "humidity": round(60 + random.gauss(0, 5), 2),
            "air_quality": round(50 + random.gauss(0, 10), 2),
            "water_level": round(1.0 + random.gauss(0, 0.2), 2),
            "wind_speed": round(8 + random.gauss(0, 3), 2),
            "wind_chill": round(18 + random.gauss(0, 3), 2),
            "heat_index": round(24 + random.gauss(0, 3), 2),
            "barometric_pressure": round(1013 + random.gauss(0, 5), 2),
            "source": "simulation",
        }

    def cleanup(self):
        pass


def load_config() -> dict:
    """Load sensor config, returning defaults if file missing."""
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Config load failed: {e}")
    return {"mode": "auto", "pi_nodes": []}


def create_sensor_reader(node_config: dict | None = None):
    """Factory: return VernierMQ7SensorReader or SimulatedSensorReader based on config/detection."""
    config = load_config()
    # Env var override takes priority
    mode = os.environ.get("CLIMATE_MESH_MODE", config.get("mode", "auto"))

    use_hardware = False
    if mode == "pi":
        use_hardware = True
    elif mode == "auto":
        use_hardware = _GDX_AVAILABLE and _ADC_AVAILABLE
    # mode == "simulation" -> use_hardware stays False

    if use_hardware and _GDX_AVAILABLE and _ADC_AVAILABLE:
        pins = node_config or {}
        try:
            reader = VernierMQ7SensorReader(
                gdx_connection=pins.get("gdx_connection", "usb"),
                ads_channel=pins.get("ads1115_channel", 0),
            )
            logger.info("Hardware sensor reader initialized (GDX-WTHR + MQ-7)")
            return reader
        except Exception as e:
            logger.error(f"Hardware init failed, falling back to simulation: {e}")
            return SimulatedSensorReader()

    if use_hardware and not (_GDX_AVAILABLE and _ADC_AVAILABLE):
        missing = []
        if not _GDX_AVAILABLE:
            missing.append(f"godirect ({_GDX_ERROR})")
        if not _ADC_AVAILABLE:
            missing.append(f"ADS1115 ({_ADC_ERROR})")
        logger.warning(f"Hardware mode requested but unavailable: {', '.join(missing)}")

    return SimulatedSensorReader()
