"""Raspberry Pi 5 sensor interface for Climate Mesh.

Supports DHT22 (temp/humidity), MQ-135 via ADS1115 (air quality),
and HC-SR04 (ultrasonic water level). Falls back gracefully to
simulated data when hardware is unavailable.
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

# --- Conditional GPIO imports ---
_HW_AVAILABLE = False
_HW_ERROR = ""

try:
    import board
    import adafruit_dht
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import RPi.GPIO as GPIO
    _HW_AVAILABLE = True
except ImportError as e:
    _HW_ERROR = str(e)
except NotImplementedError as e:
    _HW_ERROR = str(e)


def get_sensor_status() -> dict:
    """Return hardware detection results."""
    return {
        "hardware_available": _HW_AVAILABLE,
        "platform": platform.machine(),
        "error": _HW_ERROR if not _HW_AVAILABLE else None,
    }


class PiSensorReader:
    """Reads real sensor data from GPIO-attached hardware on Raspberry Pi 5."""

    def __init__(self, dht22_pin=4, trigger_pin=17, echo_pin=27, ads_channel=0):
        self._dht = adafruit_dht.DHT22(getattr(board, f"D{dht22_pin}"))
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        self._mq135 = AnalogIn(ads, getattr(ADS, f"P{ads_channel}"))
        self._trigger_pin = trigger_pin
        self._echo_pin = echo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(trigger_pin, GPIO.OUT)
        GPIO.setup(echo_pin, GPIO.IN)
        self._last_good = {}

    def read_dht22(self) -> dict:
        """Read DHT22 with retry logic (these sensors fail ~30% of reads)."""
        for attempt in range(3):
            try:
                temp = self._dht.temperature
                hum = self._dht.humidity
                if temp is not None and hum is not None:
                    result = {"temperature": round(temp, 2), "humidity": round(hum, 2)}
                    self._last_good["dht22"] = result
                    return result
            except RuntimeError:
                time.sleep(0.5)
        return self._last_good.get("dht22", {"temperature": None, "humidity": None})

    def read_mq135(self) -> dict:
        """Read MQ-135 analog value via ADS1115 and convert to AQI estimate."""
        try:
            voltage = self._mq135.voltage
            # Approximate: MQ-135 voltage to AQI (0V=0, 3.3V=500)
            aqi = max(0, min(500, (voltage / 3.3) * 500))
            result = {"air_quality": round(aqi, 2)}
            self._last_good["mq135"] = result
            return result
        except Exception as e:
            logger.warning(f"MQ-135 read failed: {e}")
            return self._last_good.get("mq135", {"air_quality": None})

    def read_hcsr04(self) -> dict:
        """Read HC-SR04 ultrasonic distance and convert to water level."""
        try:
            GPIO.output(self._trigger_pin, True)
            time.sleep(0.00001)
            GPIO.output(self._trigger_pin, False)

            timeout = time.time() + 0.04
            start = time.time()
            while GPIO.input(self._echo_pin) == 0:
                start = time.time()
                if start > timeout:
                    raise TimeoutError("HC-SR04 no echo start")

            stop = time.time()
            while GPIO.input(self._echo_pin) == 1:
                stop = time.time()
                if stop > timeout:
                    raise TimeoutError("HC-SR04 no echo end")

            distance_cm = (stop - start) * 34300 / 2
            # Sensor mounted at fixed height above river bed
            MOUNT_HEIGHT_CM = 200
            water_level_m = max(0, (MOUNT_HEIGHT_CM - distance_cm) / 100)
            result = {"water_level": round(water_level_m, 2)}
            self._last_good["hcsr04"] = result
            return result
        except Exception as e:
            logger.warning(f"HC-SR04 read failed: {e}")
            return self._last_good.get("hcsr04", {"water_level": None})

    def read_all(self) -> dict:
        """Read all sensors, returning combined dict with source metadata."""
        reading = {}
        reading.update(self.read_dht22())
        reading.update(self.read_mq135())
        reading.update(self.read_hcsr04())
        reading["source"] = "hardware"
        return reading

    def cleanup(self):
        """Release GPIO resources."""
        try:
            self._dht.exit()
            GPIO.cleanup()
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
    """Factory: return PiSensorReader or SimulatedSensorReader based on config/detection."""
    config = load_config()
    # Env var override takes priority
    mode = os.environ.get("CLIMATE_MESH_MODE", config.get("mode", "auto"))

    use_hardware = False
    if mode == "pi":
        use_hardware = True
    elif mode == "auto":
        use_hardware = _HW_AVAILABLE
    # mode == "simulation" -> use_hardware stays False

    if use_hardware and _HW_AVAILABLE:
        pins = node_config or {}
        try:
            reader = PiSensorReader(
                dht22_pin=pins.get("dht22_pin", 4),
                trigger_pin=pins.get("hcsr04_trigger_pin", 17),
                echo_pin=pins.get("hcsr04_echo_pin", 27),
                ads_channel=pins.get("ads1115_channel", 0),
            )
            logger.info("Hardware sensor reader initialized")
            return reader
        except Exception as e:
            logger.error(f"Hardware init failed, falling back to simulation: {e}")
            return SimulatedSensorReader()

    if use_hardware and not _HW_AVAILABLE:
        logger.warning(f"Pi mode requested but hardware unavailable: {_HW_ERROR}")

    return SimulatedSensorReader()
