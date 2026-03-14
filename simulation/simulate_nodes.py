"""Virtual sensor node simulation for Climate Mesh."""

import asyncio
import json
import math
import random
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import insert_reading

DEMO_CONTROL_PATH = Path(__file__).parent.parent / "data" / "demo_control.json"

# 20 nodes: 5 per environment type
NODES = []
for env, prefix in [("river", "RV"), ("forest", "FR"), ("urban", "UB"), ("residential", "RS")]:
    for i in range(1, 6):
        NODES.append({
            "node_id": f"{prefix}-{i:02d}",
            "environment": env,
        })

# Base sensor values per environment
BASE_VALUES = {
    "river":       {"temperature": 22, "humidity": 75, "air_quality": 40,  "water_level": 2.0},
    "forest":      {"temperature": 20, "humidity": 70, "air_quality": 25,  "water_level": 0.5},
    "urban":       {"temperature": 28, "humidity": 45, "air_quality": 120, "water_level": 0.3},
    "residential": {"temperature": 25, "humidity": 55, "air_quality": 80,  "water_level": 0.4},
}

# Disaster scenario effects: which sensors get boosted and for which environments
DISASTER_EFFECTS = {
    "flood": {
        "river":       {"temperature": -2, "humidity": 25, "air_quality": 10, "water_level": 4.0},
        "forest":      {"temperature": -1, "humidity": 15, "air_quality": 5,  "water_level": 1.5},
        "urban":       {"temperature": -1, "humidity": 10, "air_quality": 5,  "water_level": 1.0},
        "residential": {"temperature": -1, "humidity": 15, "air_quality": 5,  "water_level": 2.0},
    },
    "heatwave": {
        "river":       {"temperature": 12, "humidity": -15, "air_quality": 30, "water_level": -0.5},
        "forest":      {"temperature": 15, "humidity": -20, "air_quality": 50, "water_level": -0.3},
        "urban":       {"temperature": 18, "humidity": -25, "air_quality": 80, "water_level": -0.1},
        "residential": {"temperature": 15, "humidity": -20, "air_quality": 60, "water_level": -0.1},
    },
    "smog": {
        "river":       {"temperature": 2,  "humidity": 5,  "air_quality": 100, "water_level": 0.0},
        "forest":      {"temperature": 2,  "humidity": 5,  "air_quality": 80,  "water_level": 0.0},
        "urban":       {"temperature": 3,  "humidity": -5, "air_quality": 250, "water_level": 0.0},
        "residential": {"temperature": 3,  "humidity": -5, "air_quality": 200, "water_level": 0.0},
    },
}


def _read_demo_control() -> dict:
    """Read the demo control file for active disaster scenario."""
    try:
        if DEMO_CONTROL_PATH.exists():
            return json.loads(DEMO_CONTROL_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        pass
    return {"scenario": None}


def _generate_reading(node: dict, tick: float, scenario: str | None) -> dict:
    """Generate a single sensor reading with variation and optional disaster effects."""
    env = node["environment"]
    base = BASE_VALUES[env]

    # Sinusoidal daily variation (compressed to ~60s cycle for demo)
    phase = math.sin(tick * 2 * math.pi / 60)

    values = {}
    for sensor, base_val in base.items():
        # Base + sinusoidal variation + random noise
        if sensor == "temperature":
            variation = phase * 3 + random.gauss(0, 0.5)
        elif sensor == "humidity":
            variation = -phase * 5 + random.gauss(0, 1)
        elif sensor == "air_quality":
            variation = phase * 10 + random.gauss(0, 3)
        else:  # water_level
            variation = phase * 0.2 + random.gauss(0, 0.05)

        value = base_val + variation

        # Apply disaster effects with gradual ramp-up
        if scenario and scenario in DISASTER_EFFECTS:
            effects = DISASTER_EFFECTS[scenario].get(env, {})
            # Ramp up over ~10 seconds for dramatic effect
            ramp = min(1.0, (tick % 60) / 10) if scenario else 0
            value += effects.get(sensor, 0) * ramp

        # Clamp values to reasonable ranges
        if sensor == "temperature":
            value = max(-10, min(60, value))
        elif sensor == "humidity":
            value = max(0, min(100, value))
        elif sensor == "air_quality":
            value = max(0, min(500, value))
        else:  # water_level
            value = max(0, min(10, value))

        values[sensor] = round(value, 2)

    return values


async def run_simulation():
    """Main simulation loop — generates readings every 2 seconds."""
    print(f"[Simulation] {len(NODES)} sensor nodes started")
    start_time = time.time()

    while True:
        tick = time.time() - start_time
        control = _read_demo_control()
        scenario = control.get("scenario")

        if scenario:
            print(f"[Simulation] Active scenario: {scenario}")

        for node in NODES:
            values = _generate_reading(node, tick, scenario)
            insert_reading(
                node_id=node["node_id"],
                environment=node["environment"],
                source="simulation",
                **values
            )

        await asyncio.sleep(2)


async def run_pi_sensors():
    """Read real Pi sensors and insert into database alongside simulated nodes."""
    from sensors.read_sensors import create_sensor_reader, load_config

    config = load_config()
    pi_nodes = config.get("pi_nodes", [])

    if not pi_nodes:
        print("[Pi Sensors] No Pi nodes configured — skipping hardware sensor loop")
        return

    readers = {}
    for node_conf in pi_nodes:
        node_id = node_conf.get("node_id", "PI-01")
        reader = create_sensor_reader(node_conf)
        readers[node_id] = (reader, node_conf)
        source_type = "HARDWARE" if type(reader).__name__ == "PiSensorReader" else "SIMULATED"
        print(f"[Pi Sensors] Node {node_id} initialized ({source_type})")

    try:
        while True:
            for node_id, (reader, node_conf) in readers.items():
                reading = await asyncio.to_thread(reader.read_all)
                env = node_conf.get("environment", "residential")

                # Replace None values with safe defaults
                defaults = {"temperature": 22.0, "humidity": 60.0,
                            "air_quality": 50.0, "water_level": 1.0}
                for key, default in defaults.items():
                    if reading.get(key) is None:
                        reading[key] = default

                insert_reading(
                    node_id=node_id,
                    environment=env,
                    temperature=reading["temperature"],
                    humidity=reading["humidity"],
                    air_quality=reading["air_quality"],
                    water_level=reading["water_level"],
                    source=reading.get("source", "simulation"),
                )

            interval = pi_nodes[0].get("poll_interval_seconds", 2)
            await asyncio.sleep(interval)
    finally:
        for node_id, (reader, _) in readers.items():
            reader.cleanup()
