"""
prepare_web_data.py (v2)

Bundles all Pench synthetic data into a single JSON file for the frontend.
Includes: tiger sightings, territories, camera stations, villages,
zone boundary polygons, and alert classifications.
"""

import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(BASE_DIR, "Pench_Synthetic_Metadata")

def main():
    print("Building pench_web_bundle.json (v2)...")

    # 1. Tiger metadata (train only - has tiger IDs)
    df = pd.read_csv(os.path.join(META_DIR, "pench_tiger_metadata_train.csv"))
    df = df.fillna("")  # Replace NaN with empty strings for JSON compatibility
    sightings = df.to_dict(orient="records")
    print(f"  -> {len(sightings)} sightings")

    # 2. Camera stations
    df_st = pd.read_csv(os.path.join(META_DIR, "pench_camera_stations.csv"))
    df_st = df_st.fillna("")  # Replace NaN with empty strings for JSON compatibility
    stations = df_st.to_dict(orient="records")
    print(f"  -> {len(stations)} stations")

    # 3. Tiger territories
    with open(os.path.join(META_DIR, "pench_tiger_territories.json")) as f:
        territories = json.load(f)
    print(f"  -> {len(territories)} territories")

    # 4. Villages
    with open(os.path.join(META_DIR, "pench_villages.json")) as f:
        villages = json.load(f)
    print(f"  -> {len(villages)} villages")

    # 5. Zone boundaries (same as generator definitions)
    core_boundary = [
        [21.735, 79.145], [21.750, 79.210], [21.748, 79.280],
        [21.720, 79.330], [21.700, 79.370], [21.660, 79.375],
        [21.610, 79.365], [21.580, 79.340], [21.555, 79.290],
        [21.545, 79.240], [21.550, 79.195], [21.570, 79.155],
        [21.600, 79.135], [21.650, 79.130], [21.700, 79.135],
    ]
    buffer_boundary = [
        [21.765, 79.120], [21.775, 79.200], [21.770, 79.295],
        [21.750, 79.350], [21.720, 79.395], [21.670, 79.400],
        [21.610, 79.395], [21.560, 79.370], [21.520, 79.310],
        [21.495, 79.250], [21.500, 79.185], [21.520, 79.140],
        [21.555, 79.110], [21.600, 79.100], [21.670, 79.100],
        [21.730, 79.105],
    ]

    # 5b. 11 Verified Forest Sub-Regions (Ranges & Sectors)
    sub_regions = [
        {
            "id": "REG-EP",
            "name": "East Pench Range",
            "type": "Core Forest",
            "center": [21.650, 79.325],
            "polygon": [[21.600, 79.290], [21.700, 79.290], [21.700, 79.360], [21.600, 79.360]],
            "color": "#10b981"
        },
        {
            "id": "REG-DEV",
            "name": "Devalapar Range",
            "type": "Core Forest",
            "center": [21.712, 79.245],
            "polygon": [[21.685, 79.215], [21.740, 79.215], [21.740, 79.275], [21.685, 79.275]],
            "color": "#059669"
        },
        {
            "id": "REG-CHB",
            "name": "Chorbahuli Range",
            "type": "Core Forest",
            "center": [21.645, 79.250],
            "polygon": [[21.610, 79.220], [21.680, 79.220], [21.680, 79.280], [21.610, 79.280]],
            "color": "#14b8a6"
        },
        {
            "id": "REG-WP",
            "name": "West Pench Range",
            "type": "Core Forest",
            "center": [21.695, 79.175],
            "polygon": [[21.660, 79.140], [21.730, 79.140], [21.730, 79.210], [21.660, 79.210]],
            "color": "#34d399"
        },
        {
            "id": "REG-SAL",
            "name": "Saleghat Range",
            "type": "Core Forest",
            "center": [21.595, 79.175],
            "polygon": [[21.560, 79.145], [21.630, 79.145], [21.630, 79.205], [21.560, 79.205]],
            "color": "#047857"
        },
        {
            "id": "REG-PAO",
            "name": "Paoni Buffer Range",
            "type": "Buffer Zone",
            "center": [21.537, 79.215],
            "polygon": [[21.510, 79.175], [21.565, 79.175], [21.565, 79.255], [21.510, 79.255]],
            "color": "#eab308"
        },
        {
            "id": "REG-NAG",
            "name": "Nagalwadi Buffer Range",
            "type": "Buffer Zone",
            "center": [21.532, 79.290],
            "polygon": [[21.505, 79.250], [21.560, 79.250], [21.560, 79.330], [21.505, 79.330]],
            "color": "#ca8a04"
        },
        {
            "id": "REG-SIL",
            "name": "Sillari Buffer Sector",
            "type": "Buffer Zone",
            "center": [21.615, 79.375],
            "polygon": [[21.580, 79.355], [21.650, 79.355], [21.650, 79.395], [21.580, 79.395]],
            "color": "#f59e0b"
        },
        {
            "id": "REG-WBUF",
            "name": "West Buffer Sector",
            "type": "Buffer Zone",
            "center": [21.605, 79.125],
            "polygon": [[21.560, 79.105], [21.650, 79.105], [21.650, 79.145], [21.560, 79.145]],
            "color": "#d97706"
        },
        {
            "id": "REG-NBUF",
            "name": "North Buffer Sector",
            "type": "Buffer Zone",
            "center": [21.750, 79.222],
            "polygon": [[21.735, 79.155], [21.765, 79.155], [21.765, 79.290], [21.735, 79.290]],
            "color": "#b45309"
        },
        {
            "id": "REG-CORR",
            "name": "NH-44 Wildlife Corridor",
            "type": "Corridor",
            "center": [21.630, 79.265],
            "polygon": [[21.540, 79.258], [21.720, 79.258], [21.720, 79.272], [21.540, 79.272]],
            "color": "#a855f7"
        }
    ]

    # 6. Compute last-seen per tiger with alert level
    last_seen = {}
    for row in sightings:
        tid = str(row["tiger_id"])
        if tid not in last_seen or row["timestamp"] > last_seen[tid]["timestamp"]:
            last_seen[tid] = {
                "tiger_id": row["tiger_id"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "timestamp": row["timestamp"],
                "station_id": row["station_id"],
                "zone_type": row["zone_type"],
                "alert_level": row["alert_level"],
                "range": row["range"],
                "nearest_village": row.get("nearest_village", ""),
                "nearest_village_dist_km": row.get("nearest_village_dist_km", 99)
            }

    # 7. Alert summary stats
    alert_summary = {"SAFE": 0, "CAUTION": 0, "CRITICAL": 0}
    for ls in last_seen.values():
        alert_summary[ls["alert_level"]] = alert_summary.get(ls["alert_level"], 0) + 1

    print(f"\n  Alert levels in last-seen:")
    for k, v in alert_summary.items():
        print(f"    {k}: {v} tigers")

    # 8. Bundle everything
    bundle = {
        "metadata": {
            "version": "2.0",
            "reserve": "Pench Tiger Reserve (Maharashtra)",
            "core_area_sqkm": 439,
            "buffer_area_sqkm": 301,
            "total_tigers": len(territories),
            "total_stations": len(stations),
            "total_sightings": len(sightings),
            "total_villages": len(villages)
        },
        "zone_boundaries": {
            "core_forest": core_boundary,
            "buffer_zone": buffer_boundary
        },
        "sub_regions": sub_regions,
        "villages": villages,
        "stations": stations,
        "territories": territories,
        "last_seen": last_seen,
        "alert_summary": alert_summary,
        "sightings": sightings
    }

    out_path = os.path.join(BASE_DIR, "pench_web_bundle.json")
    with open(out_path, "w") as f:
        json.dump(bundle, f)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\n  -> Written: {out_path} ({size_mb:.1f} MB)")
    print("DONE!")


if __name__ == "__main__":
    main()
