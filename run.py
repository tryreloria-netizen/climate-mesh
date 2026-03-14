"""Climate Mesh Launcher — starts simulation and risk engine."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from data.database import init_db, clear_old_data
from ai.anomaly_model import AnomalyDetector
from simulation.simulate_nodes import run_simulation, run_pi_sensors
from backend.risk_engine import run_risk_engine


async def periodic_cleanup():
    """Clear old data every 5 minutes."""
    while True:
        await asyncio.sleep(300)
        clear_old_data(minutes=30)
        print("[Cleanup] Old data cleared")


async def main():
    print("=" * 50)
    print("  Climate Mesh — Decentralized Climate Monitor")
    print("=" * 50)

    # Initialize database
    init_db()
    print("[DB] Database initialized")

    # Train AI model
    detector = AnomalyDetector()
    detector.train()

    # Run simulation + risk engine concurrently
    print("[System] Starting simulation and risk engine...")
    print("[System] Open dashboard in another terminal:")
    print("         python -m streamlit run dashboard/app.py")
    print("-" * 50)

    await asyncio.gather(
        run_simulation(),
        run_pi_sensors(),
        run_risk_engine(detector),
        periodic_cleanup(),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Climate Mesh Launcher")
    parser.add_argument("--mode", choices=["auto", "pi", "simulation"], default=None,
                        help="Override sensor mode (default: read from sensor_config.json)")
    args = parser.parse_args()

    if args.mode:
        os.environ["CLIMATE_MESH_MODE"] = args.mode

    asyncio.run(main())
