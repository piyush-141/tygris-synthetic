"""
generate_pench_metadata.py (v2)

Generates ecologically realistic synthetic metadata for the Amur Tiger dataset,
modeled after Pench Tiger Reserve (Maharashtra). Includes:
- Zone-classified camera stations (core_forest / buffer / village_edge)
- 44 real village locations around the buffer perimeter
- Realistic tiger territory simulation (centroids deep in core, away from villages)
- Alert level classification (SAFE / CAUTION / CRITICAL)
- Natural movement patterns (95% core, 4% buffer, 1% village-edge)
"""

import os
import json
import random
import datetime
import math
import numpy as np
import pandas as pd

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Amur Tigers")
OUTPUT_DIR = os.path.join(BASE_DIR, "Pench_Synthetic_Metadata")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================================
# 1. PENCH GEOGRAPHIC DEFINITIONS
# =========================================================================

# Core forest boundary (irregular polygon matching Pench core ~439 sq km)
CORE_BOUNDARY = [
    [21.735, 79.145], [21.750, 79.210], [21.748, 79.280],
    [21.720, 79.330], [21.700, 79.370], [21.660, 79.375],
    [21.610, 79.365], [21.580, 79.340], [21.555, 79.290],
    [21.545, 79.240], [21.550, 79.195], [21.570, 79.155],
    [21.600, 79.135], [21.650, 79.130], [21.700, 79.135],
]

# Buffer zone boundary (outer ring around core, ~301 sq km additional)
BUFFER_BOUNDARY = [
    [21.765, 79.120], [21.775, 79.200], [21.770, 79.295],
    [21.750, 79.350], [21.720, 79.395], [21.670, 79.400],
    [21.610, 79.395], [21.560, 79.370], [21.520, 79.310],
    [21.495, 79.250], [21.500, 79.185], [21.520, 79.140],
    [21.555, 79.110], [21.600, 79.100], [21.670, 79.100],
    [21.730, 79.105],
]

# 44 villages around the buffer perimeter (Maharashtra side)
VILLAGES = [
    {"name": "Sillari", "lat": 21.612, "lon": 79.385, "population": 1800},
    {"name": "Pipariya", "lat": 21.580, "lon": 79.375, "population": 1200},
    {"name": "Paoni", "lat": 21.510, "lon": 79.220, "population": 2400},
    {"name": "Khursapar", "lat": 21.555, "lon": 79.110, "population": 900},
    {"name": "Bodhali", "lat": 21.620, "lon": 79.098, "population": 1100},
    {"name": "Awarghani", "lat": 21.670, "lon": 79.098, "population": 750},
    {"name": "Ghadazari", "lat": 21.720, "lon": 79.108, "population": 850},
    {"name": "Turia", "lat": 21.755, "lon": 79.140, "population": 1300},
    {"name": "Chikhli", "lat": 21.770, "lon": 79.200, "population": 950},
    {"name": "Karegaon", "lat": 21.765, "lon": 79.280, "population": 700},
    {"name": "Navegaon", "lat": 21.505, "lon": 79.310, "population": 1600},
    {"name": "Chargaon", "lat": 21.498, "lon": 79.260, "population": 1100},
    {"name": "Surera", "lat": 21.510, "lon": 79.175, "population": 800},
    {"name": "Dongartal", "lat": 21.530, "lon": 79.145, "population": 600},
    {"name": "Sawara", "lat": 21.515, "lon": 79.200, "population": 550},
    {"name": "Ghoti", "lat": 21.525, "lon": 79.165, "population": 470},
    {"name": "Kolitmara", "lat": 21.695, "lon": 79.385, "population": 680},
    {"name": "Totladoh", "lat": 21.740, "lon": 79.345, "population": 420},
    {"name": "Bodalkasa", "lat": 21.740, "lon": 79.160, "population": 530},
    {"name": "Mogra", "lat": 21.730, "lon": 79.130, "population": 380},
    {"name": "Ghatpendhari", "lat": 21.760, "lon": 79.235, "population": 610},
    {"name": "Bandara", "lat": 21.752, "lon": 79.260, "population": 440},
    {"name": "Fulzari", "lat": 21.545, "lon": 79.130, "population": 350},
    {"name": "Wadamba", "lat": 21.555, "lon": 79.155, "population": 290},
    {"name": "Hiwra", "lat": 21.758, "lon": 79.215, "population": 510},
    {"name": "Dhamni", "lat": 21.660, "lon": 79.400, "population": 720},
    {"name": "Rawanwadi", "lat": 21.500, "lon": 79.290, "population": 630},
    {"name": "Ambazari", "lat": 21.495, "lon": 79.240, "population": 890},
    {"name": "Karmajhiri", "lat": 21.650, "lon": 79.395, "population": 480},
    {"name": "Teliya", "lat": 21.605, "lon": 79.098, "population": 410},
    {"name": "Jamun", "lat": 21.585, "lon": 79.105, "population": 360},
    {"name": "Pangdi", "lat": 21.640, "lon": 79.395, "population": 520},
    {"name": "Junona", "lat": 21.570, "lon": 79.370, "population": 680},
    {"name": "Palasgaon", "lat": 21.550, "lon": 79.355, "population": 770},
    {"name": "Khapa", "lat": 21.530, "lon": 79.330, "population": 590},
    {"name": "Khandala", "lat": 21.510, "lon": 79.300, "population": 440},
    {"name": "Bhimgarh", "lat": 21.545, "lon": 79.115, "population": 310},
    {"name": "Tekadi", "lat": 21.575, "lon": 79.100, "population": 280},
    {"name": "Gowari", "lat": 21.535, "lon": 79.140, "population": 360},
    {"name": "Salai", "lat": 21.690, "lon": 79.100, "population": 510},
    {"name": "Pitesur", "lat": 21.710, "lon": 79.115, "population": 430},
    {"name": "Ghiregaon", "lat": 21.680, "lon": 79.105, "population": 390},
    {"name": "Manegaon", "lat": 21.745, "lon": 79.310, "population": 570},
    {"name": "Devalapar Village", "lat": 21.760, "lon": 79.250, "population": 650},
]

# Forest range definitions for camera station placement
RANGE_DEFS = {
    "East Pench": {"zone_type": "core_forest", "lat": (21.600, 21.700), "lon": (79.290, 79.360), "n": 28, "prefix": "PTR-CORE-EP"},
    "Devalapar": {"zone_type": "core_forest", "lat": (21.685, 21.740), "lon": (79.215, 79.275), "n": 24, "prefix": "PTR-CORE-DEV"},
    "Chorbahuli": {"zone_type": "core_forest", "lat": (21.610, 21.680), "lon": (79.220, 79.280), "n": 24, "prefix": "PTR-CORE-CHB"},
    "West Pench": {"zone_type": "core_forest", "lat": (21.660, 21.730), "lon": (79.140, 79.210), "n": 20, "prefix": "PTR-CORE-WP"},
    "Saleghat": {"zone_type": "core_forest", "lat": (21.560, 21.630), "lon": (79.145, 79.205), "n": 18, "prefix": "PTR-CORE-SAL"},
    "Paoni Buffer": {"zone_type": "buffer", "lat": (21.510, 21.565), "lon": (79.175, 79.255), "n": 30, "prefix": "PTR-BUF-PAO"},
    "Nagalwadi Buffer": {"zone_type": "buffer", "lat": (21.505, 21.560), "lon": (79.250, 79.330), "n": 25, "prefix": "PTR-BUF-NAG"},
    "NH-44 Corridor": {"zone_type": "buffer", "lat": (21.540, 21.720), "lon": (79.258, 79.272), "n": 14, "prefix": "PTR-COR-NH44"},
    "West Buffer": {"zone_type": "buffer", "lat": (21.560, 21.650), "lon": (79.105, 79.145), "n": 15, "prefix": "PTR-BUF-W"},
    "North Buffer": {"zone_type": "buffer", "lat": (21.735, 21.765), "lon": (79.155, 79.290), "n": 15, "prefix": "PTR-BUF-N"},
    "East Buffer": {"zone_type": "buffer", "lat": (21.580, 21.690), "lon": (79.360, 79.395), "n": 12, "prefix": "PTR-BUF-E"},
}

# Village-edge camera stations (placed at specific boundary villages for HWC monitoring)
VILLAGE_EDGE_STATIONS = [
    {"prefix": "PTR-VIL-SIL", "village": "Sillari", "lat": 21.610, "lon": 79.380, "n": 3},
    {"prefix": "PTR-VIL-PIP", "village": "Pipariya", "lat": 21.578, "lon": 79.370, "n": 2},
    {"prefix": "PTR-VIL-PAO", "village": "Paoni", "lat": 21.515, "lon": 79.225, "n": 3},
    {"prefix": "PTR-VIL-KHU", "village": "Khursapar", "lat": 21.558, "lon": 79.115, "n": 2},
    {"prefix": "PTR-VIL-BOD", "village": "Bodhali", "lat": 21.622, "lon": 79.103, "n": 2},
    {"prefix": "PTR-VIL-AWA", "village": "Awarghani", "lat": 21.668, "lon": 79.103, "n": 2},
    {"prefix": "PTR-VIL-TUR", "village": "Turia", "lat": 21.752, "lon": 79.142, "n": 2},
    {"prefix": "PTR-VIL-NAV", "village": "Navegaon", "lat": 21.510, "lon": 79.305, "n": 2},
    {"prefix": "PTR-VIL-KAR", "village": "Karegaon", "lat": 21.760, "lon": 79.278, "n": 2},
    {"prefix": "PTR-VIL-JUN", "village": "Junona", "lat": 21.572, "lon": 79.365, "n": 2},
]


# =========================================================================
# 2. HELPER: POINT-IN-POLYGON TEST
# =========================================================================

def point_in_polygon(lat, lon, polygon):
    """Ray casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def dist_km(lat1, lon1, lat2, lon2):
    """Approximate distance in km between two lat/lon points."""
    dlat = (lat2 - lat1) * 111.0
    dlon = (lon2 - lon1) * 103.0  # at ~21.6°N
    return math.sqrt(dlat**2 + dlon**2)


def min_village_dist(lat, lon):
    """Returns minimum distance (km) to any village."""
    return min(dist_km(lat, lon, v["lat"], v["lon"]) for v in VILLAGES)


# =========================================================================
# 3. GENERATE CAMERA STATIONS (ZONE-CLASSIFIED)
# =========================================================================

def generate_stations():
    stations = []

    # Core & Buffer range stations
    for rname, rdef in RANGE_DEFS.items():
        zone_type = rdef["zone_type"]
        lat_lo, lat_hi = rdef["lat"]
        lon_lo, lon_hi = rdef["lon"]
        n = rdef["n"]
        prefix = rdef["prefix"]

        for i in range(n):
            lat = round(random.uniform(lat_lo, lat_hi), 6)
            lon = round(random.uniform(lon_lo, lon_hi), 6)

            cam_type = "Camera Trap (Wildlife)" if zone_type == "core_forest" else random.choice(["Camera Trap (Wildlife)", "CCTV / Solar Camera"])

            stations.append({
                "station_id": f"{prefix}-{i+1:02d}",
                "range": rname,
                "zone_type": zone_type,
                "latitude": lat,
                "longitude": lon,
                "camera_type": cam_type,
                "nearest_village": "",
                "nearest_village_dist_km": round(min_village_dist(lat, lon), 2)
            })

    # Village-edge stations
    for vdef in VILLAGE_EDGE_STATIONS:
        for i in range(vdef["n"]):
            lat = round(vdef["lat"] + random.uniform(-0.005, 0.005), 6)
            lon = round(vdef["lon"] + random.uniform(-0.005, 0.005), 6)
            stations.append({
                "station_id": f"{vdef['prefix']}-{i+1:02d}",
                "range": f"{vdef['village']} Edge",
                "zone_type": "village_edge",
                "latitude": lat,
                "longitude": lon,
                "camera_type": "PTZ / AI Camera",
                "nearest_village": vdef["village"],
                "nearest_village_dist_km": round(dist_km(lat, lon, vdef["lat"], vdef["lon"]) + 0.2, 2)
            })

    return pd.DataFrame(stations)


# =========================================================================
# 4. REALISTIC TIGER TERRITORY SIMULATION
# =========================================================================

def simulate_territories(tiger_ids, df_stations):
    """
    Place tiger home territory centroids DEEP inside core forest,
    at least 3 km from any village. Males get larger ranges (8-12 km),
    females smaller (3.5-6 km).
    """
    territories = {}
    core_stations = df_stations[df_stations["zone_type"] == "core_forest"].copy()

    # Pre-filter core stations that are at least 3 km from any village
    safe_stations = core_stations[core_stations["nearest_village_dist_km"] >= 3.0]
    if len(safe_stations) < 20:
        safe_stations = core_stations[core_stations["nearest_village_dist_km"] >= 2.0]

    used_centroids = []

    for tid in tiger_ids:
        is_male = random.random() < 0.42
        territory_radius = round(random.uniform(8.0, 11.5) if is_male else random.uniform(3.5, 6.0), 2)

        # Pick a centroid from safe core stations, ensuring spread (min 1.5 km from other centroids)
        attempts = 0
        while attempts < 100:
            candidate = safe_stations.sample(1).iloc[0]
            c_lat = float(candidate["latitude"] + random.uniform(-0.01, 0.01))
            c_lon = float(candidate["longitude"] + random.uniform(-0.01, 0.01))

            # Check minimum distance from existing centroids
            too_close = any(dist_km(c_lat, c_lon, cl, co) < 1.5 for cl, co in used_centroids)
            # Check minimum distance from villages
            v_dist = min_village_dist(c_lat, c_lon)

            if not too_close and v_dist >= 3.0:
                break
            attempts += 1

        used_centroids.append((c_lat, c_lon))

        territories[str(tid)] = {
            "tiger_id": int(tid),
            "sex": "Male" if is_male else "Female",
            "primary_range": candidate["range"],
            "centroid_lat": round(c_lat, 6),
            "centroid_lon": round(c_lon, 6),
            "territory_radius_km": territory_radius,
            "min_village_dist_km": round(v_dist, 2)
        }

    return territories


# =========================================================================
# 5. SIGHTING ASSIGNMENT WITH NATURAL BEHAVIOR
# =========================================================================

def classify_alert(zone_type):
    if zone_type == "core_forest":
        return "SAFE"
    elif zone_type in ("buffer",):
        return "CAUTION"
    else:
        return "CRITICAL"


def generate_timestamp(start, end):
    """Generate a crepuscular/nocturnal-biased timestamp."""
    delta = (end - start).days
    day = start + datetime.timedelta(days=random.randint(0, delta))

    r = random.random()
    if r < 0.62:
        hour = random.choice([*range(19, 24), *range(0, 6)])
        lighting = "Night (IR Flash)"
    elif r < 0.84:
        hour = random.choice([5, 6, 7, 17, 18, 19])
        lighting = "Dawn / Dusk"
    else:
        hour = random.randint(8, 16)
        lighting = "Daylight"

    dt = day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

    month = dt.month
    base_temp = 16.0 if month in (11, 12, 1, 2) else 32.0
    if 0 <= hour <= 6 or hour >= 20:
        temp = base_temp - random.uniform(4, 9)
    else:
        temp = base_temp + random.uniform(2, 8)

    return dt.strftime("%Y-%m-%d %H:%M:%S"), round(temp, 1), lighting


def assign_sightings(df_pairs, territories, df_stations, is_labeled=True):
    """
    Assign each image to a camera station with natural movement behavior:
    - 95% of sightings at core_forest stations near territory centroid
    - 4% at buffer stations (dispersal/patrol events)
    - ~1% at village_edge stations (rare conflict sighting)
    - Spatial jitter to avoid dense clustering at same point
    """
    records = []
    start = datetime.datetime(2023, 11, 1)
    end = datetime.datetime(2024, 5, 30)

    st_lats = df_stations["latitude"].values
    st_lons = df_stations["longitude"].values
    st_zones = df_stations["zone_type"].values
    st_rows = df_stations.to_dict("records")

    core_mask = st_zones == "core_forest"
    buffer_mask = st_zones == "buffer"
    village_mask = st_zones == "village_edge"

    for _, row in df_pairs.iterrows():
        if is_labeled:
            tid = row[0]
            filename = row[1]
            t = territories[str(tid)]
            c_lat, c_lon = t["centroid_lat"], t["centroid_lon"]
            radius = t["territory_radius_km"]

            # Decide zone for this sighting
            r = random.random()
            if r < 0.95:
                # Core forest - Gaussian around territory center
                mask = core_mask
                sigma = max(radius / 2.0, 1.5)
            elif r < 0.99:
                # Buffer zone dispersal
                mask = buffer_mask
                sigma = radius * 1.5
            else:
                # Village edge - rare conflict
                mask = village_mask
                sigma = radius * 2.5

            d_km = np.sqrt(((st_lats - c_lat) * 111.0)**2 + ((st_lons - c_lon) * 103.0)**2)
            probs = np.where(mask, np.exp(-0.5 * (d_km / sigma)**2), 0.0)

            if probs.sum() == 0:
                # Fallback to core if no valid stations in chosen zone
                probs = np.where(core_mask, np.exp(-0.5 * (d_km / (radius / 2.0))**2), 0.0)

            probs = probs / probs.sum()
            sel_idx = np.random.choice(len(st_rows), p=probs)
            sel = st_rows[sel_idx]
        else:
            filename = row[0]
            tid = None
            sel_idx = random.randint(0, len(st_rows) - 1)
            sel = st_rows[sel_idx]

        ts, temp, lighting = generate_timestamp(start, end)

        # Spatial jitter (+/- 50m) so same-station captures don't pile on one pixel
        jitter_lat = round(sel["latitude"] + random.uniform(-0.0005, 0.0005), 6)
        jitter_lon = round(sel["longitude"] + random.uniform(-0.0005, 0.0005), 6)

        alert = classify_alert(sel["zone_type"])

        rec = {
            "filename": filename,
            "station_id": sel["station_id"],
            "range": sel["range"],
            "zone_type": sel["zone_type"],
            "alert_level": alert,
            "latitude": jitter_lat,
            "longitude": jitter_lon,
            "camera_type": sel["camera_type"],
            "nearest_village": sel.get("nearest_village", ""),
            "nearest_village_dist_km": sel.get("nearest_village_dist_km", 99),
            "timestamp": ts,
            "ambient_temp_c": temp,
            "lighting_condition": lighting
        }

        if is_labeled:
            rec["tiger_id"] = int(tid)
            ordered = {k: rec[k] for k in ["tiger_id", "filename"] + [k for k in rec if k not in ["tiger_id", "filename"]]}
            records.append(ordered)
        else:
            records.append(rec)

    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# =========================================================================
# 6. MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("PENCH v2: REALISTIC ZONE-AWARE TIGER BEHAVIOR SIMULATION")
    print("=" * 70)

    print("\n[1/5] Generating zone-classified camera stations...")
    df_stations = generate_stations()
    df_stations.to_csv(os.path.join(OUTPUT_DIR, "pench_camera_stations.csv"), index=False)
    print(f"  -> {len(df_stations)} stations")
    print(df_stations["zone_type"].value_counts().to_string())

    print("\n[2/5] Loading dataset...")
    df_train = pd.read_csv(os.path.join(DATASET_DIR, "reid_list_train.csv"), header=None)
    df_test = pd.read_csv(os.path.join(DATASET_DIR, "reid_list_test.csv"), header=None)
    tigers = df_train[0].unique()
    print(f"  -> {len(df_train)} train, {len(df_test)} test, {len(tigers)} tigers")

    print("\n[3/5] Simulating ecologically realistic territories (centroids >=3km from villages)...")
    territories = simulate_territories(tigers, df_stations)
    with open(os.path.join(OUTPUT_DIR, "pench_tiger_territories.json"), "w") as f:
        json.dump(territories, f, indent=2)

    # Verify territory placement
    min_vd = min(t["min_village_dist_km"] for t in territories.values())
    avg_vd = np.mean([t["min_village_dist_km"] for t in territories.values()])
    print(f"  -> Min village distance: {min_vd:.1f} km, Avg: {avg_vd:.1f} km")

    print("\n[4/5] Assigning sightings with natural movement behavior...")
    df_meta_train = assign_sightings(df_train, territories, df_stations, is_labeled=True)
    df_meta_train.to_csv(os.path.join(OUTPUT_DIR, "pench_tiger_metadata_train.csv"), index=False)

    df_meta_test = assign_sightings(df_test, territories, df_stations, is_labeled=False)
    df_meta_test.to_csv(os.path.join(OUTPUT_DIR, "pench_tiger_metadata_test.csv"), index=False)

    # Zone distribution stats
    zone_counts = df_meta_train["zone_type"].value_counts()
    alert_counts = df_meta_train["alert_level"].value_counts()
    print(f"\n  Zone distribution (train):")
    print(f"  {zone_counts.to_string()}")
    print(f"\n  Alert distribution (train):")
    print(f"  {alert_counts.to_string()}")

    print("\n[5/5] Saving village data...")
    with open(os.path.join(OUTPUT_DIR, "pench_villages.json"), "w") as f:
        json.dump(VILLAGES, f, indent=2)

    print("\n" + "=" * 70)
    print("DONE! All files in:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
