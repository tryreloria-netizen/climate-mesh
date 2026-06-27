# Climate Mesh — Project Development Log

## Project overview

Climate Mesh is a Raspberry Pi 5 climate-monitoring and AI early-warning system
built by two students — **Leo** (project lead and AI) and **Luis** (software,
dashboard and hardware) — at Harrow School. It models a mesh of community
climate nodes, scores environmental hazard in real time, and raises explainable
early-warning alerts with practical community action playbooks.

The project's guiding principle is **"sensor-ready, not sensor-dependent"**: the
full pipeline works today using simulated and/or live-API data, and physical
sensors are a clean drop-in for the future. **No physical sensors are connected
yet — every current result uses simulation or live-API data.**

### How it runs

```bash
python run.py --mode <MODE> --scenario <SCENARIO> [--judge-mode]
python -m streamlit run dashboard/app.py   # separate terminal
```

- **Modes:** `simulation` (default, offline synthetic), `demo` (deterministic,
  screenshot-ready), `api` (live Open-Meteo, falls back to simulation if
  offline), `hardware` (physical Vernier sensor over a simulated mesh, falls
  back if absent), `auto` (hardware → API → simulation).
- **Scenarios:** `normal`, `flood`, `heatwave`, `smog`, `storm`.
- **Best demo command:** `python run.py --mode demo --scenario flood --judge-mode`

## From v1 to v2

### v1 (initial prototype)
- Synthetic-only data.
- Four generic environments.
- A single, basic risk calculation with little explanation.

### v2 (competition-upgrade)
- **Operating modes** (`simulation` / `demo` / `api` / `hardware` / `auto`) with
  graceful fallback, so a demo never fails.
- **Sensor-ready adapter architecture** in `sensors/` (`base.py`,
  `simulated_adapter.py`, `api_adapter.py`, `vernier_adapter.py`,
  `hardware_status.py`) — every source emits the same canonical reading shape.
- **20 named London/Harrow nodes** with real coordinates across five
  environments (school, river, residential, urban, park).
- **Explainable risk engine** (`backend/risk_engine.py`): six 0–100 hazard
  sub-scores combined as *worst hazard + 20% of the rest*, then multiplied by an
  Isolation-Forest anomaly multiplier and a mesh-correlation multiplier (1.2×
  when ≥2 adjacent nodes show the same trend). Bands: SAFE / MODERATE / WARNING
  / CRITICAL.
- **Action playbooks** (`backend/playbooks.py`) and plain-English alert
  explanations, **cooldown rate-limited** (45 s, re-firing only on severity
  change).
- **Seven-tab dashboard:** Live Map, Network Overview, Node Detail, AI
  Explainability, Evidence & Validation, Hardware Readiness, Competition Pitch.
- **Evidence scripts** (`scripts/`): `reset_demo_db.py`, `export_evidence.py`,
  `run_validation.py`, `smoke_test.py`.
- **pytest suite:** 33 tests, all passing (`tests/`).
- **Honest documentation** throughout.

## Log entries

### 2026-06-27 — competition-upgrade
Completed the v2 competition upgrade. Consolidated the operating-mode system,
finalised the 20-node London/Harrow mesh, wired the explainable risk engine with
AI anomaly detection and mesh correlation, added community action playbooks with
alert cooldown, and built out the seven-tab Streamlit dashboard. Added the
evidence-export and validation scripts and confirmed the full pytest suite (33
tests) passes. Authored the honest project documentation set. Prepared the repo
for push to `github.com/tryreloria-netizen/climate-mesh` on branch
`competition-upgrade`.

**Honesty note:** physical sensors are not yet connected. All results to date are
produced with simulation or live-API data; the Vernier hardware pathway is
implemented and ready but untested against a physical device.

## Competition context
PA Raspberry Pi Competition 2026, theme *"Building a Positive Human Future"*
(Safer Societies & Sustainable World). Also targeting The Earth Prize, CREST
Awards, Big Bang, TeenTech, Conrad Challenge and Regeneron ISEF.
