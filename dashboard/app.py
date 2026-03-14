"""Streamlit dashboard for Climate Mesh."""

import json
import time
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.database import (
    init_db, get_latest_readings_per_node, get_risk_scores,
    get_alerts, get_node_history,
)

DEMO_CONTROL_PATH = Path(__file__).parent.parent / "data" / "demo_control.json"

# Page config
st.set_page_config(
    page_title="Climate Mesh Dashboard",
    page_icon="🌍",
    layout="wide",
)

# Initialize DB connection for dashboard process
init_db()


# --- Demo Control ---
def _write_demo_control(scenario: str | None):
    DEMO_CONTROL_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_CONTROL_PATH.write_text(json.dumps({"scenario": scenario}))


st.title("Climate Mesh Dashboard")

# Demo control buttons
cols = st.columns(5)
with cols[0]:
    if st.button("Trigger Flood", type="primary", use_container_width=True):
        _write_demo_control("flood")
        st.toast("Flood scenario activated!")
with cols[1]:
    if st.button("Trigger Heatwave", type="primary", use_container_width=True):
        _write_demo_control("heatwave")
        st.toast("Heatwave scenario activated!")
with cols[2]:
    if st.button("Trigger Smog", type="primary", use_container_width=True):
        _write_demo_control("smog")
        st.toast("Smog scenario activated!")
with cols[3]:
    if st.button("Stop Scenario", type="secondary", use_container_width=True):
        _write_demo_control(None)
        st.toast("Scenario stopped — returning to normal")
with cols[4]:
    # Show active scenario
    try:
        ctrl = json.loads(DEMO_CONTROL_PATH.read_text()) if DEMO_CONTROL_PATH.exists() else {}
        active = ctrl.get("scenario")
        if active:
            st.warning(f"Active: {active.upper()}")
        else:
            st.success("Normal conditions")
    except Exception:
        st.info("No scenario")

st.divider()

# --- Fetch data ---
readings = get_latest_readings_per_node()
risks = get_risk_scores()
alerts = get_alerts(limit=30)

readings_df = pd.DataFrame(readings) if readings else pd.DataFrame()
risks_df = pd.DataFrame(risks) if risks else pd.DataFrame()
alerts_df = pd.DataFrame(alerts) if alerts else pd.DataFrame()

# --- Build source map (node_id -> "hardware" or "simulation") ---
source_map = {}
if not readings_df.empty and "source" in readings_df.columns:
    source_map = dict(zip(readings_df["node_id"], readings_df["source"]))

live_count = sum(1 for s in source_map.values() if s == "hardware")

# --- Sidebar: Node list with risk indicators ---
with st.sidebar:
    st.header("Sensor Nodes")

    if live_count > 0:
        st.success(f"📡 {live_count} live sensor(s) connected")

    if not risks_df.empty:
        for _, row in risks_df.iterrows():
            level = row["level"]
            color_map = {"safe": "🟢", "moderate": "🟡", "warning": "🟠", "critical": "🔴"}
            icon = color_map.get(level, "⚪")
            node_source = source_map.get(row["node_id"], "simulation")
            live_tag = " `[LIVE]`" if node_source == "hardware" else ""
            st.markdown(f"{icon} **{row['node_id']}**{live_tag} — {row['score']:.0f}/100 ({level})")
    else:
        st.info("Waiting for data... Make sure `python run.py` is running.")

    st.divider()
    st.caption("Climate Mesh v1.0")
    st.caption("Auto-refreshes every 2s")

# --- Tabs ---
tab_overview, tab_nodes, tab_ai = st.tabs(["Overview", "Node Details", "AI Insights"])

# === OVERVIEW TAB ===
with tab_overview:
    if not readings_df.empty and not risks_df.empty:
        # KPI metrics
        m1, m2, m3, m4, m5 = st.columns(5)
        avg_risk = risks_df["score"].mean()
        critical_count = len(risks_df[risks_df["level"] == "critical"])
        avg_temp = readings_df["temperature"].mean()
        avg_aqi = readings_df["air_quality"].mean()

        m1.metric("Avg Risk Score", f"{avg_risk:.1f}/100")
        m2.metric("Critical Nodes", f"{critical_count}/{len(risks_df)}")
        m3.metric("Avg Temperature", f"{avg_temp:.1f}°C")
        m4.metric("Avg AQI", f"{avg_aqi:.0f}")
        m5.metric("Live Sensors", f"{live_count}/{len(readings_df)}")

        st.subheader("Risk Score Heatmap")

        # Scatter plot as risk visualization
        merged = readings_df.merge(risks_df[["node_id", "score", "level"]], on="node_id", how="left")
        if not merged.empty:
            # Create grid positions for nodes
            merged["node_num"] = merged["node_id"].str.extract(r"(\d+)$").astype(int)

            # Add source info for marker differentiation
            if "source" in merged.columns:
                merged["data_source"] = merged["source"].apply(
                    lambda s: "Live Hardware" if s == "hardware" else "Simulation"
                )
            else:
                merged["data_source"] = "Simulation"

            fig = px.scatter(
                merged,
                x="node_num",
                y="environment",
                size="score",
                color="score",
                symbol="data_source",
                color_continuous_scale=["green", "yellow", "orange", "red"],
                range_color=[0, 100],
                hover_data=["node_id", "temperature", "humidity", "air_quality", "water_level"],
                size_max=40,
                title="Node Risk Scores by Environment",
            )
            fig.update_layout(
                xaxis_title="Node Number",
                yaxis_title="Environment",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Alert feed
        st.subheader("Recent Alerts")
        if not alerts_df.empty:
            for _, alert in alerts_df.head(10).iterrows():
                severity = alert["severity"]
                icon = "🔴" if severity == "critical" else "🟠" if severity == "warning" else "🟡"
                ts = alert["timestamp"].split("T")[1].split(".")[0] if "T" in alert["timestamp"] else alert["timestamp"]
                st.markdown(f"{icon} **[{ts}]** `{alert['node_id']}` — {alert['message']}")
        else:
            st.info("No alerts yet")
    else:
        st.info("Waiting for sensor data... Make sure `python run.py` is running in another terminal.")

# === NODE DETAILS TAB ===
with tab_nodes:
    if not readings_df.empty:
        node_ids = sorted(readings_df["node_id"].tolist())
        selected_node = st.selectbox("Select Node", node_ids)

        if selected_node:
            # Data source indicator
            node_source = source_map.get(selected_node, "simulation")
            if node_source == "hardware":
                st.success("📡 Data Source: **Real Hardware** (DHT22 / MQ-135 / HC-SR04)")
            else:
                st.info("💻 Data Source: **Simulation** (synthetic sensor data)")

            # Current reading
            node_reading = readings_df[readings_df["node_id"] == selected_node].iloc[0]
            node_risk = risks_df[risks_df["node_id"] == selected_node]

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Temperature", f"{node_reading['temperature']:.1f}°C")
            c2.metric("Humidity", f"{node_reading['humidity']:.1f}%")
            c3.metric("Air Quality", f"{node_reading['air_quality']:.0f} AQI")
            c4.metric("Water Level", f"{node_reading['water_level']:.2f}m")

            if not node_risk.empty:
                risk_row = node_risk.iloc[0]
                st.metric("Risk Score", f"{risk_row['score']:.1f}/100 ({risk_row['level']})")

            # Time series charts
            history = get_node_history(selected_node, minutes=10)
            if history:
                hist_df = pd.DataFrame(history)
                hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

                st.subheader("Sensor History (last 10 min)")
                for sensor, unit in [("temperature", "°C"), ("humidity", "%"),
                                     ("air_quality", "AQI"), ("water_level", "m")]:
                    fig = px.line(
                        hist_df, x="timestamp", y=sensor,
                        title=f"{sensor.replace('_', ' ').title()} ({unit})",
                    )
                    fig.update_layout(height=250, margin=dict(t=30, b=20))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No history yet — data accumulates over time")
    else:
        st.info("Waiting for sensor data...")

# === AI INSIGHTS TAB ===
with tab_ai:
    st.subheader("AI Anomaly Detection")
    st.markdown("""
    The anomaly detection system uses an **Isolation Forest** algorithm trained on
    2000 synthetic normal sensor readings. It identifies unusual patterns across
    temperature, humidity, air quality, and water level simultaneously.
    """)

    if not risks_df.empty:
        # Show nodes with highest AI multiplier (most anomalous)
        anomalous = risks_df[risks_df["ai_multiplier"] > 1.0].sort_values("ai_multiplier", ascending=False)

        if not anomalous.empty:
            st.subheader("Detected Anomalies")
            for _, row in anomalous.iterrows():
                boost = (row["ai_multiplier"] - 1.0) * 100
                node_source = source_map.get(row["node_id"], "simulation")
                live_tag = " 📡" if node_source == "hardware" else ""
                st.markdown(
                    f"**{row['node_id']}**{live_tag} — AI boost: +{boost:.0f}% | "
                    f"Risk: {row['score']:.1f}/100"
                )
        else:
            st.success("No anomalies detected — all readings within normal parameters")

        # Anomaly frequency chart
        st.subheader("Risk Distribution")
        fig = px.histogram(
            risks_df, x="score", nbins=20,
            color_discrete_sequence=["#FF6B6B"],
            title="Distribution of Risk Scores Across All Nodes",
        )
        fig.update_layout(
            xaxis_title="Risk Score",
            yaxis_title="Number of Nodes",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Sub-score breakdown
        st.subheader("Risk Sub-Score Breakdown")
        sub_cols = ["temp_sub", "humidity_sub", "aqi_sub", "water_sub"]
        sub_labels = ["Temperature", "Humidity", "Air Quality", "Water Level"]
        avg_subs = [risks_df[c].mean() for c in sub_cols]

        fig = go.Figure(data=[go.Bar(
            x=sub_labels, y=avg_subs,
            marker_color=["#FF6B6B", "#4ECDC4", "#95E1D3", "#3498DB"],
        )])
        fig.update_layout(
            title="Average Sub-Scores (0-25 each)",
            yaxis_range=[0, 25],
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Hardware vs Simulation comparison (if live nodes exist)
        if live_count > 0 and "source" in readings_df.columns:
            st.subheader("Hardware vs Simulation Comparison")
            hw_df = readings_df[readings_df["source"] == "hardware"]
            sim_df = readings_df[readings_df["source"] == "simulation"]

            for sensor, unit in [("temperature", "°C"), ("humidity", "%"),
                                 ("air_quality", "AQI"), ("water_level", "m")]:
                col1, col2 = st.columns(2)
                hw_val = hw_df[sensor].mean() if not hw_df.empty else 0
                sim_val = sim_df[sensor].mean() if not sim_df.empty else 0
                col1.metric(f"Hardware Avg {sensor.replace('_', ' ').title()}", f"{hw_val:.1f} {unit}")
                col2.metric(f"Simulation Avg {sensor.replace('_', ' ').title()}", f"{sim_val:.1f} {unit}")
    else:
        st.info("Waiting for risk data...")

# --- Auto-refresh ---
time.sleep(2)
st.rerun()
