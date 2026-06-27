# Write-up corrections

These are accuracy and honesty corrections to apply to the project write-up
(*Climate Mesh Write Up v2*). The competition is strengthened — not weakened — by
being precise about what runs today versus what is planned. Judges reward
reproducibility and honesty.

## 1. Team size: "both of us", not "three"

The team is **two students — Leo and Luis**. Replace every accidental "three of
us" / "all three of us" / "three students" with **"both of us" / "the two of us"
/ "two students"**.

- ❌ "all three of us debugged it together"
  → ✅ "both of us debugged it together"
- ❌ "built by three students"
  → ✅ "built by two students"

## 2. Separate working simulation/API mode from future hardware validation

Be explicit about the boundary between **what runs now** and **what is planned**:

- **Working today:** the complete pipeline — simulation and optional live
  Open-Meteo API data, the Isolation Forest model, the risk engine with mesh
  correlation, alerts with playbooks, the dashboard, and reproducible evidence
  export. This needs **no physical sensors**.
- **Planned / future:** physical Vernier Go Direct sensor readings validated
  against the digital twin. This has **not** happened yet.

Any performance figure that was produced from simulated or API data must say so.
Do **not** present simulated results as hardware-measured results. Where the
original write-up has a "Hardware" column marked "Not yet measured", keep it
honest — those rows are genuinely not yet measured on hardware.

## 3. Do not claim unavailable sensors were used

The physical environmental sensors are **not currently available/connected**.
Remove or reword any sentence implying the GDX-WTHR, GDX-CO2, or GDX-WQ sensors
were producing live readings during testing.

- ❌ "the GDX-WTHR is connected and producing live hardware readings"
  → ✅ "the GDX-WTHR pathway is implemented and ready; until it is connected,
       this node uses clearly-labelled simulated/API data"
- ❌ "its hardware readings appear as node PI-01"
  → ✅ "when connected, its hardware readings will appear for the chosen node and
       are labelled `source = hardware`"

## 4. Say "sensor-ready", not "fully deployed"

Frame the project as **sensor-ready, not sensor-dependent**. The standard line to
use anywhere the write-up implies sensors are physically deployed:

> "Physical sensor support is hardware-ready but not required for the current
> demo. Until sensors are connected, Climate Mesh uses simulated and/or API data,
> and every reading is labelled with its source."

## 5. Honesty as a strength

Where the write-up makes external claims, keep the existing honest hedges (e.g.
"we have not independently verified this figure" on market-size statistics) and
add the same care elsewhere. Every reading in the live system already carries a
`source` and a `quality_flag`, and the evidence export preserves them — so the
reproducibility claim is backed by the code, not just asserted.

## Summary of edits to make in the document

| Location / theme | Change |
|---|---|
| Team collaboration section | "all three of us" → "both of us" |
| World Benefit section | "three students" → "two students" |
| Hardware / "How it works" | Reword "connected and producing live readings" to the sensor-ready wording above |
| Metrics tables | Ensure simulated/API results are labelled as such; leave hardware rows as "Not yet measured" |
| Throughout | Prefer "sensor-ready" / "when connected" over present-tense deployment claims |
