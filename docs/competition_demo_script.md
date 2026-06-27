# Climate Mesh — Competition Demo Script (~3–5 minutes)

A timed, spoken script for walking a judge through a live demo. Spoken lines are
in quotes; **[stage directions]** tell you what to do and point at. Run on the
Raspberry Pi with the dashboard already open in a browser tab.

---

## 0:00–0:40 — The problem
> "We're Leo and Luis, two students at Harrow School. Harrow sits beside the
> Yeading Brook, but the nearest official flood gauge is kilometres away — so by
> the time a warning reaches the community, water is already rising. There's a
> gap between where the flooding happens and where it's measured."

> "Climate Mesh fills that gap: a low-cost mesh of community climate nodes on a
> Raspberry Pi, with an AI that turns raw readings into explainable early
> warnings and practical actions."

## 0:40–1:10 — Start the system
**[Run in the engine terminal]**
```bash
python run.py --mode demo --scenario flood --judge-mode
```
> "I'm starting in demo flood judge-mode — a deterministic state so what you see
> is exactly repeatable. Everything today runs on simulated and live-API data:
> the system is sensor-ready, not sensor-dependent."

## 1:10–1:50 — The Live Map
**[Switch to the dashboard, Live Map tab]**
> "Here are 20 real London and Harrow nodes — Harrow School, Yeading Brook, the
> River Colne, Brent Reservoir, and more — each coloured by risk band: green is
> safe, through to red for critical."

**[Point at the cluster near Yeading Brook turning amber/red]**

## 1:50–2:30 — Trigger each scenario
**[Briefly switch scenarios to show range]**
```bash
python run.py --mode demo --scenario heatwave --judge-mode
python run.py --mode demo --scenario smog --judge-mode
python run.py --mode demo --scenario storm --judge-mode
```
> "The same engine handles flood, heatwave, smog and storm — six hazard
> sub-scores combine into one risk number, so different threats are comparable."

**[Return to flood for the rest of the demo.]**

## 2:30–3:10 — An explainable alert + playbook
**[Point at a CRITICAL alert in the terminal / Node Detail tab]**
> "This isn't a black box. The alert says *why* in plain English — water level
> and pressure are driving it — and it comes with a community action playbook:
> what residents and the school should do right now. Alerts are rate-limited, so
> they only re-fire when severity actually changes."

## 3:10–3:50 — AI Explainability + mesh correlation
**[AI Explainability tab]**
> "An Isolation Forest flags anomalies and applies a multiplier on top of the
> base score. And because this is a *mesh*, when two or more neighbouring nodes
> show the same trend we apply a 1.2× correlation boost."

**[Point at the Yeading Brook neighbours rising together]**
> "Around Yeading Brook, several adjacent nodes are rising together — that
> agreement is what raises confidence in a real flood, not a glitch."

## 3:50–4:30 — Evidence + export
**[Evidence & Validation tab, then the terminal]**
```bash
python scripts/export_evidence.py
```
> "Everything is auditable. We export readings, risk scores and alerts to CSV,
> plus a run summary JSON, and we validate them. 33 automated tests all pass."

## 4:30–5:00 — Honest close
> "To be completely honest: no physical sensors are connected yet. Every result
> you've seen is simulation or live API data. But every source emits the same
> canonical reading, and our Vernier USB adapter is already written — so the day
> the sensors arrive, a physical node simply joins the mesh. Sensor-ready, not
> sensor-dependent. Thank you."
