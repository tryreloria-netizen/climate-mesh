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
- **Hardware Nodes:** GDX-WTHR (temp/humidity) + MQ-7 (CO/air quality) nodes run alongside simulation
- **SQLite (WAL mode):** Shared data bus for concurrent read/write
- **Isolation Forest AI:** Trained on 2000 synthetic samples, detects anomalies in real-time
- **Risk Engine:** Calculates 0-100 risk scores with 4 sub-components + AI multiplier
- **Streamlit Dashboard:** Auto-refreshing with demo controls, charts, and alerts

## Demo Scenarios

Use the dashboard buttons to trigger:
- **Flood:** River water levels surge, humidity increases
- **Heatwave:** Temperatures spike, humidity drops, AQI rises
- **Smog:** Air quality degrades dramatically in urban/residential areas

## Hardware Sensor Setup

### Sensors

| Sensor | Purpose | Connection |
|--------|---------|------------|
| Vernier GDX-WTHR | Temperature + Humidity | USB or Bluetooth (BLE) |
| MQ-7 Flying Fish + ADS1115 | Air Quality (CO-based AQI) | I2C (SDA/SCL), Channel 0 |

Water level is simulated when using hardware sensors (neither sensor provides it).

### Wiring (MQ-7)

```
ADS1115:   VCC -> 3.3V, GND -> GND, SDA -> GPIO 2, SCL -> GPIO 3
MQ-7:     VCC -> 5V, GND -> GND, AO -> ADS1115 A0
```

The GDX-WTHR connects via USB cable or Bluetooth — no GPIO wiring needed.

### Software Setup

```bash
pip install -r requirements.txt
pip install adafruit-circuitpython-ads1x15
```

You also need the `gdx` helper module from [VernierST/godirect-examples](https://github.com/VernierST/godirect-examples) — place the `gdx/` folder in the project root.

### Configuration

Edit `data/sensor_config.json` to set connection type and mode:

```json
{
    "mode": "auto",
    "pi_nodes": [
        {
            "node_id": "PI-01",
            "environment": "residential",
            "gdx_connection": "usb",
            "ads1115_channel": 0,
            "poll_interval_seconds": 2
        }
    ]
}
```

Set `gdx_connection` to `"ble"` for Bluetooth. The system auto-detects available hardware. On a regular PC without sensors, it runs in pure simulation mode.

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
        read_sensors.py          # GDX-WTHR + MQ-7 hardware + simulation fallback
```
