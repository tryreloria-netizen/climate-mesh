# 🌍 Climate Mesh

**Decentralised climate monitoring & AI-powered early-warning mesh — runs on a Raspberry Pi 5.**

Climate Mesh is a network of 20 environmental "nodes" across Harrow and Greater
London. It scores each location's climate risk in real time, uses an explainable
AI anomaly model plus *mesh correlation* (nearby nodes confirming a trend) to
escalate genuine events, and raises plain-English alerts with suggested actions —
all on a single Raspberry Pi with no cloud subscription.

> **Honest by design — sensor-ready, not sensor-dependent.**
> Physical sensor support is hardware-ready but **not required** for the current
> demo. Until sensors are connected, Climate Mesh uses clearly-labelled
> **simulated** and/or **live API** data. Every reading shows its source
> (`simulation` / `demo` / `api` / `hardware`) so nothing is ever overstated.

Built by **Leo & Luis** (Harrow School, Years 10–11) for the PA Raspberry Pi
Competition 2026 — theme *Building a Positive Human Future* (Safer Societies &
Sustainable World).

---

## What works right now

- ✅ 20 named London/Harrow nodes with real coordinates on a live risk map.
- ✅ Five demo scenarios: **normal, flood, heatwave, smog, storm**.
- ✅ 0–100 risk scores with **SAFE / MODERATE / WARNING / CRITICAL** levels.
- ✅ Explainable AI (Isolation Forest) + **mesh correlation** across adjacent nodes.
- ✅ Plain-English alerts with **community action playbooks**.
- ✅ A 7-tab Streamlit dashboard.
- ✅ Reproducible **evidence export** (CSV + JSON) for judges.
- ✅ `pytest` test suite (33 tests) and a one-command smoke test.
- ✅ Runs **fully offline, with no sensors**, on a Raspberry Pi 5.

## What is simulated vs real

| Mode | Data source | Internet? | Sensors? |
|------|-------------|-----------|----------|
| `simulation` | Realistic generated data (default) | No | No |
| `demo` | Deterministic, screenshot-stable data | No | No |
| `api` | **Live Open-Meteo** weather + air quality | Yes (falls back to simulation) | No |
| `hardware` | **Physical Vernier sensor** for one node, simulated mesh for the rest | No | Yes (falls back if absent) |
| `auto` | Detect hardware → else API → else simulation | Optional | Optional |

## What happens when physical sensors are added

The architecture is **sensor-ready**: every data source emits the *same* canonical
reading shape, so the risk engine, AI, dashboard, and database never change. When a
Vernier Go Direct Weather sensor is connected over USB, that node switches to
`source="hardware"` and its real readings are compared against the simulated/API
"digital twin" for the same location. See
[docs/hardware_integration_plan.md](docs/hardware_integration_plan.md).

---

## Quick start (any computer)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Sanity check (no sensors / no internet needed)
python scripts/smoke_test.py
pytest
```

**Run the demo — two terminals:**

```bash
# Terminal 1 — engine (best mode for screenshots/video)
python run.py --mode demo --scenario flood --judge-mode

# Terminal 2 — dashboard
python -m streamlit run dashboard/app.py
```

Then open the local Streamlit URL it prints (usually <http://localhost:8501>).

## Raspberry Pi 5 setup

```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip
git clone https://github.com/tryreloria-netizen/climate-mesh.git
cd climate-mesh
git checkout competition-upgrade        # until merged to the default branch

# One-command setup (creates .venv, installs deps, runs smoke test)
chmod +x setup_pi.sh && ./setup_pi.sh
```

Or do it manually with the Quick start steps above. Physical sensors are **not**
required — the demo runs on simulation.

## Run commands

```bash
python run.py --mode simulation                         # offline, default
python run.py --mode demo --scenario normal             # deterministic demo
python run.py --mode demo --scenario flood   --judge-mode
python run.py --mode demo --scenario heatwave --judge-mode
python run.py --mode demo --scenario smog    --judge-mode
python run.py --mode demo --scenario storm   --judge-mode
python run.py --mode api                                # live Open-Meteo data
python run.py --mode hardware                           # physical sensor (falls back)
python run.py --mode auto                               # detect hardware/API/sim
python run.py --mode demo --scenario flood --once       # one cycle, for CI
```

Scenarios can also be triggered live from the dashboard sidebar while the engine
runs.

## Screenshots to capture

The dashboard's 7 tabs are all screenshot-worthy — see
[docs/evidence_checklist.md](docs/evidence_checklist.md). In short:
**Live Map** (risk-coloured London nodes), **Network Overview** (KPIs + charts),
**Node Detail** (per-node readings, source label, risk breakdown), **AI
Explainability**, **Evidence & Validation**, **Hardware Readiness**, **Competition
Pitch**. Always note the **Mode** and **Data source** banner in each shot.

---

## Architecture (text diagram)

```
                 +------------------- run.py (engine process) -------------------+
                 |                                                               |
  Sensor adapter |  sensors/ -- simulated / api / vernier / hardware_status      |
  (one shape!)   |        every adapter -> the SAME canonical reading dict       |
                 |                         |                                     |
                 |                         v                                     |
                 |   ai/anomaly_model.py (Isolation Forest, explainable)         |
                 |                         |                                     |
                 |                         v                                     |
                 |   backend/risk_engine.py  -> 6 sub-scores -> base 0-100       |
                 |        x AI multiplier  x mesh-correlation multiplier         |
                 |        -> level, top factors, plain-English explanation       |
                 |        -> alerts (cooldown) + playbooks                       |
                 +-----------------------------+---------------------------------+
                                               |
                              data/database.py | SQLite (WAL) = message bus
                                               |
                 +-----------------------------v---------------------------------+
                 |  dashboard/app.py (Streamlit) — 7 tabs, reads the same DB     |
                 +---------------------------------------------------------------+
```

## File structure

```
climate-mesh/
  run.py                     # launcher: modes, scenarios, judge-mode, --once
  config/nodes.py            # 20 named London nodes + mesh neighbour map
  sensors/
    base.py                  # canonical reading shape + adapter base class
    simulated_adapter.py     # offline / demo data
    api_adapter.py           # live Open-Meteo data (falls back if offline)
    vernier_adapter.py       # physical Vernier sensor (falls back if absent)
    hardware_status.py       # sensor detection (never crashes)
  simulation/
    engine.py                # data generation: daily cycle, noise, scenarios
    scenarios.py             # flood / heatwave / smog / storm deltas
  ai/anomaly_model.py        # explainable Isolation Forest
  backend/
    risk_engine.py           # explainable scoring + mesh correlation + alerts
    playbooks.py             # community action playbooks per hazard
  data/database.py           # SQLite storage (readings, risk, alerts, runs)
  dashboard/app.py           # 7-tab Streamlit dashboard
  scripts/
    reset_demo_db.py         # wipe DB to a clean state
    export_evidence.py       # CSV + JSON evidence export
    run_validation.py        # one-command pass/fail validation
    smoke_test.py            # fast end-to-end check
  tests/                     # pytest suite (33 tests)
  docs/                      # project log, evidence checklist, demo script, etc.
```

## How the AI works

`ai/anomaly_model.py` trains an **Isolation Forest** on 2000 synthetic *normal*
samples at startup (no internet needed). For each reading it returns an anomaly
score (0–1), whether the reading is anomalous, and the channels deviating most
from the learned baseline. Unlike fixed thresholds, it flags an unusual
**combination** of values *before* any single channel crosses a hard limit. A
confirmed anomaly multiplies a node's risk by up to **1.5×**.

## How the risk score works

For each node the engine computes six 0–100 hazard sub-scores — temperature,
humidity, air quality, water level, wind, pressure — and combines them
(worst hazard + 20% of the rest) into a 0–100 **base score**. It then applies:

- **AI multiplier** (1.0–1.5×) when the Isolation Forest confirms an anomaly, and
- **Mesh multiplier** (1.2×) when **2+ adjacent nodes** show the same trend — a
  single spike is trusted less than a correlated regional event.

| Score | Level | Meaning |
|------:|-------|---------|
| 0–30  | SAFE | Within normal baseline |
| 30–60 | MODERATE | One factor drifting; advisory |
| 60–80 | WARNING | Confirmed anomaly on a node / correlated moderate readings |
| 80–100 | CRITICAL | Correlated anomaly across adjacent nodes |

Example alert:
> *Flood risk rising near Yeading Brook. Same trend seen across 4 nearby nodes.
> Risk score 100/100. Main contributors: water level, humidity, pressure drop.*
> **Suggested actions:** check and clear nearby drains; inspect low-lying paths;
> review the evacuation route.

## How to export evidence

```bash
# After running a demo for a little while:
python scripts/export_evidence.py
# -> evidence/readings.csv, risk_scores.csv, alerts.csv, run_summary.json
```

Each row keeps its `source` and `quality_flag`, so simulated/API/hardware data is
never confused. See [docs/evidence_checklist.md](docs/evidence_checklist.md).

## Troubleshooting

- **Dashboard says "No data yet"** → start the engine in another terminal:
  `python run.py --mode demo --scenario flood --judge-mode`.
- **`api` mode shows a fallback note** → no internet; it automatically uses
  simulation. This is expected and clearly labelled.
- **Map doesn't render** → the bundled Streamlit/Plotly versions use OpenStreetMap
  tiles (no API key). Ensure `pip install -r requirements.txt` completed.
- **`pytest: command not found`** → use `python -m pytest`.
- **Reset everything** → `python scripts/reset_demo_db.py`.

## Competition notes

Climate Mesh targets the PA Raspberry Pi Competition 2026 and a wider pipeline
(The Earth Prize, CREST Awards, Big Bang, TeenTech, Conrad Challenge, Regeneron
ISEF). Its competition strengths: an **evidence mode** for reproducible judging,
**explainable alerts**, a **sensor-ready-without-sensors** pipeline, **community
action playbooks**, **mesh correlation**, a **local digital twin**, and
**offline-first** operation. See [docs/competition_demo_script.md](docs/competition_demo_script.md).

## Tests

```bash
pytest                 # 33 tests
python scripts/smoke_test.py
python scripts/run_validation.py --mode demo --scenario flood
```

## Licence

Open source for educational use. Built by Leo & Luis, Harrow School.
