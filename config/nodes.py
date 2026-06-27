"""Climate Mesh node registry — 20 named London / Harrow-area locations.

Every data source (simulation, API, hardware) maps onto these nodes so the
risk engine, AI model, dashboard, and database never need to know where a
reading came from. Coordinates are real London locations; environment type
drives the baseline values used by the simulator and the risk weighting.
"""

from __future__ import annotations

import math

# Environment types used across the project.
ENVIRONMENTS = ("school", "river", "residential", "urban", "park")

# 20 named nodes. node_id is stable and human-readable; it is the primary key
# used everywhere else in the system.
NODES: list[dict] = [
    {"node_id": "HARROW-SCHOOL", "node_name": "Harrow School",       "environment": "school",      "latitude": 51.5730, "longitude": -0.3370},
    {"node_id": "YEADING-BROOK", "node_name": "Yeading Brook",       "environment": "river",       "latitude": 51.5530, "longitude": -0.3970},
    {"node_id": "RIVER-COLNE",   "node_name": "River Colne",         "environment": "river",       "latitude": 51.6160, "longitude": -0.4750},
    {"node_id": "BRENT-RES",     "node_name": "Brent Reservoir",     "environment": "river",       "latitude": 51.5750, "longitude": -0.2500},
    {"node_id": "HARROW-HILL",   "node_name": "Harrow-on-the-Hill",  "environment": "residential", "latitude": 51.5780, "longitude": -0.3340},
    {"node_id": "NORTH-HARROW",  "node_name": "North Harrow",        "environment": "residential", "latitude": 51.5850, "longitude": -0.3620},
    {"node_id": "SOUTH-HARROW",  "node_name": "South Harrow",        "environment": "residential", "latitude": 51.5630, "longitude": -0.3530},
    {"node_id": "WATFORD",       "node_name": "Watford",             "environment": "residential", "latitude": 51.6560, "longitude": -0.3960},
    {"node_id": "WEMBLEY",       "node_name": "Wembley",             "environment": "urban",       "latitude": 51.5560, "longitude": -0.2790},
    {"node_id": "EALING",        "node_name": "Ealing",              "environment": "urban",       "latitude": 51.5130, "longitude": -0.3050},
    {"node_id": "UXBRIDGE",      "node_name": "Uxbridge",            "environment": "urban",       "latitude": 51.5460, "longitude": -0.4790},
    {"node_id": "CANARY-WHARF",  "node_name": "Canary Wharf",        "environment": "urban",       "latitude": 51.5050, "longitude": -0.0230},
    {"node_id": "GREENWICH",     "node_name": "Greenwich",           "environment": "urban",       "latitude": 51.4830, "longitude": -0.0050},
    {"node_id": "STRATFORD",     "node_name": "Stratford",           "environment": "urban",       "latitude": 51.5410, "longitude": -0.0030},
    {"node_id": "CROYDON",       "node_name": "Croydon",             "environment": "urban",       "latitude": 51.3760, "longitude": -0.0990},
    {"node_id": "HEATHROW",      "node_name": "Heathrow",            "environment": "urban",       "latitude": 51.4700, "longitude": -0.4540},
    {"node_id": "CENTRAL-LDN",   "node_name": "Central London",      "environment": "urban",       "latitude": 51.5070, "longitude": -0.1280},
    {"node_id": "HYDE-PARK",     "node_name": "Hyde Park",           "environment": "park",        "latitude": 51.5070, "longitude": -0.1650},
    {"node_id": "RICHMOND-PARK", "node_name": "Richmond Park",       "environment": "park",        "latitude": 51.4420, "longitude": -0.2750},
    {"node_id": "HAMPSTEAD",     "node_name": "Hampstead Heath",     "environment": "park",        "latitude": 51.5600, "longitude": -0.1630},
]

NODES_BY_ID: dict[str, dict] = {n["node_id"]: n for n in NODES}

# Two nodes count as mesh neighbours when within this distance (km).
NEIGHBOUR_RADIUS_KM = 6.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def neighbours_of(node_id: str, radius_km: float = NEIGHBOUR_RADIUS_KM) -> list[str]:
    """Return node_ids within ``radius_km`` of the given node (excluding itself)."""
    base = NODES_BY_ID.get(node_id)
    if not base:
        return []
    out = []
    for other in NODES:
        if other["node_id"] == node_id:
            continue
        d = haversine_km(base["latitude"], base["longitude"],
                         other["latitude"], other["longitude"])
        if d <= radius_km:
            out.append(other["node_id"])
    return out


# Pre-computed adjacency map used by the mesh-correlation logic in the risk engine.
NEIGHBOURS: dict[str, list[str]] = {n["node_id"]: neighbours_of(n["node_id"]) for n in NODES}
