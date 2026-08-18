"""
prepare_web_data.py  (v3 — Scientific Bundle Builder)

Bundles all Pench synthetic data into a single JSON file for the frontend.
Reads rich outputs from generate_pench_metadata.py v3 and exposes:
  - Sighting events with 30+ fields per event
  - Camera stations with trap-night effort, failure logs
  - Tiger territories with individualized home-range parameters
  - Water sources layer (for map rendering)
  - Social events summary
  - Territory shift results
  - Zone boundaries (Voronoi-clipped)
  - Sub-region polygons
  - Villages
  - Anomaly type distribution
  - Per-camera effort statistics

All backward-compatible with app.js v2:
  - zone_type, station_id, range, alert_level fields preserved
  - pench_web_bundle.json shape unchanged; new keys are additive
"""

import os
import json
import pandas as pd
import numpy as np
from shapely.geometry import Polygon
from scipy.spatial import Voronoi

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
META_DIR  = os.path.join(BASE_DIR, "Pench_Synthetic_Metadata")


# ─────────────────────────────────────────────────────────────────────────────
# GEOGRAPHY LAYERS (same as simulator — kept in sync)
# ─────────────────────────────────────────────────────────────────────────────

CORE_BOUNDARY = [
    [21.735, 79.145], [21.750, 79.210], [21.748, 79.280],
    [21.720, 79.330], [21.700, 79.370], [21.660, 79.375],
    [21.610, 79.365], [21.580, 79.340], [21.555, 79.290],
    [21.545, 79.240], [21.550, 79.195], [21.570, 79.155],
    [21.600, 79.135], [21.650, 79.130], [21.700, 79.135],
]

BUFFER_BOUNDARY = [
    [21.765, 79.120], [21.775, 79.200], [21.770, 79.295],
    [21.750, 79.350], [21.720, 79.395], [21.670, 79.400],
    [21.610, 79.395], [21.560, 79.370], [21.520, 79.310],
    [21.495, 79.250], [21.500, 79.185], [21.520, 79.140],
    [21.555, 79.110], [21.600, 79.100], [21.670, 79.100],
    [21.730, 79.105],
]

# Sub-regions with Voronoi-generated realistic boundaries
SUB_REGIONS_BASE = [
    {"id": "REG-EP",   "name": "East Pench Range",       "type": "Core Forest", "center": [21.650, 79.325], "color": "#10b981"},
    {"id": "REG-DEV",  "name": "Devalapar Range",         "type": "Core Forest", "center": [21.712, 79.245], "color": "#059669"},
    {"id": "REG-CHB",  "name": "Chorbahuli Range",        "type": "Core Forest", "center": [21.645, 79.250], "color": "#14b8a6"},
    {"id": "REG-WP",   "name": "West Pench Range",        "type": "Core Forest", "center": [21.695, 79.175], "color": "#34d399"},
    {"id": "REG-SAL",  "name": "Saleghat Range",          "type": "Core Forest", "center": [21.595, 79.175], "color": "#047857"},
    {"id": "REG-PAO",  "name": "Paoni Buffer Range",      "type": "Buffer Zone", "center": [21.537, 79.215], "color": "#eab308"},
    {"id": "REG-NAG",  "name": "Nagalwadi Buffer Range",  "type": "Buffer Zone", "center": [21.532, 79.290], "color": "#ca8a04"},
    {"id": "REG-SIL",  "name": "Sillari Buffer Sector",   "type": "Buffer Zone", "center": [21.615, 79.375], "color": "#f59e0b"},
    {"id": "REG-WBUF", "name": "West Buffer Sector",      "type": "Buffer Zone", "center": [21.605, 79.125], "color": "#d97706"},
    {"id": "REG-NBUF", "name": "North Buffer Sector",     "type": "Buffer Zone", "center": [21.750, 79.222], "color": "#b45309"},
    {"id": "REG-CORR", "name": "NH-44 Wildlife Corridor", "type": "Corridor",    "center": [21.630, 79.265], "color": "#a855f7"},
]


def build_voronoi_sub_regions():
    """Build sub-region polygons using Voronoi tessellation clipped to buffer boundary."""
    buffer_poly = Polygon([(p[1], p[0]) for p in BUFFER_BOUNDARY])
    centers = np.array([reg["center"] for reg in SUB_REGIONS_BASE])
    dummy_points = np.array([
        [22.5, 80.5], [20.5, 80.5], [22.5, 78.5], [20.5, 78.5],
        [23.0, 79.2], [20.0, 79.2], [21.6, 81.0], [21.6, 77.0]
    ])
    all_pts = np.vstack([centers, dummy_points])
    vor = Voronoi(all_pts)

    sub_regions = []
    for i, reg in enumerate(SUB_REGIONS_BASE):
        region_idx = vor.point_region[i]
        region_vertices = vor.regions[region_idx]
        if -1 in region_vertices:
            sub_regions.append(dict(reg))
            continue
        vor_poly = Polygon([vor.vertices[v] for v in region_vertices])
        if not vor_poly.is_valid:
            vor_poly = vor_poly.buffer(0)
        clipped = vor_poly.intersection(buffer_poly)
        if not clipped.is_empty:
            if clipped.geom_type == "MultiPolygon":
                clipped = max(clipped.geoms, key=lambda x: x.area)
            coords = list(clipped.exterior.coords)
            # Convert back from (lon, lat) to [lat, lon]
            polygon = [[round(p[1], 5), round(p[0], 5)] for p in coords]
        else:
            polygon = [reg["center"]]
        entry = dict(reg)
        entry["polygon"] = polygon
        sub_regions.append(entry)

    return sub_regions


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUNDLE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Building pench_web_bundle.json (v3 — Scientific)...")

    # ── 1. Tiger sightings ───────────────────────────────────────────────────
    df = pd.read_csv(os.path.join(META_DIR, "pench_tiger_metadata_train.csv"))
    df = df.fillna("")
    # Ensure backward-compat fields exist
    if "zone_type" not in df.columns and "zone" in df.columns:
        df["zone_type"] = df["zone"]
    if "station_id" not in df.columns and "camera_id" in df.columns:
        df["station_id"] = df["camera_id"]
    # Ensure numeric fields are cast correctly
    for col in ["latitude", "longitude", "prey_density", "water_availability",
                "human_disturbance", "camera_detection_probability", "reid_confidence",
                "distance_from_hr_center_km", "distance_to_village_km", "distance_to_water_km"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    sightings = df.to_dict(orient="records")
    print(f"  -> {len(sightings)} sightings")

    # ── 2. Camera stations ───────────────────────────────────────────────────
    df_st = pd.read_csv(os.path.join(META_DIR, "pench_camera_stations.csv"))
    df_st = df_st.fillna("")
    if "station_id" not in df_st.columns and "camera_id" in df_st.columns:
        df_st["station_id"] = df_st["camera_id"]
    stations = df_st.to_dict(orient="records")
    print(f"  -> {len(stations)} camera stations")

    # ── 3. Tiger territories ─────────────────────────────────────────────────
    with open(os.path.join(META_DIR, "pench_tiger_territories.json")) as f:
        territories = json.load(f)
    print(f"  -> {len(territories)} tiger territories")

    # ── 4. Villages ──────────────────────────────────────────────────────────
    with open(os.path.join(META_DIR, "pench_villages.json")) as f:
        villages = json.load(f)
    print(f"  -> {len(villages)} villages")

    # ── 5. Water sources (new §9 layer) ──────────────────────────────────────
    water_sources_path = os.path.join(META_DIR, "pench_water_sources.json")
    if os.path.exists(water_sources_path):
        with open(water_sources_path) as f:
            water_sources = json.load(f)
        print(f"  -> {len(water_sources)} water sources")
    else:
        water_sources = []

    # ── 6. Social events summary ─────────────────────────────────────────────
    social_path = os.path.join(META_DIR, "pench_social_events.json")
    if os.path.exists(social_path):
        with open(social_path) as f:
            social_events = json.load(f)
        social_summary = {}
        for ev in social_events:
            t = ev["type"]
            social_summary[t] = social_summary.get(t, 0) + 1
        print(f"  -> {len(social_events)} social events ({len(social_summary)} types)")
    else:
        social_events  = []
        social_summary = {}

    # ── 7. Territory shifts ───────────────────────────────────────────────────
    shifts_path = os.path.join(META_DIR, "pench_territory_shifts.json")
    if os.path.exists(shifts_path):
        with open(shifts_path) as f:
            territory_shifts = json.load(f)
        n_shifts = sum(1 for v in territory_shifts.values() if v.get("territory_shift_detected"))
        print(f"  -> {n_shifts} tigers with territory shifts detected")
    else:
        territory_shifts = {}

    # ── 8. Zone boundaries ────────────────────────────────────────────────────
    # (already defined at module level)

    # ── 9. Sub-regions (Voronoi-clipped) ─────────────────────────────────────
    sub_regions = build_voronoi_sub_regions()
    print(f"  -> {len(sub_regions)} Voronoi sub-regions built")

    # ── 10. Compute last_seen per tiger with alert level ──────────────────────
    last_seen = {}
    for row in sightings:
        tid = str(row.get("tiger_id", ""))
        if not tid:
            continue
        if tid not in last_seen or row["timestamp"] > last_seen[tid]["timestamp"]:
            last_seen[tid] = {
                "tiger_id":               row.get("tiger_id"),
                "latitude":               row.get("latitude"),
                "longitude":              row.get("longitude"),
                "timestamp":              row.get("timestamp"),
                "station_id":             row.get("station_id") or row.get("camera_id"),
                "camera_id":              row.get("camera_id"),
                "zone_type":              row.get("zone_type") or row.get("zone"),
                "alert_level":            row.get("alert_level", "SAFE"),
                "range":                  row.get("range", "Unknown"),
                "nearest_village":        row.get("nearest_village", ""),
                "nearest_village_dist_km":row.get("nearest_village_dist_km") or row.get("distance_to_village_km", 0),
                "anomaly_type":           row.get("anomaly_type", "normal"),
                "movement_state":         row.get("movement_state", "NORMAL"),
                "behavioral_state":       row.get("behavioral_state", "normal_travel"),
                "image_quality":          row.get("image_quality", "good"),
                "reid_confidence":        row.get("reid_confidence", 0.8),
                "prey_density":           row.get("prey_density", 0.5),
                "water_availability":     row.get("water_availability", 0.5),
                "human_disturbance":      row.get("human_disturbance", 0.1),
            }

    # ── 11. Alert summary ────────────────────────────────────────────────────
    alert_summary = {"SAFE": 0, "CAUTION": 0, "CRITICAL": 0}
    for ls in last_seen.values():
        level = ls.get("alert_level", "SAFE")
        alert_summary[level] = alert_summary.get(level, 0) + 1

    print(f"\n  Alert levels in last-seen:")
    for k, v in alert_summary.items():
        print(f"    {k}: {v} tigers")

    # ── 12. Anomaly distribution ─────────────────────────────────────────────
    anomaly_dist = {}
    for row in sightings:
        at = row.get("anomaly_type", "normal")
        anomaly_dist[at] = anomaly_dist.get(at, 0) + 1

    # ── 13. Camera effort statistics ─────────────────────────────────────────
    camera_effort = {}
    for cam in stations:
        camera_effort[cam.get("camera_id", cam.get("station_id", ""))] = {
            "trap_nights":       cam.get("trap_nights", 0),
            "total_detections":  cam.get("total_detections", 0),
            "n_failures":        cam.get("n_failures", 0),
        }

    # ── 14. Bundle ────────────────────────────────────────────────────────────
    bundle = {
        "metadata": {
            "version":           "3.0",
            "description":       "Scientific ecological simulation — Pench Tiger Reserve (§1-§28)",
            "reserve":           "Pench Tiger Reserve (Maharashtra)",
            "simulation_start":  "2022-06-01",
            "simulation_end":    "2024-05-31",
            "sim_step_hours":    3,
            "n_tigers":          len(territories),
            "n_cameras":         len(stations),
            "total_sightings":   len(sightings),
            "total_villages":    len(villages),
            "total_water_sources": len(water_sources),
            "core_area_sqkm":    439,
            "buffer_area_sqkm":  301,
            "alert_thresholds": {
                "range_shift_km2":         17.5,
                "buffer_penetration_km":   5.0,
                "note": "Alert thresholds — configurable parameters, not biological constants"
            },
        },
        "zone_boundaries": {
            "core_forest":  CORE_BOUNDARY,
            "buffer_zone":  BUFFER_BOUNDARY,
        },
        "sub_regions":       sub_regions,
        "villages":          villages,
        "water_sources":     water_sources,
        "stations":          stations,
        "territories":       territories,
        "last_seen":         last_seen,
        "alert_summary":     alert_summary,
        "anomaly_distribution": anomaly_dist,
        "social_event_summary": social_summary,
        "territory_shifts":  territory_shifts,
        "camera_effort":     camera_effort,
        "sightings":         sightings,
    }

    # ── 15. Write bundle ──────────────────────────────────────────────────────
    out_path = os.path.join(BASE_DIR, "pench_web_bundle.json")
    with open(out_path, "w") as f:
        json.dump(bundle, f, default=str)

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"\n  -> Written: {out_path} ({size_mb:.1f} MB)")

    # Print summary of new layer sizes
    print("\n  Bundle contents:")
    print(f"    sightings:          {len(sightings):>8,}")
    print(f"    cameras:            {len(stations):>8,}")
    print(f"    tigers:             {len(territories):>8,}")
    print(f"    last_seen entries:  {len(last_seen):>8,}")
    print(f"    water_sources:      {len(water_sources):>8,}")
    print(f"    sub_regions:        {len(sub_regions):>8,}")
    print(f"    social_event_types: {len(social_summary):>8,}")
    print(f"    territory_shifts:   {len(territory_shifts):>8,}")
    print(f"    anomaly_types:      {len(anomaly_dist):>8,}")
    print("\nDONE!")


if __name__ == "__main__":
    main()
