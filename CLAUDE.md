# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Climate Mesh is a decentralized climate monitoring system that simulates 20 environmental sensor nodes, detects anomalies via Isolation Forest, calculates risk scores, and displays a real-time Streamlit dashboard. It also supports hardware sensors (Vernier GDX-WTHR for temperature/humidity, MQ-7 Flying Fish for CO-based air quality) alongside simulation.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulation + risk engine (Terminal 1)
python run.py

# Run dashboard (Terminal 2)
python -m streamlit run dashboard/app.py

# Force a specific sensor mode
python run.py --mode simulation   # Simulation only (default on PC)
python run.py --mode pi           # Hardware sensors
python run.py --mode auto         # Auto-detect
```

There are no tests or linting configured in this project.

## Architecture

The system runs as two separate processes that communicate through a shared SQLite database (WAL mode):

**Process 1 (`run.py`)** — launches four concurrent async tasks via `asyncio.gather`:
- `run_simulation()` — generates readings every 2s for 20 nodes (5 each: river, forest, urban, residential)
- `run_pi_sensors()` — reads real hardware sensors if configured, inserts alongside simulated data
- `run_risk_engine()` — every 3s, reads latest per-node readings, calculates risk scores (4 sub-scores 0-25 each + AI anomaly multiplier 1.0-1.5x), writes alerts
- `periodic_cleanup()` — purges data older than 30 minutes every 5 minutes

**Process 2 (`dashboard/app.py`)** — Streamlit dashboard that reads from the same SQLite DB, auto-refreshes every 2s via `time.sleep(2)` + `st.rerun()`.

**Demo scenarios** (flood, heatwave, smog) are controlled via a `data/demo_control.json` file — the dashboard writes it, the simulation reads it.

## Node ID Convention

Simulated nodes use environment-prefixed IDs: `RV-01`..`RV-05` (river), `FR-01`..`FR-05` (forest), `UB-01`..`UB-05` (urban), `RS-01`..`RS-05` (residential). Hardware Pi nodes use `PI-01`, etc.

## Vendored Packages

The `packages/` directory contains pre-downloaded `.whl` files for offline installation (streamlit, pandas, numpy, etc.).

## Key Design Decisions

- **SQLite as message bus**: All inter-process communication goes through `data/climate_mesh.db`. The `data/database.py` module provides thread-local connections with WAL mode and busy timeout.
- **Sensor mode override**: The `CLIMATE_MESH_MODE` env var (set by `--mode` flag) takes priority over `data/sensor_config.json`. The `sensors/read_sensors.py` factory returns either `VernierMQ7SensorReader` (GDX-WTHR + MQ-7 via ADS1115) or `SimulatedSensorReader`. Water level is always simulated since neither hardware sensor provides it.
- **AI model trains on synthetic data**: `AnomalyDetector.train()` generates 2000 synthetic normal samples at startup — no external training data needed.
- **Risk score**: Sum of 4 sub-scores (temp, humidity, AQI, water level, each 0-25) multiplied by AI anomaly factor. Levels: safe (<30), moderate (30-59), warning (60-79), critical (80+).
