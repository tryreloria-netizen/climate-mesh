# Climate Mesh - Decentralized Climate Monitoring System

A decentralized climate monitoring system that simulates 20 environmental sensor nodes, uses AI (Isolation Forest) to detect anomalies, calculates risk scores, and displays everything on a real-time Streamlit dashboard. Supports real Raspberry Pi 5 hardware sensors alongside simulation.

## Setup

```bash
cd climate-mesh
pip install -r requirements.txt
```

## Usage

Open two terminals:

**Terminal 1 — Simulation + Risk Engine:**
```bash
python run.py
```

**Terminal 2 — Dashboard:**
```bash
python -m streamlit run dashboard/app.py
```

### Sensor Mode Override

```bash
python run.py --mode simulation   # Force simulation only (default on PC)
python run.py --mode pi           # Force hardware sensors
python run.py --mode auto         # Auto-detect (default)
```

## Architecture

- **20 Simulated Nodes:** 5 river, 5 forest, 5 urban, 5 residential
- **Pi Sensor Nodes:** Real hardware nodes (PI-01, etc.) run alongside simulation
- **SQLite (WAL mode):** Shared data bus for concurrent read/write
- **Isolation Forest AI:** Trained on 2000 synthetic samples, detects anomalies in real-time
- **Risk Engine:** Calculates 0-100 risk scores with 4 sub-components + AI multiplier
- **Streamlit Dashboard:** Auto-refreshing with demo controls, charts, and alerts

## Demo Scenarios

Use the dashboard buttons to trigger:
- **Flood:** River water levels surge, humidity increases
- **Heatwave:** Temperatures spike, humidity drops, AQI rises
- **Smog:** Air quality degrades dramatically in urban/residential areas

## Raspberry Pi 5 Setup

### Hardware

| Sensor | Purpose | Connection |
|--------|---------|------------|
| DHT22 | Temperature + Humidity | GPIO 4 (data pin) |
| MQ-135 + ADS1115 | Air Quality (AQI) | I2C (SDA/SCL), Channel 0 |
| HC-SR04 | Water Level (ultrasonic) | GPIO 17 (trigger), GPIO 27 (echo) |

### Wiring

```
DHT22:     VCC -> 3.3V, GND -> GND, DATA -> GPIO 4
ADS1115:   VCC -> 3.3V, GND -> GND, SDA -> GPIO 2, SCL -> GPIO 3
MQ-135:    VCC -> 5V, GND -> GND, AOUT -> ADS1115 A0
HC-SR04:   VCC -> 5V, GND -> GND, TRIG -> GPIO 17, ECHO -> GPIO 27
           (Use voltage divider on ECHO: 1kΩ + 2kΩ to bring 5V down to 3.3V)
```

### Pi Software Setup

```bash
pip install -r requirements.txt
pip install adafruit-circuitpython-dht adafruit-circuitpython-ads1x15 RPi.GPIO
```

### Configuration

Edit `data/sensor_config.json` to set pin numbers and mode:

```json
{
    "mode": "auto",
    "pi_nodes": [
        {
            "node_id": "PI-01",
            "environment": "residential",
            "dht22_pin": 4,
            "hcsr04_trigger_pin": 17,
            "hcsr04_echo_pin": 27,
            "ads1115_channel": 0,
            "poll_interval_seconds": 2
        }
    ]
}
```

The system auto-detects whether it's running on a Pi. On a regular PC, it runs in pure simulation mode with no errors.

## Project Structure

```
climate-mesh/
    run.py                       # Launcher (--mode flag)
    requirements.txt             # Dependencies
    data/
        database.py              # SQLite helpers
        sensor_config.json       # Pi sensor configuration
    simulation/
        simulate_nodes.py        # 20 virtual sensors + Pi sensor loop
    backend/
        risk_engine.py           # Risk calculator
    ai/
        anomaly_model.py         # Isolation Forest
    dashboard/
        app.py                   # Streamlit dashboard
    sensors/
        read_sensors.py          # Pi hardware + simulation fallback
```
