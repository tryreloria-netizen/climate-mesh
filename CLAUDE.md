# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Climate Mesh is a decentralised climate-monitoring and AI early-warning system that runs on a Raspberry Pi 5. It models 20 named London/Harrow nodes, scores each one's climate risk 0–100, detects anomalies with an explainable Isolation Forest, escalates correlated events across adjacent nodes (mesh correlation), and raises plain-English alerts with action playbooks. A 7-tab Streamlit dashboard reads from a shared SQLite database.

**Sensor-ready, not sensor-dependent.** The full pipeline works with no physical sensors and (optionally) no internet. Every reading is labelled with its `source` (`simulation` / `demo` / `api` / `hardware`); simulated data is never presented as hardware data.

## Commands

```bash
pip install -r requirements.txt

# Engine (Terminal 1)
python run.py --mode simulation                       # offline default
python run.py --mode demo --scenario flood --judge-mode   # best for screenshots
python run.py --mode api                              # live Open-Meteo (falls back)
python run.py --mode hardware                         # physical sensor (falls back)
python run.py --mode auto                             # hardware -> api -> simulation
python run.py --mode demo --scenario flood --once     # one cycle (CI)

# Dashboard (Terminal 2)
python -m streamlit run dashboard/app.py

# Tests / evidence
pytest
python scripts/smoke_test.py
python scripts/run_validation.py --mode demo --scenario flood
python scripts/export_evidence.py
python scripts/reset_demo_db.py
```

Modes: `simulation`, `demo`, `api`, `hardware`, `auto`. Scenarios: `normal`, `flood`, `heatwave`, `smog`, `storm`. `--judge-mode` freezes the clock for deterministic, screenshot-stable output.

## Architecture

Two processes share a SQLite database (WAL mode) as a message bus:

**Engine (`run.py`)** runs three async tasks: a sensor loop (an adapter produces one canonical reading per node each tick and inserts them), `run_risk_engine` (scores every node every 3s and writes risk + alerts), and a cleanup loop (purges data older than 30 min). `--once` runs a single synchronous cycle for tests/CI.

**Dashboard (`dashboard/app.py`)** is a pure reader: 7 tabs, auto-refresh via `time.sleep(2)` + `st.rerun()`. Live scenario buttons write `data/demo_control.json`, which the engine's sensor loop reads each tick.

## The canonical reading contract

The core design idea: **every data source emits the same reading dict** (see `sensors/base.py:make_reading` / `MEASUREMENT_FIELDS`). Keys: `node_id, node_name, environment, latitude, longitude, temperature, humidity, air_quality, water_level, wind_speed, wind_chill, heat_index, barometric_pressure, source, is_simulated, quality_flag, scenario, timestamp`. The risk engine, AI, database, and dashboard never branch on where a reading came from. To add a sensor, write one adapter — nothing else changes.

Adapters (`sensors/`): `SimulatedAdapter` (simulation/demo), `ApiAdapter` (live Open-Meteo, raises `ApiUnavailable` → caller falls back), `VernierAdapter` (one physical node over a simulated mesh; never crashes without hardware). `sensors/__init__.py:create_adapter(mode)` is the factory and owns all fallback decisions, returning `(adapter, notes)`.

## Nodes & scenarios

`config/nodes.py` defines 20 nodes with real coordinates and a distance-based mesh neighbour map (`NEIGHBOURS`, ≤6 km). Environments: `school, river, residential, urban, park`. `simulation/scenarios.py` holds per-environment deltas for each scenario; `simulation/engine.py` generates values (daily cycle + noise + gradual scenario ramp + neighbour correlation). Deterministic mode (demo/judge) seeds RNG per node so screenshots are stable.

## Risk model

`backend/risk_engine.py`: six 0–100 hazard sub-scores (temp, humidity, AQI, water, wind, pressure) → base = `worst + 0.20 * sum(rest)`, capped 100 → `× AI multiplier (1.0–1.5)` `× mesh multiplier (1.2 if ≥2 neighbours elevated)`. Levels: SAFE <30, MODERATE 30–60, WARNING 60–80, CRITICAL 80+. Each result carries `top_factors`, `correlated`, and a plain-English `explanation`. Alerts are cooldown-gated (45 s; re-fire only on severity change) and carry a `playbook` from `backend/playbooks.py`.

## Database

`data/database.py` is the only module that knows table shapes: `sensor_readings`, `risk_scores` (with sub-scores, multipliers, `top_factors` JSON, `explanation`), `alerts` (with `playbook`), and `run_meta` (for evidence). Point the DB elsewhere with the `CLIMATE_MESH_DB` env var (tests and scripts use a temp file).

## Tests

`pytest` (33 tests in `tests/`). `conftest.py` pins an isolated temp DB and resets it per test. Coverage: reading shape, risk bounds/thresholds, scenario effects, mesh correlation, DB round-trips, alert cooldown, hardware-fallback-never-crashes.

## Honesty rules (do not regress)

- Never fabricate physical-sensor data. Anything not from real hardware is `is_simulated = True`.
- Always keep the `source` and `quality_flag` on every reading and in exports.
- It's a two-person team (Leo & Luis) — see `docs/writeup_corrections.md`.
