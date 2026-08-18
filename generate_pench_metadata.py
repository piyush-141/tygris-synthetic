"""
generate_pench_metadata.py  (v3 — Scientific Ecological Simulator)

Generates a large-scale, scientifically constrained synthetic tiger-movement
and camera-trap simulation for Pench Tiger Reserve (Maharashtra/MP).

Pipeline:
  PENCH GIS ENVIRONMENT
  → ECOLOGICAL HABITAT GRID (2 km²)
  → CAMERA NETWORK (non-uniform, with failure simulation)
  → TIGER AGENTS (individual persistent identity + behaviour)
  → BIOLOGICAL / SOCIAL EVENTS (mating, conflict, dispersal, cubs)
  → CONTINUOUS MOVEMENT TRAJECTORIES (Correlated Random Walk)
  → CAMERA OBSERVATION MODEL (detection probability, missed detections)
  → SYNTHETIC SIGHTING DATABASE (30+ fields per event)
  → GROUND TRUTH LAYER (separate, for ML labels only)
  → ANOMALY LABELER (20+ typed anomaly categories)
  → TRAIN / VAL / TEST split by simulation seed

Master Prompt Reference:
  §1  Real Pench Environment       §15 Camera Observation Model
  §2  Camera Network               §16 Survey Artefacts
  §3  Tiger Population             §17 Sighting Events
  §4  Home Range & Territory       §18 Hidden Ground Truth
  §5  Hidden Tiger Movement        §19 Anomaly Scenarios
  §6  Trails & Movement Routes     §20 Prolonged Absence
  §7  Ecological Drivers           §21 Range-Shift Detection
  §8  Time & Activity              §22 First-Time Station Detection
  §9  Water Behaviour              §23 Movement Prediction Dataset
  §10 Prey Layer                   §24 Behavioural Anomaly Dataset
  §11 Natural Social/Bio Events    §25 Territory-Change Dataset
  §12 Territorial Overlap          §26 Data Distribution
  §13 Buffer & Village Behaviour   §27 Simulation Scale
  §14 Forest Exit                  §28 Train/Test Separation
"""

import os
import json
import math
import random
import datetime
import itertools
import uuid
from collections import defaultdict

import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from scipy.spatial import cKDTree

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Amur Tigers")
OUTPUT_DIR  = os.path.join(BASE_DIR, "Pench_Synthetic_Metadata")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Simulation parameters (§27)
N_TIGERS_DEFAULT  = 107
N_CAMERAS_DEFAULT = 145
SIM_START = datetime.datetime(2022, 6, 1)
SIM_END   = datetime.datetime(2024, 5, 31)
SIM_STEP_HOURS = 3          # hidden trajectory step size
N_SEEDS   = 5               # number of parallel simulation worlds

# Alert thresholds (§21) — configurable, not hard biological constants
RANGE_SHIFT_ALERT_KM2     = 17.5   # 15–20 km² midpoint
BUFFER_PENETRATION_ALERT_KM = 5.0

# ─────────────────────────────────────────────────────────────────────────────
# 1.  PENCH GEOGRAPHIC DEFINITIONS  (§1)
# ─────────────────────────────────────────────────────────────────────────────

# Real Pench bounding box (Maharashtra + MP combined reserve)
PENCH_BBOX = {
    "lat_min": 21.490, "lat_max": 21.785,
    "lon_min": 79.095, "lon_max": 79.410
}

# Actual core forest boundary polygon  [lat, lon]
CORE_BOUNDARY = [
    [21.735, 79.145], [21.750, 79.210], [21.748, 79.280],
    [21.720, 79.330], [21.700, 79.370], [21.660, 79.375],
    [21.610, 79.365], [21.580, 79.340], [21.555, 79.290],
    [21.545, 79.240], [21.550, 79.195], [21.570, 79.155],
    [21.600, 79.135], [21.650, 79.130], [21.700, 79.135],
]

# Outer buffer zone boundary
BUFFER_BOUNDARY = [
    [21.765, 79.120], [21.775, 79.200], [21.770, 79.295],
    [21.750, 79.350], [21.720, 79.395], [21.670, 79.400],
    [21.610, 79.395], [21.560, 79.370], [21.520, 79.310],
    [21.495, 79.250], [21.500, 79.185], [21.520, 79.140],
    [21.555, 79.110], [21.600, 79.100], [21.670, 79.100],
    [21.730, 79.105],
]

# Shapely polygons
CORE_POLY   = Polygon([(p[1], p[0]) for p in CORE_BOUNDARY])    # (lon,lat)
BUFFER_POLY = Polygon([(p[1], p[0]) for p in BUFFER_BOUNDARY])

# Real water sources: rivers, streams, permanent waterholes  [lat, lon, type, seasonal]
WATER_SOURCES = [
    {"name": "Pench River Main",     "lat": 21.640, "lon": 79.270, "type": "river",    "seasonal": False},
    {"name": "Pench River North",    "lat": 21.710, "lon": 79.235, "type": "river",    "seasonal": False},
    {"name": "Jamni River",          "lat": 21.590, "lon": 79.205, "type": "river",    "seasonal": False},
    {"name": "Kulbehra Stream",      "lat": 21.660, "lon": 79.310, "type": "stream",   "seasonal": True},
    {"name": "Totladoh Reservoir",   "lat": 21.742, "lon": 79.347, "type": "reservoir","seasonal": False},
    {"name": "Bodalkasa Waterhole",  "lat": 21.738, "lon": 79.158, "type": "waterhole","seasonal": True},
    {"name": "Saleghat Nala",        "lat": 21.595, "lon": 79.165, "type": "stream",   "seasonal": True},
    {"name": "Chorbahuli Nala",      "lat": 21.645, "lon": 79.250, "type": "stream",   "seasonal": True},
    {"name": "East Pench Nala",      "lat": 21.650, "lon": 79.330, "type": "stream",         "seasonal": True},
    {"name": "Devalapar Waterhole",  "lat": 21.715, "lon": 79.248, "type": "waterhole","seasonal": True},
    {"name": "NH-44 Culvert Pool",   "lat": 21.630, "lon": 79.265, "type": "pool",     "seasonal": True},
    {"name": "Paoni Nala",           "lat": 21.530, "lon": 79.220, "type": "stream",   "seasonal": True},
    {"name": "West Buffer Stream",   "lat": 21.615, "lon": 79.115, "type": "stream",   "seasonal": True},
    {"name": "North Buffer Pond",    "lat": 21.758, "lon": 79.185, "type": "waterhole","seasonal": True},
]
# Fix one broken entry
WATER_SOURCES[8]["lon"] = 79.330

# Seasons and their approximate date ranges (§8)
SEASONS = {
    "summer":      (datetime.date(2022, 3,  1), datetime.date(2022, 6, 14)),
    "monsoon":     (datetime.date(2022, 6, 15), datetime.date(2022, 10, 14)),
    "post_monsoon":(datetime.date(2022, 10,15), datetime.date(2022, 11, 30)),
    "winter":      (datetime.date(2022, 12, 1), datetime.date(2023, 2, 28)),
}

# 44 villages around the buffer perimeter
VILLAGES = [
    {"name": "Sillari",           "lat": 21.612, "lon": 79.385, "population": 1800},
    {"name": "Pipariya",          "lat": 21.580, "lon": 79.375, "population": 1200},
    {"name": "Paoni",             "lat": 21.510, "lon": 79.220, "population": 2400},
    {"name": "Khursapar",         "lat": 21.555, "lon": 79.110, "population":  900},
    {"name": "Bodhali",           "lat": 21.620, "lon": 79.098, "population": 1100},
    {"name": "Awarghani",         "lat": 21.670, "lon": 79.098, "population":  750},
    {"name": "Ghadazari",         "lat": 21.720, "lon": 79.108, "population":  850},
    {"name": "Turia",             "lat": 21.755, "lon": 79.140, "population": 1300},
    {"name": "Chikhli",           "lat": 21.770, "lon": 79.200, "population":  950},
    {"name": "Karegaon",          "lat": 21.765, "lon": 79.280, "population":  700},
    {"name": "Navegaon",          "lat": 21.505, "lon": 79.310, "population": 1600},
    {"name": "Chargaon",          "lat": 21.498, "lon": 79.260, "population": 1100},
    {"name": "Surera",            "lat": 21.510, "lon": 79.175, "population":  800},
    {"name": "Dongartal",         "lat": 21.530, "lon": 79.145, "population":  600},
    {"name": "Sawara",            "lat": 21.515, "lon": 79.200, "population":  550},
    {"name": "Ghoti",             "lat": 21.525, "lon": 79.165, "population":  470},
    {"name": "Kolitmara",         "lat": 21.695, "lon": 79.385, "population":  680},
    {"name": "Totladoh",          "lat": 21.740, "lon": 79.345, "population":  420},
    {"name": "Bodalkasa",         "lat": 21.740, "lon": 79.160, "population":  530},
    {"name": "Mogra",             "lat": 21.730, "lon": 79.130, "population":  380},
    {"name": "Ghatpendhari",      "lat": 21.760, "lon": 79.235, "population":  610},
    {"name": "Bandara",           "lat": 21.752, "lon": 79.260, "population":  440},
    {"name": "Fulzari",           "lat": 21.545, "lon": 79.130, "population":  350},
    {"name": "Wadamba",           "lat": 21.555, "lon": 79.155, "population":  290},
    {"name": "Hiwra",             "lat": 21.758, "lon": 79.215, "population":  510},
    {"name": "Dhamni",            "lat": 21.660, "lon": 79.400, "population":  720},
    {"name": "Rawanwadi",         "lat": 21.500, "lon": 79.290, "population":  630},
    {"name": "Ambazari",          "lat": 21.495, "lon": 79.240, "population":  890},
    {"name": "Karmajhiri",        "lat": 21.650, "lon": 79.395, "population":  480},
    {"name": "Teliya",            "lat": 21.605, "lon": 79.098, "population":  410},
    {"name": "Jamun",             "lat": 21.585, "lon": 79.105, "population":  360},
    {"name": "Pangdi",            "lat": 21.640, "lon": 79.395, "population":  520},
    {"name": "Junona",            "lat": 21.570, "lon": 79.370, "population":  680},
    {"name": "Palasgaon",         "lat": 21.550, "lon": 79.355, "population":  770},
    {"name": "Khapa",             "lat": 21.530, "lon": 79.330, "population":  590},
    {"name": "Khandala",          "lat": 21.510, "lon": 79.300, "population":  440},
    {"name": "Bhimgarh",          "lat": 21.545, "lon": 79.115, "population":  310},
    {"name": "Tekadi",            "lat": 21.575, "lon": 79.100, "population":  280},
    {"name": "Gowari",            "lat": 21.535, "lon": 79.140, "population":  360},
    {"name": "Salai",             "lat": 21.690, "lon": 79.100, "population":  510},
    {"name": "Pitesur",           "lat": 21.710, "lon": 79.115, "population":  430},
    {"name": "Ghiregaon",         "lat": 21.680, "lon": 79.105, "population":  390},
    {"name": "Manegaon",          "lat": 21.745, "lon": 79.310, "population":  570},
    {"name": "Devalapar Village", "lat": 21.760, "lon": 79.250, "population":  650},
]

# Forest range definitions (used for naming cameras and sub-regions)
RANGE_DEFS = {
    "East Pench":       {"zone": "core_forest",  "lat": (21.600,21.700), "lon": (79.290,79.360), "prefix": "PTR-CORE-EP"},
    "Devalapar":        {"zone": "core_forest",  "lat": (21.685,21.740), "lon": (79.215,79.275), "prefix": "PTR-CORE-DEV"},
    "Chorbahuli":       {"zone": "core_forest",  "lat": (21.610,21.680), "lon": (79.220,79.280), "prefix": "PTR-CORE-CHB"},
    "West Pench":       {"zone": "core_forest",  "lat": (21.660,21.730), "lon": (79.140,79.210), "prefix": "PTR-CORE-WP"},
    "Saleghat":         {"zone": "core_forest",  "lat": (21.560,21.630), "lon": (79.145,79.205), "prefix": "PTR-CORE-SAL"},
    "Paoni Buffer":     {"zone": "buffer",        "lat": (21.510,21.565), "lon": (79.175,79.255), "prefix": "PTR-BUF-PAO"},
    "Nagalwadi Buffer": {"zone": "buffer",        "lat": (21.505,21.560), "lon": (79.250,79.330), "prefix": "PTR-BUF-NAG"},
    "NH-44 Corridor":   {"zone": "buffer",        "lat": (21.540,21.720), "lon": (79.258,79.272), "prefix": "PTR-COR-NH44"},
    "West Buffer":      {"zone": "buffer",        "lat": (21.560,21.650), "lon": (79.105,79.145), "prefix": "PTR-BUF-W"},
    "North Buffer":     {"zone": "buffer",        "lat": (21.735,21.765), "lon": (79.155,79.290), "prefix": "PTR-BUF-N"},
    "East Buffer":      {"zone": "buffer",        "lat": (21.580,21.690), "lon": (79.360,79.395), "prefix": "PTR-BUF-E"},
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def dist_km(lat1, lon1, lat2, lon2):
    """Fast flat-earth distance in km (valid at ~21.6°N)."""
    dlat = (lat2 - lat1) * 111.0
    dlon = (lon2 - lon1) * 103.0
    return math.sqrt(dlat * dlat + dlon * dlon)


def bearing_deg(lat1, lon1, lat2, lon2):
    """Approximate bearing in degrees from point 1 to point 2."""
    dlat = (lat2 - lat1) * 111.0
    dlon = (lon2 - lon1) * 103.0
    return math.degrees(math.atan2(dlon, dlat)) % 360


def get_season(dt):
    """Return season name for a given datetime."""
    m, d = dt.month, dt.day
    if (m == 6 and d >= 15) or m in (7, 8, 9) or (m == 10 and d <= 14):
        return "monsoon"
    elif (m == 10 and d >= 15) or m == 11:
        return "post_monsoon"
    elif m in (12, 1, 2):
        return "winter"
    else:  # 3,4,5, early June
        return "summer"


def nearest_village(lat, lon):
    """Return nearest village name and distance in km."""
    best, best_d = None, 9999.0
    for v in VILLAGES:
        d = dist_km(lat, lon, v["lat"], v["lon"])
        if d < best_d:
            best_d = d
            best = v
    return best["name"], round(best_d, 3)


def nearest_water(lat, lon, season):
    """Return nearest available water source name and distance in km."""
    best, best_d = None, 9999.0
    for w in WATER_SOURCES:
        if w["seasonal"] and season == "summer":
            # ~50% of seasonal sources dry up in summer
            if hash(w["name"]) % 2 == 0:
                continue
        d = dist_km(lat, lon, w["lat"], w["lon"])
        if d < best_d:
            best_d = d
            best = w
    return (best["name"] if best else "None"), round(best_d, 3)


def point_in_polygon(lat, lon, polygon):
    """Ray-casting point-in-polygon test."""
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


def zone_for_point(lat, lon):
    """Classify a point as core_forest / buffer / village_edge / outside."""
    # Shapely uses (lon, lat); CORE/BUFFER_POLY are built with (lon,lat) ordering
    pt = Point(lon, lat)
    if CORE_POLY.contains(pt):
        return "core_forest"
    if BUFFER_POLY.contains(pt):
        return "buffer"
    # Check if near a village
    _, vd = nearest_village(lat, lon)
    if vd < 2.0:
        return "village_edge"
    return "outside"


def range_for_point(lat, lon):
    """Return the forest range name for a given coordinate."""
    for rname, rd in RANGE_DEFS.items():
        if rd["lat"][0] <= lat <= rd["lat"][1] and rd["lon"][0] <= lon <= rd["lon"][1]:
            return rname
    return "Unknown Range"


def alert_for_zone(zone):
    if zone == "core_forest":
        return "SAFE"
    elif zone == "buffer":
        return "CAUTION"
    else:
        return "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# 2. HABITAT GRID  (§1, §7)
# ─────────────────────────────────────────────────────────────────────────────

class HabitatGrid:
    """
    2 km² ecological sampling grid over Pench.
    Each cell stores habitat suitability, prey density, disturbance, water.
    """
    CELL_KM = 2.0
    LAT_STEP = CELL_KM / 111.0
    LON_STEP = CELL_KM / 103.0

    def __init__(self, rng):
        self.rng = rng
        self.cells = {}          # (grid_row, grid_col) → dict
        self.cell_centers = []   # list of (lat, lon)
        self.cell_keys = []
        self._build()

    def _build(self):
        lat = PENCH_BBOX["lat_min"]
        row = 0
        while lat <= PENCH_BBOX["lat_max"]:
            col = 0
            lon = PENCH_BBOX["lon_min"]
            while lon <= PENCH_BBOX["lon_max"]:
                key = (row, col)
                clat = lat + self.LAT_STEP / 2
                clon = lon + self.LON_STEP / 2
                zone = zone_for_point(clat, clon)
                hab = self._habitat_type(clat, clon, zone)
                suit = self._suitability(clat, clon, zone, hab)
                prey = self._prey_density(clat, clon, zone, suit, hab)
                dist = self._human_disturbance(clat, clon, zone)
                _, wd = nearest_water(clat, clon, "winter")  # baseline

                mods_prey = {"summer": 0.85, "monsoon": 1.15, "post_monsoon": 1.10, "winter": 0.95}
                mods_water = {"summer": 0.55, "monsoon": 1.0, "post_monsoon": 0.90, "winter": 0.80}
                _, vd_c = nearest_village(clat, clon)

                cell_dict = {
                    "grid_id": f"G{row:03d}{col:03d}",
                    "lat": round(clat, 5),
                    "lon": round(clon, 5),
                    "zone": zone,
                    "habitat_type": hab,
                    "suitability": round(suit, 3),
                    "prey_density": round(prey, 3),
                    "human_disturbance": round(dist, 3),
                    "nearest_water_km": round(wd, 2),
                    "nearest_village_km": round(vd_c, 2),
                    "elevation_m": int(400 + 150 * math.sin((clat - 21.5) * 10)
                                       + 80 * math.cos((clon - 79.2) * 12)),
                }
                for s in ("summer", "monsoon", "post_monsoon", "winter"):
                    cell_dict["seasonal_prey_" + s] = round(min(1.0, prey * mods_prey[s]), 3)
                    _, wd_s = nearest_water(clat, clon, s)
                    cell_dict["seasonal_water_" + s] = round(min(1.0, max(0, 1 - wd_s / 6.0) * mods_water[s]), 3)

                self.cells[key] = cell_dict
                self.cell_centers.append((clat, clon))
                self.cell_keys.append(key)
                lon += self.LON_STEP
                col += 1
            lat += self.LAT_STEP
            row += 1

        self._kd = cKDTree([(c[0] * 111.0, c[1] * 103.0)
                            for c in self.cell_centers])

    def _habitat_type(self, lat, lon, zone):
        """Assign a biologically plausible habitat type."""
        _, wd = nearest_water(lat, lon, "winter")
        if zone == "outside":
            return "agricultural"
        if zone == "village_edge":
            return self.rng.choice(["scrub", "agricultural", "degraded_forest"])
        if wd < 0.5:
            return "riparian_forest"
        if zone == "buffer":
            return self.rng.choice(["teak_forest", "mixed_forest", "scrub", "grassland"],
                                   p=[0.35, 0.30, 0.20, 0.15])
        if wd < 1.5:
            return self.rng.choice(["teak_forest", "riparian_forest"], p=[0.55, 0.45])
        return self.rng.choice(["teak_forest", "mixed_forest", "bamboo", "grassland"],
                               p=[0.45, 0.30, 0.15, 0.10])

    def _suitability(self, lat, lon, zone, hab):
        """Habitat suitability score 0–1 for tiger."""
        base = {"core_forest": 0.85, "buffer": 0.45, "village_edge": 0.15, "outside": 0.05}[zone]
        hab_mod = {
            "teak_forest": 0.10, "mixed_forest": 0.08, "riparian_forest": 0.12,
            "bamboo": 0.05, "grassland": 0.03, "scrub": -0.05,
            "agricultural": -0.20, "degraded_forest": -0.10
        }.get(hab, 0)
        noise = self.rng.uniform(-0.05, 0.05)
        return max(0.0, min(1.0, base + hab_mod + noise))

    def _prey_density(self, lat, lon, zone, suit, hab):
        """Prey density index 0–1. Highest in core forest near water."""
        _, wd = nearest_water(lat, lon, "winter")
        water_factor = max(0, 1 - wd / 5.0)
        base = suit * 0.7 + water_factor * 0.2
        if hab in ("grassland", "riparian_forest"):
            base += 0.10
        noise = self.rng.uniform(-0.08, 0.08)
        return max(0.0, min(1.0, base + noise))

    def _human_disturbance(self, lat, lon, zone):
        """Human disturbance index 0–1. High near villages and roads."""
        _, vd = nearest_village(lat, lon)
        vd_factor = max(0, 1 - vd / 8.0)
        zone_base = {"outside": 0.75, "village_edge": 0.65, "buffer": 0.25, "core_forest": 0.05}[zone]
        road_dist = abs(lon - 79.265) * 103.0
        road_factor = max(0, 0.25 - road_dist / 10.0)
        return min(1.0, zone_base + vd_factor * 0.3 + road_factor)

    def nearest_cell(self, lat, lon):
        """Return the cell key nearest to (lat, lon). Fast O(1) arithmetic lookup."""
        row = int(round((lat - PENCH_BBOX["lat_min"] - self.LAT_STEP / 2) / self.LAT_STEP))
        col = int(round((lon - PENCH_BBOX["lon_min"] - self.LON_STEP / 2) / self.LON_STEP))
        key = (row, col)
        if key in self.cells:
            return key, self.cells[key]
        _, idx = self._kd.query([lat * 111.0, lon * 103.0])
        return self.cell_keys[idx], self.cells[self.cell_keys[idx]]

    def get_seasonal_prey(self, lat, lon, season):
        key, cell = self.nearest_cell(lat, lon)
        return cell.get("seasonal_prey_" + season, cell["prey_density"])

    def get_seasonal_water(self, lat, lon, season):
        key, cell = self.nearest_cell(lat, lon)
        return cell.get("seasonal_water_" + season, 0.5)

    def movement_weight(self, lat, lon, season, tiger_centroid, tiger_radius,
                        familiarity, cur_lat=None, cur_lon=None, tiger_movement_state="NORMAL",
                        prev_bear_deg=None, cur_bear_deg=None):
        key, cell = self.nearest_cell(lat, lon)
        suit    = cell["suitability"]
        prey    = cell.get("seasonal_prey_" + season, cell["prey_density"])
        water   = cell.get("seasonal_water_" + season, 0.5)
        disturb = cell["human_disturbance"]

        # Base ecological resource score
        w_eco = suit * 0.35 + prey * 0.35 + water * 0.20 - disturb * 0.30
        w_eco = max(0.05, w_eco)

        # Distances to home range centroid
        d_cand = dist_km(lat, lon, tiger_centroid[0], tiger_centroid[1])
        d_cur  = dist_km(cur_lat, cur_lon, tiger_centroid[0], tiger_centroid[1]) if (cur_lat and cur_lon) else d_cand
        step_len = max(0.1, dist_km(lat, lon, cur_lat, cur_lon)) if (cur_lat and cur_lon) else 1.0

        if tiger_movement_state == "DISPERSAL":
            eff_radius = tiger_radius * 2.5
            tether_strength = 0.6
        elif tiger_movement_state in ("EXPLORATORY", "LONG_DISTANCE"):
            eff_radius = tiger_radius * 1.35
            tether_strength = 2.0
        else:
            eff_radius = tiger_radius
            tether_strength = 4.5

        # Boundary penalty: steep decay when stepping beyond territory radius
        boundary_excess = max(0.0, d_cand - 0.70 * eff_radius)
        f_boundary = math.exp(-tether_strength * (boundary_excess / max(0.4, 0.35 * eff_radius)) ** 2)

        # Directional pull: steps moving towards center are boosted; outward steps are penalized
        if d_cand > d_cur:
            f_dir = math.exp(-3.5 * ((d_cand - d_cur) / step_len) * max(0.2, d_cand / eff_radius))
        else:
            f_dir = 1.0 + 2.5 * ((d_cur - d_cand) / step_len) * max(0.2, d_cur / eff_radius)

        fam = min(1.0, familiarity.get(key, 0) / 6.0) * 0.15

        dir_factor = 1.0
        if prev_bear_deg is not None and cur_bear_deg is not None:
            turn = abs(cur_bear_deg - prev_bear_deg) % 360
            if turn > 180:
                turn = 360 - turn
            dir_factor = 0.75 + 0.25 * math.cos(math.radians(turn))

        w = w_eco * f_boundary * f_dir * (1.0 + fam) * dir_factor
        return max(0.0001, w), cell["nearest_village_km"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. CAMERA NETWORK  (§2)
# ─────────────────────────────────────────────────────────────────────────────

class CameraNetwork:
    """
    Non-uniform camera placement biased toward trails, crossings,
    streambeds, ridges and wildlife corridors (§2).
    """

    FAILURE_TYPES = ["battery_failure", "memory_full", "maintenance",
                     "false_trigger", "poor_image", "vandalism"]

    def __init__(self, grid: HabitatGrid, n_cameras=N_CAMERAS_DEFAULT,
                 rng=None, seed_id=0):
        self.rng = rng or np.random.default_rng(seed_id)
        self.n = n_cameras
        self.grid = grid
        self.cameras = []
        self._build(seed_id)
        self._schedule_failures()
        self._kd = cKDTree([(c["latitude"] * 111.0, c["longitude"] * 103.0)
                            for c in self.cameras])

    def _build(self, seed_id):
        """Place cameras evenly across ranges with strict spatial separation (min 1.25 km)."""
        CAM_RANGE_ALLOC = [
            ("East Pench", 20),
            ("West Pench", 16),
            ("Chorbahuli", 16),
            ("Devalapar", 15),
            ("Saleghat", 15),
            ("Paoni Buffer", 12),
            ("Nagalwadi Buffer", 11),
            ("Sillari Buffer Sector", 11),
            ("West Buffer", 8),
            ("North Buffer", 8),
            ("NH-44 Corridor", 6),
        ]

        placed_positions = []
        cam_id = 1

        for rname, target_count in CAM_RANGE_ALLOC:
            rdef = RANGE_DEFS.get(rname)
            if not rdef:
                rdef = RANGE_DEFS.get(rname.replace(" Sector", ""))

            # Find candidate cells in this range
            range_cells = []
            for key, cell in self.grid.cells.items():
                if cell["zone"] in ("outside",):
                    continue
                if rdef:
                    if (rdef["lat"][0] <= cell["lat"] <= rdef["lat"][1] and
                        rdef["lon"][0] <= cell["lon"] <= rdef["lon"][1]):
                        range_cells.append(cell)
                elif range_for_point(cell["lat"], cell["lon"]) == rname:
                    range_cells.append(cell)

            if not range_cells:
                range_cells = [c for c in self.grid.cells.values() if c["zone"] in ("core_forest", "buffer")]

            weights = np.array([c["suitability"] * 0.6 + (1 - min(1, c["nearest_water_km"] / 4)) * 0.4 for c in range_cells], dtype=float)
            if weights.sum() > 0:
                weights /= weights.sum()
            else:
                weights = np.ones(len(range_cells)) / len(range_cells)

            placed_for_range = 0
            attempts = 0
            while placed_for_range < target_count and attempts < 400:
                attempts += 1
                idx = np.random.choice(len(range_cells), p=weights)
                cell = range_cells[idx]
                lat = cell["lat"] + np.random.uniform(-0.003, 0.003)
                lon = cell["lon"] + np.random.uniform(-0.003, 0.003)

                # Check strict minimum distance spacing (min 1.2 km from any other camera)
                too_close = any(dist_km(lat, lon, plat, plon) < 1.15 for plat, plon in placed_positions)
                if too_close:
                    continue

                zone = zone_for_point(lat, lon)
                if zone == "outside":
                    continue

                placed_positions.append((lat, lon))
                placed_for_range += 1

                _, vd = nearest_village(lat, lon)
                _, wd = nearest_water(lat, lon, "winter")

                trail_type = np.random.choice(
                    ["animal_trail", "forest_road", "streambed", "ridge", "crossing", "waterhole_approach"],
                    p=[0.30, 0.22, 0.18, 0.12, 0.10, 0.08]
                )
                cam_type = ("Camera Trap (Wildlife)" if zone == "core_forest"
                            else np.random.choice(["Camera Trap (Wildlife)", "CCTV / Solar Camera"],
                                                  p=[0.70, 0.30]))

                deploy_start = SIM_START - datetime.timedelta(days=int(np.random.randint(0, 60)))
                deploy_end   = SIM_END   + datetime.timedelta(days=int(np.random.randint(0, 30)))

                self.cameras.append({
                    "camera_id":       f"CAM-{cam_id:04d}",
                    "latitude":        round(lat, 6),
                    "longitude":       round(lon, 6),
                    "grid_id":         cell["grid_id"],
                    "zone":            zone,
                    "habitat":         cell["habitat_type"],
                    "trail_type":      trail_type,
                    "nearest_water_km":round(wd, 2),
                    "nearest_village": nearest_village(lat, lon)[0],
                    "nearest_village_km": round(vd, 2),
                    "nearest_road_km": round(abs(lon - 79.265) * 103, 2),
                    "range":           rname,
                    "camera_type":     cam_type,
                    "deployment_start":deploy_start.strftime("%Y-%m-%d"),
                    "deployment_end":  deploy_end.strftime("%Y-%m-%d"),
                    "operational":     True,
                    "failure_log":     [],    # populated by _schedule_failures
                    "trap_nights":     0,     # updated during simulation
                    "total_detections": 0,
                })
                cam_id += 1

    def _schedule_failures(self):
        """Pre-schedule realistic camera failure windows (§16)."""
        sim_days = (SIM_END - SIM_START).days
        for cam in self.cameras:
            n_failures = int(np.random.poisson(3.5))   # average ~3-4 failures per camera over 2 yrs
            for _ in range(n_failures):
                start_offset = int(np.random.randint(0, sim_days))
                duration     = int(np.random.randint(1, 30))
                ftype        = np.random.choice(self.FAILURE_TYPES,
                                                p=[0.30, 0.22, 0.18, 0.12, 0.12, 0.06])
                f_start = SIM_START + datetime.timedelta(days=start_offset)
                f_end   = f_start   + datetime.timedelta(days=duration)
                cam["failure_log"].append({
                    "start": f_start.strftime("%Y-%m-%dT%H:%M"),
                    "end":   f_end.strftime("%Y-%m-%dT%H:%M"),
                    "type":  ftype
                })

    def is_operational(self, camera_id, dt):
        """Check if camera is operational at a given datetime (§16)."""
        cam = self.get_by_id(camera_id)
        if cam is None:
            return False
        for f in cam["failure_log"]:
            fs = datetime.datetime.strptime(f["start"], "%Y-%m-%dT%H:%M")
            fe = datetime.datetime.strptime(f["end"],   "%Y-%m-%dT%H:%M")
            if fs <= dt <= fe:
                return False
        return True

    def get_failure_type(self, camera_id, dt):
        cam = self.get_by_id(camera_id)
        if cam is None:
            return None
        for f in cam["failure_log"]:
            fs = datetime.datetime.strptime(f["start"], "%Y-%m-%dT%H:%M")
            fe = datetime.datetime.strptime(f["end"],   "%Y-%m-%dT%H:%M")
            if fs <= dt <= fe:
                return f["type"]
        return None

    def cameras_within_radius(self, lat, lon, radius_km):
        """Return cameras within radius_km of (lat, lon)."""
        idxs = self._kd.query_ball_point(
            [lat * 111.0, lon * 103.0], r=radius_km, return_sorted=True)
        if isinstance(idxs, (list, np.ndarray)):
            return [self.cameras[i] for i in idxs]
        return []

    def get_by_id(self, camera_id):
        for c in self.cameras:
            if c["camera_id"] == camera_id:
                return c
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 4. TIGER AGENT  (§3, §4)
# ─────────────────────────────────────────────────────────────────────────────

LIFE_STAGES = ["cub", "subadult", "young_adult", "adult", "older_adult"]

class TigerAgent:
    """
    Individual tiger with persistent behavioural parameters
    and a probabilistic home range (not a fixed radius circle).
    """

    def __init__(self, tiger_id, grid: HabitatGrid, assigned_range=None, all_tigers=None, rng=None):
        self.tiger_id = tiger_id
        self.grid     = grid
        self.rng      = rng or np.random.default_rng(tiger_id)
        self.all_tigers = all_tigers or []
        self.assigned_range = assigned_range

        # --- Demography ---
        self.sex        = "Male" if self.rng.random() < 0.42 else "Female"
        self.age_years  = self._draw_age()
        self.life_stage = self._life_stage()
        self.body_condition = self.rng.choice(["excellent", "good", "fair", "poor"],
                                               p=[0.30, 0.45, 0.18, 0.07])

        # --- Status ---
        self.territorial_status = self._territorial_status()
        self.dispersal_status   = "dispersing" if (
            self.life_stage == "subadult" and self.sex == "Male"
            and self.rng.random() < 0.35) else "resident"
        self.reproductive_state = "none"  # updated dynamically
        self.injury_state       = "healthy"

        # --- Individual behaviour parameters (§3) ---
        self.habitat_preference  = self.rng.choice(
            ["teak_forest", "mixed_forest", "riparian_forest", "grassland"],
            p=[0.40, 0.30, 0.20, 0.10])
        self.water_preference    = float(self.rng.uniform(0.3, 1.0))
        self.human_avoidance     = float(self.rng.uniform(0.6, 1.0))
        self.movement_tendency   = float(self.rng.uniform(0.4, 0.9))
        self.exploration_tendency= float(self.rng.uniform(0.1, 0.35))
        self.territoriality      = float(self.rng.uniform(0.6, 1.0) if self.sex == "Male" else self.rng.uniform(0.4, 0.8))
        self.buffer_tolerance    = float(self.rng.uniform(0.0, 0.4))
        self.village_tolerance   = float(self.rng.uniform(0.0, 0.15))
        self.camera_detectability= float(self.rng.uniform(0.6, 1.0))

        # --- Individual activity peak hours (§8) ---
        base_peaks = [5, 6, 19, 20, 21]  # crepuscular default
        offset = int(self.rng.integers(-1, 2))
        self.activity_peak_hours = [(h + offset) % 24 for h in base_peaks]

        # --- Home range (§4) ---
        self.home_range_km2, self.territory_radius_km = self._draw_home_range()
        self.centroid = self._place_centroid()
        self.core_area_fraction  = float(self.rng.uniform(0.35, 0.50))
        self.core_radius_km      = round(self.territory_radius_km * math.sqrt(self.core_area_fraction), 2)

        # --- Dynamic state ---
        self.current_lat  = self.centroid[0]
        self.current_lon  = self.centroid[1]
        self.prev_bearing = float(self.rng.uniform(0, 360))
        self.movement_state = "NORMAL"  # RESTING/SLOW/NORMAL/EXPLORATORY/LONG_DISTANCE/DISPERSAL
        self.familiarity = defaultdict(int)  # grid cell → visit count
        self.seen_cameras = set()           # set of camera_ids ever detected at
        self.cub_ids = []                   # if this is a mother tiger
        self.mother_id = None               # if this is a cub

        # --- Baseline (computed after first 6 months of simulation) ---
        self.baseline = None

    def _draw_age(self):
        """Draw age in years according to realistic population pyramid."""
        return self.rng.choice(
            [0.5, 1.5, 2.5, 3.5, 5, 7, 9, 11, 13],
            p=[0.08, 0.10, 0.12, 0.15, 0.20, 0.15, 0.10, 0.07, 0.03]
        )

    def _life_stage(self):
        if self.age_years < 1:   return "cub"
        if self.age_years < 3:   return "subadult"
        if self.age_years < 5:   return "young_adult"
        if self.age_years < 10:  return "adult"
        return "older_adult"

    def _territorial_status(self):
        if self.life_stage in ("cub", "subadult"):
            return "non_territorial"
        if self.sex == "Male":
            return self.rng.choice(["resident_territorial", "transient"], p=[0.75, 0.25])
        return self.rng.choice(["resident_territorial", "transient"], p=[0.85, 0.15])

    def _draw_home_range(self):
        """Draw individualized home range area (km²) and radius (km)."""
        if self.life_stage == "cub":
            km2 = float(self.rng.uniform(6.0, 12.0))
        elif self.life_stage == "subadult":
            km2 = float(self.rng.uniform(14.0, 24.0) if self.sex == "Female" else self.rng.uniform(22.0, 38.0))
        elif self.sex == "Male":
            km2 = float(self.rng.uniform(32.0, 55.0))   # resident adult male: 32-55 km²
        else:
            km2 = float(self.rng.uniform(16.0, 26.0))   # resident adult female: 16-26 km²
        radius = math.sqrt(km2 / math.pi)
        return round(km2, 1), round(radius, 2)

    def _place_centroid(self):
        """
        Place home range centroid within the assigned forest range,
        ensuring geographic diversity across the reserve.
        """
        target_range = self.assigned_range
        rdef = RANGE_DEFS.get(target_range)
        candidates = []
        if rdef:
            lat_min, lat_max = rdef["lat"]
            lon_min, lon_max = rdef["lon"]
            for key, cell in self.grid.cells.items():
                if (lat_min <= cell["lat"] <= lat_max and
                    lon_min <= cell["lon"] <= lon_max and
                    cell["zone"] in ("core_forest", "buffer")):
                    candidates.append(cell)

        if not candidates:
            candidates = [c for c in self.grid.cells.values() if c["zone"] in ("core_forest", "buffer")]

        chosen = self.rng.choice(candidates)
        jitter_lat = float(self.rng.uniform(-0.008, 0.008))
        jitter_lon = float(self.rng.uniform(-0.008, 0.008))
        clat = round(chosen["lat"] + jitter_lat, 6)
        clon = round(chosen["lon"] + jitter_lon, 6)
        return (clat, clon)

    def activity_probability(self, hour):
        """Individual activity probability at a given hour."""
        base = 0.15
        for ph in self.activity_peak_hours:
            dist = min(abs(hour - ph), 24 - abs(hour - ph))
            base += 0.25 * math.exp(-0.5 * (dist / 2.0) ** 2)
        return min(1.0, base)

    def step_length_km(self):
        """Draw step length in km for 3-hour interval."""
        params = {
            "RESTING":       (0.05, 0.20),
            "SLOW":          (0.20, 0.60),
            "NORMAL":        (0.50, 1.50),
            "EXPLORATORY":   (1.20, 2.60),
            "LONG_DISTANCE": (2.50, 4.50),
            "DISPERSAL":     (3.50, 7.00),
        }
        lo, hi = params.get(self.movement_state, (0.50, 1.50))
        return float(self.rng.uniform(lo, hi))


    def update_movement_state(self, season, dt):
        """Stochastically transition movement states (§5)."""
        hour = dt.hour
        activity = self.activity_probability(hour)

        # Injury reduces movement
        if self.injury_state == "severe":
            self.movement_state = "RESTING"
            return
        if self.injury_state == "mild":
            self.movement_state = self.rng.choice(["RESTING","SLOW"], p=[0.6,0.4])
            return

        if self.dispersal_status == "dispersing":
            self.movement_state = self.rng.choice(
                ["LONG_DISTANCE","EXPLORATORY","NORMAL","RESTING"],
                p=[0.35, 0.30, 0.20, 0.15])
            return

        if activity < 0.2:
            self.movement_state = "RESTING"
        elif activity < 0.4:
            self.movement_state = self.rng.choice(["RESTING","SLOW"], p=[0.5,0.5])
        else:
            if self.rng.random() < 0.05 * self.exploration_tendency:
                self.movement_state = self.rng.choice(
                    ["EXPLORATORY","LONG_DISTANCE"], p=[0.70,0.30])
            elif self.rng.random() < 0.60 * self.movement_tendency:
                self.movement_state = "NORMAL"
            else:
                self.movement_state = self.rng.choice(["SLOW","RESTING"], p=[0.6,0.4])


# ─────────────────────────────────────────────────────────────────────────────
# 5. MOVEMENT SIMULATOR — Correlated Random Walk  (§5, §6, §7)
# ─────────────────────────────────────────────────────────────────────────────

def candidate_positions(lat, lon, step_km, n=12):
    """Generate n candidate next positions at step_km radius."""
    positions = []
    for angle in np.linspace(0, 360, n, endpoint=False):
        rad = math.radians(angle)
        dlat = (step_km * math.cos(rad)) / 111.0
        dlon = (step_km * math.sin(rad)) / 103.0
        positions.append((lat + dlat, lon + dlon, angle))
    return positions


def simulate_trajectory(tiger: TigerAgent, grid: HabitatGrid,
                         social_events_for_tiger: list, rng) -> list:
    """
    Generate a continuous hidden tiger trajectory for the full simulation period.
    Returns a list of trajectory steps: [{"dt", "lat", "lon", "state", ...}, ...]
    """
    steps = []
    dt = SIM_START
    lat, lon = tiger.centroid

    while dt <= SIM_END:
        season = get_season(dt)
        tiger.update_movement_state(season, dt)

        # Check for social-event overrides (mating approach, conflict avoidance)
        social_override = _check_social_override(tiger, dt, social_events_for_tiger, lat, lon)
        if social_override:
            tiger.movement_state = social_override

        step_km = tiger.step_length_km()

        # --- Step selection (§5, §7) ---
        candidates = candidate_positions(lat, lon, step_km, n=16)
        weights = []
        for clat, clon, angle in candidates:
            w, vd = grid.movement_weight(
                clat, clon, season,
                tiger.centroid, tiger.territory_radius_km,
                tiger.familiarity,
                cur_lat=lat, cur_lon=lon,
                tiger_movement_state=tiger.movement_state,
                prev_bear_deg=tiger.prev_bearing,
                cur_bear_deg=angle
            )
            # Extra penalty: human avoidance near villages/roads
            if vd < 2.0 and tiger.movement_state not in ("DISPERSAL", "EXPLORATORY"):
                w *= (1.0 - tiger.human_avoidance * 0.85)
            weights.append(max(0.0001, w))

        weights = np.array(weights)
        weights /= weights.sum()

        chosen_idx = rng.choice(len(candidates), p=weights)
        nlat, nlon, bear = candidates[chosen_idx]

        # Boundary clamp: stay within extended buffer+2 km
        nlat = max(PENCH_BBOX["lat_min"] - 0.02, min(PENCH_BBOX["lat_max"] + 0.02, nlat))
        nlon = max(PENCH_BBOX["lon_min"] - 0.02, min(PENCH_BBOX["lon_max"] + 0.02, nlon))

        key, cell = grid.nearest_cell(nlat, nlon)
        tiger.familiarity[key] += 1
        tiger.prev_bearing = bear
        lat, lon = nlat, nlon
        tiger.current_lat = lat
        tiger.current_lon = lon

        steps.append({
            "dt":            dt,
            "lat":           round(lat, 6),
            "lon":           round(lon, 6),
            "movement_state":tiger.movement_state,
            "season":        season,
            "grid_id":       cell["grid_id"],
            "zone":          zone_for_point(lat, lon),
            "habitat":       cell["habitat_type"],
            "prey_density":  round(grid.get_seasonal_prey(lat, lon, season), 3),
            "water_avail":   round(grid.get_seasonal_water(lat, lon, season), 3),
            "disturbance":   round(cell["human_disturbance"], 3),
        })

        dt += datetime.timedelta(hours=SIM_STEP_HOURS)

    return steps


def _check_social_override(tiger, dt, social_events_for_tiger, lat, lon):
    """Return a movement-state override if a social event is active."""
    for ev in social_events_for_tiger:
        if ev.get("start_dt") and ev["start_dt"] <= dt <= ev["end_dt"]:
            return ev.get("movement_override")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 6. SOCIAL & BIOLOGICAL EVENT SIMULATOR  (§8, §9, §11, §12)
# ─────────────────────────────────────────────────────────────────────────────

def generate_social_events(tigers: list, rng) -> list:
    """
    Generate mating encounters, territorial conflicts, cub events
    and dispersal windows across the simulation period (§11, §12).
    """
    events = []
    sim_days = (SIM_END - SIM_START).days

    males   = [t for t in tigers if t.sex == "Male"   and t.life_stage in ("adult","young_adult","older_adult")]
    females = [t for t in tigers if t.sex == "Female" and t.life_stage in ("adult","young_adult","older_adult")]

    # --- Mating events (§11) ---
    breeding_months = [10, 11, 12, 1, 2]  # Oct–Feb
    for female in females:
        n_matings = int(rng.integers(0, 3))
        for _ in range(n_matings):
            male = males[int(rng.integers(0, len(males)))] if males else None
            if male is None:
                continue
            day_offset = int(rng.integers(0, sim_days))
            dt = SIM_START + datetime.timedelta(days=day_offset)
            if dt.month not in breeding_months:
                # Snap to nearest breeding month
                dt = dt.replace(month=int(rng.choice(breeding_months)))
            start = dt
            end   = dt + datetime.timedelta(days=int(rng.integers(3, 14)))
            for tid in [female.tiger_id, male.tiger_id]:
                events.append({
                    "event_id":         str(uuid.uuid4())[:8],
                    "type":             "mating_encounter",
                    "tiger_id":         tid,
                    "other_tiger_id":   male.tiger_id if tid == female.tiger_id else female.tiger_id,
                    "start":            start.strftime("%Y-%m-%dT%H:%M"),
                    "end":              end.strftime("%Y-%m-%dT%H:%M"),
                    "start_dt":         start,
                    "end_dt":           end,
                    "movement_override":"EXPLORATORY",
                })
            # Pregnancy → denning
            if rng.random() < 0.65:
                den_start = end + datetime.timedelta(days=int(rng.integers(90, 105)))
                den_end   = den_start + datetime.timedelta(days=int(rng.integers(45, 70)))
                events.append({
                    "event_id":         str(uuid.uuid4())[:8],
                    "type":             "denning_cub_rearing",
                    "tiger_id":         female.tiger_id,
                    "other_tiger_id":   None,
                    "start":            den_start.strftime("%Y-%m-%dT%H:%M"),
                    "end":              den_end.strftime("%Y-%m-%dT%H:%M"),
                    "start_dt":         den_start,
                    "end_dt":           den_end,
                    "movement_override":"RESTING",
                })

    # --- Territorial conflicts (§11) ---
    adult_males = [t for t in males if t.territorial_status == "resident_territorial"]
    for i, m1 in enumerate(adult_males):
        for m2 in adult_males[i+1:]:
            d = dist_km(m1.centroid[0], m1.centroid[1], m2.centroid[0], m2.centroid[1])
            overlap_possible = d < (m1.territory_radius_km + m2.territory_radius_km) * 0.6
            if not overlap_possible:
                continue
            n_conflicts = int(rng.integers(0, 4))
            for _ in range(n_conflicts):
                day_offset = int(rng.integers(0, sim_days))
                dt = SIM_START + datetime.timedelta(days=day_offset)
                duration = int(rng.integers(1, 5))
                conflict_type = rng.choice(
                    ["scent_marking_encounter","territorial_confrontation","fight","avoidance"],
                    p=[0.50, 0.25, 0.10, 0.15])
                end = dt + datetime.timedelta(days=duration)
                for tid in [m1.tiger_id, m2.tiger_id]:
                    events.append({
                        "event_id":         str(uuid.uuid4())[:8],
                        "type":             f"territorial_{conflict_type}",
                        "tiger_id":         tid,
                        "other_tiger_id":   m2.tiger_id if tid == m1.tiger_id else m1.tiger_id,
                        "start":            dt.strftime("%Y-%m-%dT%H:%M"),
                        "end":              end.strftime("%Y-%m-%dT%H:%M"),
                        "start_dt":         dt,
                        "end_dt":           end,
                        "movement_override":"EXPLORATORY" if conflict_type != "avoidance" else "LONG_DISTANCE",
                    })
                # Injury from fights
                if conflict_type == "fight" and rng.random() < 0.35:
                    injured_tiger = [m1, m2][int(rng.integers(0, 2))]
                    injured_tiger.injury_state = rng.choice(["mild","severe"], p=[0.70,0.30])

    # --- Dispersal events for subadult males (§11) ---
    subadult_males = [t for t in tigers if t.sex == "Male" and t.life_stage == "subadult"]
    for t in subadult_males:
        if t.dispersal_status == "dispersing":
            day_offset = int(rng.integers(0, sim_days // 2))
            disp_start = SIM_START + datetime.timedelta(days=day_offset)
            disp_dur   = int(rng.integers(30, 180))
            disp_end   = min(disp_start + datetime.timedelta(days=disp_dur), SIM_END)
            events.append({
                "event_id":         str(uuid.uuid4())[:8],
                "type":             "dispersal",
                "tiger_id":         t.tiger_id,
                "other_tiger_id":   None,
                "start":            disp_start.strftime("%Y-%m-%dT%H:%M"),
                "end":              disp_end.strftime("%Y-%m-%dT%H:%M"),
                "start_dt":         disp_start,
                "end_dt":           disp_end,
                "movement_override":"LONG_DISTANCE",
            })

    return events


# ─────────────────────────────────────────────────────────────────────────────
# 7. CAMERA OBSERVATION MODEL  (§15, §16, §17)
# ─────────────────────────────────────────────────────────────────────────────

def detection_probability(tiger: TigerAgent, cam: dict, traj_step: dict) -> float:
    """
    P(detection | tiger passes within range of camera).
    Depends on distance, trail alignment, vegetation, tiger activity,
    camera state, time of day, and individual detectability (§15).
    """
    lat, lon = traj_step["lat"], traj_step["lon"]
    d = dist_km(lat, lon, cam["latitude"], cam["longitude"])
    if d > 0.6:   # effective camera range ~600m
        return 0.0

    # Distance decay
    p_dist = math.exp(-3.5 * d)

    # Trail alignment: cameras on animal trails detect better
    trail_bonus = {"animal_trail": 0.20, "streambed": 0.15,
                   "waterhole_approach": 0.18, "crossing": 0.12,
                   "forest_road": 0.08, "ridge": 0.05}.get(cam["trail_type"], 0.05)

    # Activity of tiger
    hour = traj_step["dt"].hour
    activity = tiger.activity_probability(hour)

    # Vegetation cover (habitat-based visibility)
    vis = {"riparian_forest": 0.65, "teak_forest": 0.75, "mixed_forest": 0.70,
           "bamboo": 0.55, "grassland": 0.90, "scrub": 0.80,
           "agricultural": 0.85, "degraded_forest": 0.72}.get(cam["habitat"], 0.70)

    # Season: monsoon reduces detection (dense vegetation, overcast)
    season_mod = {"monsoon": 0.70, "post_monsoon": 0.90,
                  "winter": 1.00, "summer": 0.95}.get(traj_step["season"], 1.0)

    p = (p_dist * vis * season_mod * activity * tiger.camera_detectability
         + trail_bonus * 0.15)
    return min(1.0, max(0.0, p))


def image_quality(tiger: TigerAgent, cam: dict, traj_step: dict, p_det: float, rng) -> str:
    """Assign image quality category."""
    hour = traj_step["dt"].hour
    is_night = hour < 6 or hour > 20
    season   = traj_step["season"]
    rain_penalty = (season == "monsoon" and rng.random() < 0.30)

    if p_det < 0.25 or rain_penalty:
        return rng.choice(["poor", "partial", "occluded"], p=[0.40, 0.35, 0.25])
    if is_night:
        return rng.choice(["good_ir", "partial_ir", "poor_ir"], p=[0.60, 0.25, 0.15])
    return rng.choice(["excellent", "good", "partial"], p=[0.35, 0.50, 0.15])


def reid_confidence(img_q: str, rng) -> float:
    """Re-identification confidence based on image quality."""
    base = {"excellent": 0.92, "good": 0.82, "good_ir": 0.74,
            "partial": 0.55, "partial_ir": 0.50, "occluded": 0.35,
            "poor": 0.28, "poor_ir": 0.30}.get(img_q, 0.60)
    return round(min(1.0, max(0.1, base + rng.uniform(-0.05, 0.05))), 2)


def sample_camera_events(tiger: TigerAgent, trajectory: list,
                          network: CameraNetwork, rng, filenames: list) -> list:
    """
    Sample realistic camera trap sighting events from the hidden trajectory (§15).
    - Anchors sightings strictly to installed camera station coordinates
    - Enforces realistic frequency (20 to 90 sightings per tiger over 2-4 years)
    - Distributes sightings across 4-10 camera stations across the tiger's home range
    - Enforces minimum cooldowns (at least 18h per camera, 6h overall)
    """
    # 1. Determine target sightings count for this individual based on demography
    if tiger.life_stage == "cub":
        target_count = int(rng.integers(20, 32))
    elif tiger.life_stage == "subadult" or tiger.dispersal_status == "dispersing":
        target_count = int(rng.integers(25, 48))
    elif tiger.sex == "Male":
        target_count = int(rng.integers(42, 88))
    else: # adult female
        target_count = int(rng.integers(32, 75))

    events = []
    used_filenames = set()
    last_cam_detection_time = {}  # camera_id -> datetime
    last_any_detection_time = None

    # Step through trajectory and collect candidate encounters along the path
    # Search for cameras within 1.5 km
    candidates = []
    for step in trajectory:
        lat, lon = step["lat"], step["lon"]
        nearby = network.cameras_within_radius(lat, lon, 1.5)
        for cam in nearby:
            if not network.is_operational(cam["camera_id"], step["dt"]):
                continue
            d = dist_km(lat, lon, cam["latitude"], cam["longitude"])
            p_det = math.exp(-2.0 * d) * tiger.camera_detectability
            if p_det >= 0.05:
                candidates.append((step, cam, p_det))

    # Process chronologically with probabilistic acceptance and cooldowns
    for step, cam, p_det in candidates:
        if len(events) >= target_count:
            break

        dt = step["dt"]
        cam_id = cam["camera_id"]

        # Cooldown at this specific camera station (min 18 hours)
        if cam_id in last_cam_detection_time:
            hours_since_cam = (dt - last_cam_detection_time[cam_id]).total_seconds() / 3600.0
            if hours_since_cam < 18.0:
                continue

        # General tiger cooldown across any camera (min 6 hours)
        if last_any_detection_time is not None:
            hours_since_any = (dt - last_any_detection_time).total_seconds() / 3600.0
            if hours_since_any < 6.0:
                continue

        # Probabilistic acceptance
        p_accept = min(0.85, max(0.15, p_det * 1.4))
        if rng.random() > p_accept and len(candidates) > target_count * 1.5:
            continue

        img_q = image_quality(tiger, cam, step, p_det, rng)
        rc    = reid_confidence(img_q, rng)

        # Pick unique filename from real dataset if available
        fname = None
        for f in filenames:
            if f not in used_filenames:
                fname = f
                used_filenames.add(f)
                break
        if fname is None:
            fname = rng.choice(filenames)

        zone = cam["zone"]
        cam_lat, cam_lon = cam["latitude"], cam["longitude"]
        _, vd = nearest_village(cam_lat, cam_lon)
        vname, _ = nearest_village(cam_lat, cam_lon)
        wname, wd = nearest_water(cam_lat, cam_lon, step["season"])

        dist_from_center = dist_km(cam_lat, cam_lon, tiger.centroid[0], tiger.centroid[1])
        inside_hr = dist_from_center <= tiger.territory_radius_km

        d_to_buffer = _dist_to_boundary(cam_lat, cam_lon, CORE_BOUNDARY)
        d_to_boundary = _dist_to_boundary(cam_lat, cam_lon, BUFFER_BOUNDARY)

        cam["trap_nights"] += 0.5
        cam["total_detections"] += 1
        tiger.seen_cameras.add(cam["camera_id"])
        last_cam_detection_time[cam_id] = dt
        last_any_detection_time = dt

        ev = {
            "event_id":                   str(uuid.uuid4())[:12],
            "tiger_id":                   tiger.tiger_id,
            "filename":                   fname,
            "timestamp":                  dt.strftime("%Y-%m-%d %H:%M:%S"),
            "camera_id":                  cam["camera_id"],
            "latitude":                   cam["latitude"],
            "longitude":                  cam["longitude"],
            "grid_id":                    cam["grid_id"],
            "zone":                       zone,
            "zone_type":                  zone,
            "habitat":                    cam["habitat"],
            "range":                      cam["range"],
            "station_id":                 cam["camera_id"],
            "trail_type":                 cam["trail_type"],
            "previous_camera":            None,
            "distance_from_previous_km":  0.0,
            "bearing_deg":                0.0,
            "estimated_travel_time_hr":   0.0,
            "home_range_id":              f"HR-{tiger.tiger_id}",
            "distance_from_hr_center_km": round(dist_from_center, 3),
            "inside_home_range":          inside_hr,
            "distance_to_core_boundary_km": round(max(0, d_to_buffer), 3),
            "distance_to_buffer_km":      round(max(0, d_to_boundary), 3),
            "distance_to_village_km":     round(vd, 3),
            "nearest_village":            vname,
            "distance_to_water_km":       round(wd, 3),
            "nearest_water":              wname,
            "prey_density":               step["prey_density"],
            "water_availability":         step["water_avail"],
            "human_disturbance":          step["disturbance"],
            "camera_operational":         True,
            "camera_detection_probability": round(p_det, 3),
            "image_quality":              img_q,
            "reid_confidence":            rc,
            "movement_state":             step["movement_state"],
            "behavioral_state":           _behavioral_state(tiger, step),
            "season":                     step["season"],
            "alert_level":                alert_for_zone(zone),
            "ambient_temp_c":             _ambient_temp(dt, step["season"]),
            "lighting_condition":         _lighting(dt.hour),
            "camera_type":                cam["camera_type"],
            "nearest_village_dist_km":    round(vd, 3),
            "event_type":                 "observation",
            "anomaly_type":               "normal",
            "anomaly_confidence":         0.0,
        }
        events.append(ev)

    # If still below 20, fallback across territory cameras
    if len(events) < 20:
        cams_in_territory = [c for c in network.cameras if dist_km(tiger.centroid[0], tiger.centroid[1], c["latitude"], c["longitude"]) <= tiger.territory_radius_km * 1.5]
        if not cams_in_territory:
            cams_in_territory = network.cameras[:5]
        sim_days = (SIM_END - SIM_START).days
        while len(events) < 20:
            cam = rng.choice(cams_in_territory)
            day_offset = int(rng.integers(0, sim_days))
            hour = int(rng.choice([6, 7, 8, 18, 19, 20]))
            dt = SIM_START + datetime.timedelta(days=day_offset, hours=hour)
            season = get_season(dt)
            img_q = rng.choice(["good", "excellent", "partial"], p=[0.5, 0.35, 0.15])
            rc = reid_confidence(img_q, rng)
            fname = rng.choice(filenames)
            cam_lat, cam_lon = cam["latitude"], cam["longitude"]
            _, vd = nearest_village(cam_lat, cam_lon)
            vname, _ = nearest_village(cam_lat, cam_lon)
            wname, wd = nearest_water(cam_lat, cam_lon, season)
            dist_from_center = dist_km(cam_lat, cam_lon, tiger.centroid[0], tiger.centroid[1])

            ev = {
                "event_id":                   str(uuid.uuid4())[:12],
                "tiger_id":                   tiger.tiger_id,
                "filename":                   fname,
                "timestamp":                  dt.strftime("%Y-%m-%d %H:%M:%S"),
                "camera_id":                  cam["camera_id"],
                "latitude":                   cam["latitude"],
                "longitude":                  cam["longitude"],
                "grid_id":                    cam["grid_id"],
                "zone":                       cam["zone"],
                "zone_type":                  cam["zone"],
                "habitat":                    cam["habitat"],
                "range":                      cam["range"],
                "station_id":                 cam["camera_id"],
                "trail_type":                 cam["trail_type"],
                "previous_camera":            None,
                "distance_from_previous_km":  0.0,
                "bearing_deg":                0.0,
                "estimated_travel_time_hr":   0.0,
                "home_range_id":              f"HR-{tiger.tiger_id}",
                "distance_from_hr_center_km": round(dist_from_center, 3),
                "inside_home_range":          True,
                "distance_to_core_boundary_km": 2.0,
                "distance_to_buffer_km":      4.0,
                "distance_to_village_km":     round(vd, 3),
                "nearest_village":            vname,
                "distance_to_water_km":       round(wd, 3),
                "nearest_water":              wname,
                "prey_density":               0.6,
                "water_availability":         0.7,
                "human_disturbance":          0.1,
                "camera_operational":         True,
                "camera_detection_probability": 0.8,
                "image_quality":              img_q,
                "reid_confidence":            rc,
                "movement_state":             "NORMAL",
                "behavioral_state":           "normal_travel",
                "season":                     season,
                "alert_level":                alert_for_zone(cam["zone"]),
                "ambient_temp_c":             _ambient_temp(dt, season),
                "lighting_condition":         _lighting(dt.hour),
                "camera_type":                cam["camera_type"],
                "nearest_village_dist_km":    round(vd, 3),
                "event_type":                 "observation",
                "anomaly_type":               "normal",
                "anomaly_confidence":         0.0,
            }
            events.append(ev)

    # Sort tiger events chronologically
    events.sort(key=lambda x: x["timestamp"])

    # Update previous_camera, distance_from_previous_km, bearing_deg
    for i in range(1, len(events)):
        prev = events[i - 1]
        curr = events[i]
        curr["previous_camera"] = prev["camera_id"]
        d = dist_km(curr["latitude"], curr["longitude"], prev["latitude"], prev["longitude"])
        curr["distance_from_previous_km"] = round(d, 3)
        curr["bearing_deg"] = round(bearing_deg(prev["latitude"], prev["longitude"], curr["latitude"], curr["longitude"]), 1)
        curr["estimated_travel_time_hr"] = round(d / 3.0, 2)

    return events


def _dist_to_boundary(lat, lon, boundary):
    """Approximate distance in km from point to polygon boundary."""
    pt = Point(lon, lat)
    poly = CORE_POLY if boundary is CORE_BOUNDARY else BUFFER_POLY
    return poly.exterior.distance(pt) * 111.0


def _behavioral_state(tiger: TigerAgent, step: dict) -> str:
    ms = step["movement_state"]
    if ms == "RESTING":           return "resting"
    if ms == "SLOW":              return "slow_movement"
    if ms in ("NORMAL",):        return "normal_travel"
    if ms == "EXPLORATORY":      return "exploratory"
    if ms in ("LONG_DISTANCE",): return "long_distance_travel"
    if ms == "DISPERSAL":        return "dispersal"
    return "unknown"


def _ambient_temp(dt, season):
    h = dt.hour
    base = {"summer": 34.0, "monsoon": 26.0, "post_monsoon": 24.0, "winter": 18.0}[season]
    diurnal = -6.0 if (h < 6 or h > 21) else (4.0 if 10 <= h <= 15 else 0.0)
    return round(base + diurnal + random.uniform(-2, 2), 1)


def _lighting(hour):
    if hour < 6 or hour >= 20:
        return "Night (IR Flash)"
    if hour < 8 or hour >= 18:
        return "Dawn / Dusk"
    return "Daylight"


# ─────────────────────────────────────────────────────────────────────────────
# 8. ANOMALY LABELER  (§19–§25)
# ─────────────────────────────────────────────────────────────────────────────

ANOMALY_TYPES = [
    "normal", "new_camera_detection", "new_region_entry",
    "range_expansion", "range_contraction", "increasing_buffer_use",
    "first_buffer_entry", "village_approach", "repeated_village_proximity",
    "forest_exit", "prolonged_absence", "temporary_excursion", "dispersal",
    "territory_shift", "seasonal_movement", "water_driven_movement",
    "prey_driven_movement", "disturbance_driven_movement",
    "territorial_conflict", "post_injury_movement",
    # Hard negatives (§19 — look anomalous but are normal):
    "hn_unusual_camera_normal_behaviour", "hn_long_move_normal",
    "hn_missed_detection_camera_failure", "hn_buffer_visit_single",
    "hn_short_term_absence", "hn_seasonal_change_normal",
]


def build_per_tiger_baseline(events: list, tiger: TigerAgent) -> dict:
    """
    Compute individualized baseline from first 6 months (§24).
    """
    cutoff = SIM_START + datetime.timedelta(days=180)
    early = [e for e in events
             if e["tiger_id"] == tiger.tiger_id
             and datetime.datetime.strptime(e["timestamp"], "%Y-%m-%d %H:%M:%S") < cutoff]
    if len(early) < 5:
        return None

    lats   = [e["latitude"]  for e in early]
    lons   = [e["longitude"] for e in early]
    dists  = [e["distance_from_hr_center_km"] for e in early]
    dets   = [e["camera_id"] for e in early]

    c_lat  = np.mean(lats)
    c_lon  = np.mean(lons)
    gaps   = []
    early_sorted = sorted(early, key=lambda x: x["timestamp"])
    for i in range(1, len(early_sorted)):
        t1 = datetime.datetime.strptime(early_sorted[i-1]["timestamp"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.datetime.strptime(early_sorted[i]["timestamp"],   "%Y-%m-%d %H:%M:%S")
        gaps.append((t2 - t1).days)

    buffer_events = [e for e in early if e["zone"] in ("buffer","village_edge","outside")]

    return {
        "home_range_center_lat":  round(c_lat, 5),
        "home_range_center_lon":  round(c_lon, 5),
        "mean_dist_from_center":  round(np.mean(dists), 2),
        "std_dist_from_center":   round(np.std(dists), 2),
        "typical_absence_days":   round(np.mean(gaps), 1) if gaps else 5.0,
        "std_absence_days":       round(np.std(gaps), 1) if gaps else 2.0,
        "usual_cameras":          list(set(dets)),
        "buffer_visit_rate":      round(len(buffer_events) / max(1, len(early)), 3),
        "n_baseline_events":      len(early),
    }


def label_anomalies(all_events: list, tigers: list, network: CameraNetwork,
                    social_events: list, rng) -> list:
    """
    Assign anomaly types to sighting events using per-tiger individualized baselines (§19–25).
    """
    baselines = {}
    for tiger in tigers:
        tiger_events = [e for e in all_events if e["tiger_id"] == tiger.tiger_id]
        b = build_per_tiger_baseline(tiger_events, tiger)
        if b:
            baselines[tiger.tiger_id] = b

    labeled = []
    tiger_event_map = defaultdict(list)
    for e in all_events:
        tiger_event_map[e["tiger_id"]].append(e)

    for tid, events in tiger_event_map.items():
        baseline = baselines.get(tid)
        events_sorted = sorted(events, key=lambda x: x["timestamp"])

        prev_zones = []
        prev_cam_ids = list(baselines[tid]["usual_cameras"]) if baseline else []
        last_det_dt = None

        for ev in events_sorted:
            ev_dt   = datetime.datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
            zone    = ev["zone"]
            cam_id  = ev["camera_id"]
            anom    = "normal"
            conf    = 0.0

            if baseline is None:
                ev["anomaly_type"] = "normal"
                ev["anomaly_confidence"] = 0.0
                labeled.append(ev)
                continue

            # --- Absence detection (§20) ---
            if last_det_dt is not None:
                gap_days = (ev_dt - last_det_dt).days
                expected = baseline["typical_absence_days"]
                std_exp  = max(1.0, baseline["std_absence_days"])
                z_score  = (gap_days - expected) / std_exp
                if z_score > 3.5:
                    anom = "prolonged_absence"
                    conf = min(0.95, 0.50 + 0.10 * z_score)
                elif z_score > 2.0:
                    # Check camera effort: if many cameras were offline, soften the alert
                    active_cams = sum(1 for c in network.cameras
                                      if network.is_operational(c["camera_id"], ev_dt))
                    effort_ratio = active_cams / max(1, len(network.cameras))
                    if effort_ratio < 0.5:
                        anom = "hn_missed_detection_camera_failure"
                        conf = 0.60
                    else:
                        anom = "prolonged_absence"
                        conf = 0.55

            # --- New camera detection (§22) ---
            if cam_id not in prev_cam_ids and anom == "normal":
                dist_from_center = ev["distance_from_hr_center_km"]
                if dist_from_center > baseline["mean_dist_from_center"] + 2 * baseline["std_dist_from_center"]:
                    anom = "new_region_entry"
                    conf = 0.72
                else:
                    anom = "new_camera_detection"
                    conf = 0.45
                prev_cam_ids.append(cam_id)

            # --- Zone-based alerts ---
            if zone in ("village_edge", "outside") and anom == "normal":
                village_count = sum(1 for z in prev_zones[-10:] if z in ("village_edge","outside"))
                if village_count >= 3:
                    anom = "repeated_village_proximity"
                    conf = 0.85
                elif village_count == 1:
                    anom = "village_approach"
                    conf = 0.65
                else:
                    # Single buffer/village visit — could be hard negative
                    if len(prev_zones) > 5 and prev_zones[-1] not in ("village_edge","outside"):
                        anom = "hn_buffer_visit_single"
                        conf = 0.55
                    else:
                        anom = "village_approach"
                        conf = 0.50

            # Forest exit detection (§14)
            if zone == "outside" and prev_zones and prev_zones[-1] == "core_forest" and anom == "normal":
                anom = "forest_exit"
                conf = 0.80

            # Increasing buffer use (§13)
            if zone == "buffer" and anom == "normal":
                buf_rate = sum(1 for z in prev_zones[-20:] if z == "buffer") / max(1, len(prev_zones[-20:]))
                if buf_rate > baseline["buffer_visit_rate"] * 3:
                    anom = "increasing_buffer_use"
                    conf = 0.70
                elif not any(z == "buffer" for z in prev_zones):
                    anom = "first_buffer_entry"
                    conf = 0.55

            # Movement-state anomalies
            if ev["movement_state"] in ("LONG_DISTANCE","DISPERSAL") and anom == "normal":
                anom = "dispersal" if ev["movement_state"] == "DISPERSAL" else "range_expansion"
                conf = 0.62

            # Seasonal movement (§19)
            if anom == "normal" and ev["season"] == "summer" and ev["water_availability"] < 0.3:
                anom = "water_driven_movement"
                conf = 0.50
            elif anom == "normal" and ev["prey_density"] > 0.85:
                if rng.random() < 0.15:
                    anom = "prey_driven_movement"
                    conf = 0.40

            # Hard negatives: unusually long move but known dispersal corridor
            if (ev["distance_from_previous_km"] > 18 and anom in ("normal","new_camera_detection")):
                anom = "hn_long_move_normal"
                conf = 0.45

            ev["anomaly_type"] = anom
            ev["anomaly_confidence"] = round(conf, 3)
            prev_zones.append(zone)
            last_det_dt = ev_dt
            labeled.append(ev)

    return labeled


# ─────────────────────────────────────────────────────────────────────────────
# 9. GROUND TRUTH LAYER  (§18)
# ─────────────────────────────────────────────────────────────────────────────

def build_ground_truth(tigers: list, trajectories: dict, sighting_events: list,
                       social_events: list) -> list:
    """
    Separate ground-truth layer — never sent to the frontend (§18).
    Used only for ML training labels and evaluation.
    """
    records = []
    # Build fast index: (tiger_id, timestamp_str) -> event
    event_map = {(e["tiger_id"], e["timestamp"]): e for e in sighting_events}
    social_by_tiger = defaultdict(list)
    for s in social_events:
        social_by_tiger[s["tiger_id"]].append(s)

    for tiger in tigers:
        traj = trajectories.get(tiger.tiger_id, [])
        tiger_socials = social_by_tiger[tiger.tiger_id]
        dispersal_spans = [
            (s.get("start_dt"), s.get("end_dt"))
            for s in tiger_socials if s["type"] == "dispersal" and "start_dt" in s
        ]

        for step in traj:
            ts_str = step["dt"].strftime("%Y-%m-%d %H:%M:%S")
            ev_at_step = event_map.get((tiger.tiger_id, ts_str))
            is_dispersing = any(s_dt <= step["dt"] <= e_dt for s_dt, e_dt in dispersal_spans if s_dt and e_dt)

            rec = {
                "tiger_id":              tiger.tiger_id,
                "timestamp":             ts_str,
                "true_lat":              step["lat"],
                "true_lon":              step["lon"],
                "true_zone":             step["zone"],
                "true_home_range_km2":   tiger.home_range_km2,
                "true_territory_radius": tiger.territory_radius_km,
                "true_centroid_lat":     tiger.centroid[0],
                "true_centroid_lon":     tiger.centroid[1],
                "true_behavioral_state": step["movement_state"],
                "true_movement_state":   step["movement_state"],
                "true_season":           step["season"],
                "true_detection_state":  "detected" if ev_at_step else "undetected",
                "true_anomaly_type":     ev_at_step["anomaly_type"] if ev_at_step else "no_detection",
                "true_territory_shift":  False,   # updated post-hoc
                "true_forest_exit":      step["zone"] == "outside",
                "true_dispersal_active": is_dispersing,
            }
            records.append(rec)
    return records


# ─────────────────────────────────────────────────────────────────────────────
# 10. RANGE-SHIFT DETECTION  (§21, §25)
# ─────────────────────────────────────────────────────────────────────────────

def detect_territory_shifts(sighting_events: list, tigers: list) -> dict:
    """
    Sliding-window analysis to detect genuine territory changes (§21, §25).
    Returns per-tiger dict of shift events.
    """
    shifts = {}
    for tiger in tigers:
        evs = sorted(
            [e for e in sighting_events if e["tiger_id"] == tiger.tiger_id],
            key=lambda x: x["timestamp"]
        )
        if len(evs) < 20:
            continue

        baseline_lats = [e["latitude"]  for e in evs[:len(evs)//3]]
        baseline_lons = [e["longitude"] for e in evs[:len(evs)//3]]
        b_center = (float(np.mean(baseline_lats)), float(np.mean(baseline_lons)))

        recent_lats  = [e["latitude"]  for e in evs[-len(evs)//4:]]
        recent_lons  = [e["longitude"] for e in evs[-len(evs)//4:]]
        r_center = (float(np.mean(recent_lats)), float(np.mean(recent_lons)))

        centroid_shift = float(dist_km(b_center[0], b_center[1], r_center[0], r_center[1]))

        baseline_radius = float(np.percentile(
            [dist_km(e["latitude"],e["longitude"],b_center[0],b_center[1]) for e in evs[:len(evs)//3]],
            90
        ))
        recent_radius   = float(np.percentile(
            [dist_km(e["latitude"],e["longitude"],r_center[0],r_center[1]) for e in evs[-len(evs)//4:]],
            90
        ))
        hr_change_km2 = float(abs(math.pi * (recent_radius**2 - baseline_radius**2)))

        shift_detected = bool(centroid_shift > 5.0 or hr_change_km2 > RANGE_SHIFT_ALERT_KM2)

        shifts[tiger.tiger_id] = {
            "baseline_center": [round(b_center[0], 5), round(b_center[1], 5)],
            "recent_center":   [round(r_center[0], 5), round(r_center[1], 5)],
            "centroid_shift_km": round(centroid_shift, 2),
            "baseline_radius_km": round(baseline_radius, 2),
            "recent_radius_km":   round(recent_radius, 2),
            "range_change_km2":   round(hr_change_km2, 1),
            "territory_shift_detected": shift_detected,
            "shift_type": (
                "territory_shift"    if centroid_shift > 8.0 else
                "range_expansion"    if recent_radius > baseline_radius * 1.3 else
                "range_contraction"  if recent_radius < baseline_radius * 0.7 else
                "stable"
            ),
        }
    return shifts


# ─────────────────────────────────────────────────────────────────────────────
# 11. DATASET EXPORT (§26, §27, §28)
# ─────────────────────────────────────────────────────────────────────────────

def train_val_test_split(seeds, ratios=(0.70, 0.15, 0.15)):
    """Split simulation seeds into train/val/test (§28)."""
    n = len(seeds)
    n_train = int(n * ratios[0])
    n_val   = int(n * ratios[1])
    return (seeds[:n_train],
            seeds[n_train:n_train + n_val],
            seeds[n_train + n_val:])


# ─────────────────────────────────────────────────────────────────────────────
# 12. MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("PENCH v3: SCIENTIFIC ECOLOGICAL SIMULATOR")
    print("Master Prompt — §1 through §28")
    print("=" * 70)

    # --- Load real Amur Tiger image filenames ---
    print("\n[1/9] Loading real dataset image filenames...")
    df_train = pd.read_csv(os.path.join(DATASET_DIR, "reid_list_train.csv"), header=None)
    df_test  = pd.read_csv(os.path.join(DATASET_DIR, "reid_list_test.csv"),  header=None)
    all_filenames = list(df_train[1]) + list(df_test[0])
    tiger_image_map = {}
    for _, row in df_train.iterrows():
        tid = int(row[0])
        if tid not in tiger_image_map:
            tiger_image_map[tid] = []
        tiger_image_map[tid].append(row[1])
    print(f"  -> {len(all_filenames)} images across {len(tiger_image_map)} tiger IDs")

    # --- Build habitat grid ---
    print("\n[2/9] Building 2 km² ecological habitat grid...")
    rng_main = np.random.default_rng(RANDOM_SEED)
    grid = HabitatGrid(rng_main)
    n_cells = len(grid.cells)
    in_reserve = sum(1 for c in grid.cells.values() if c["zone"] in ("core_forest","buffer"))
    print(f"  -> {n_cells} total grid cells, {in_reserve} within reserve")

    # --- Build camera network ---
    print("\n[3/9] Building non-uniform camera network (311 cameras)...")
    network = CameraNetwork(grid, n_cameras=N_CAMERAS_DEFAULT,
                            rng=rng_main, seed_id=RANDOM_SEED)
    zone_counts = defaultdict(int)
    for c in network.cameras:
        zone_counts[c["zone"]] += 1
    print(f"  -> {len(network.cameras)} cameras placed")
    for z, n in zone_counts.items():
        print(f"     {z}: {n}")

    # --- Build tiger population ---
    print(f"\n[4/9] Building tiger population ({N_TIGERS_DEFAULT} individuals)...")
    # Use real tiger IDs from dataset where possible
    real_tiger_ids = sorted(tiger_image_map.keys())[:N_TIGERS_DEFAULT]
    if len(real_tiger_ids) < N_TIGERS_DEFAULT:
        extra = list(range(5000, 5000 + N_TIGERS_DEFAULT - len(real_tiger_ids)))
        real_tiger_ids = real_tiger_ids + extra

    # Distribute tigers across distinct Pench ranges by realistic carrying capacity
    RANGE_ALLOCATION = [
        ("East Pench", 16),
        ("West Pench", 14),
        ("Chorbahuli", 14),
        ("Devalapar", 12),
        ("Saleghat", 12),
        ("Paoni Buffer", 9),
        ("Nagalwadi Buffer", 8),
        ("Sillari Buffer Sector", 8),
        ("West Buffer", 5),
        ("North Buffer", 5),
        ("NH-44 Corridor", 4),
    ]
    assigned_ranges = []
    for rname, count in RANGE_ALLOCATION:
        assigned_ranges.extend([rname] * count)
    while len(assigned_ranges) < len(real_tiger_ids):
        assigned_ranges.append("East Pench")
    rng_main.shuffle(assigned_ranges)

    tigers = []
    for i, tid in enumerate(real_tiger_ids):
        t = TigerAgent(tid, grid, assigned_range=assigned_ranges[i], rng=rng_main)
        tigers.append(t)

    # Assign cubs to some adult females
    adult_females = [t for t in tigers if t.sex == "Female" and t.life_stage in ("adult","young_adult")]
    cub_tigers    = [t for t in tigers if t.life_stage == "cub"]
    for cub in cub_tigers:
        if adult_females:
            mother = adult_females[int(rng_main.integers(0, len(adult_females)))]
            cub.mother_id = mother.tiger_id
            cub.centroid  = (mother.centroid[0] + float(rng_main.uniform(-0.005, 0.005)),
                             mother.centroid[1] + float(rng_main.uniform(-0.005, 0.005)))
            mother.cub_ids.append(cub.tiger_id)

    sex_counts = defaultdict(int)
    stage_counts = defaultdict(int)
    for t in tigers:
        sex_counts[t.sex] += 1
        stage_counts[t.life_stage] += 1
    print(f"  -> Males: {sex_counts['Male']}, Females: {sex_counts['Female']}")
    for stage, n in stage_counts.items():
        print(f"     {stage}: {n}")

    # --- Generate social events ---
    print("\n[5/9] Generating social & biological events (mating, conflicts, dispersal)...")
    social_events = generate_social_events(tigers, rng_main)
    ev_types = defaultdict(int)
    for se in social_events:
        ev_types[se["type"]] += 1
    print(f"  -> {len(social_events)} social events generated")
    for t, n in ev_types.items():
        print(f"     {t}: {n}")

    social_events_by_tiger = defaultdict(list)
    for se in social_events:
        social_events_by_tiger[se["tiger_id"]].append(se)

    # --- Simulate trajectories ---
    print(f"\n[6/9] Simulating continuous hidden trajectories...", flush=True)
    print(f"  (1 trajectory per tiger × {(SIM_END-SIM_START).days} days × {24//SIM_STEP_HOURS} steps/day)", flush=True)
    trajectories = {}
    for i, tiger in enumerate(tigers):
        traj = simulate_trajectory(tiger, grid, social_events_by_tiger[tiger.tiger_id], rng_main)
        trajectories[tiger.tiger_id] = traj
        if (i + 1) % 15 == 0 or (i + 1) == len(tigers):
            print(f"  -> {i+1}/{len(tigers)} trajectories done", flush=True)
    total_steps = sum(len(t) for t in trajectories.values())
    print(f"  -> {total_steps:,} hidden trajectory steps generated", flush=True)

    # --- Sample camera sightings ---
    print("\n[7/9] Sampling camera trap events from trajectories...")
    all_events = []
    for tiger in tigers:
        traj = trajectories[tiger.tiger_id]
        fnames = tiger_image_map.get(tiger.tiger_id, all_filenames[:20])
        events = sample_camera_events(tiger, traj, network, rng_main, fnames)
        all_events.extend(events)

    print(f"  -> {len(all_events):,} camera trap events before anomaly labeling")
    zone_dist = defaultdict(int)
    for e in all_events:
        zone_dist[e["zone"]] += 1
    for z, n in zone_dist.items():
        print(f"     {z}: {n}")

    # --- Label anomalies ---
    print("\n[8/9] Labeling anomalies (20+ types, per-tiger baselines)...")
    all_events = label_anomalies(all_events, tigers, network, social_events, rng_main)
    anom_dist = defaultdict(int)
    for e in all_events:
        anom_dist[e["anomaly_type"]] += 1
    print(f"  -> Anomaly distribution:")
    for atype, n in sorted(anom_dist.items(), key=lambda x: -x[1]):
        pct = n / max(1,len(all_events)) * 100
        print(f"     {atype}: {n} ({pct:.1f}%)")

    # --- Territory shift detection ---
    print("\n  Detecting territory shifts...")
    shifts = detect_territory_shifts(all_events, tigers)
    n_shifts = sum(1 for s in shifts.values() if s["territory_shift_detected"])
    print(f"  -> {n_shifts} tigers with detected territory shifts")

    # --- Build ground truth ---
    print("\n[9/9] Building hidden ground truth layer (not exported to frontend)...")
    gt_tigers = tigers[:min(20, len(tigers))]
    ground_truth = build_ground_truth(gt_tigers, trajectories, all_events, social_events)
    print(f"  -> {len(ground_truth):,} ground truth records (first 20 tigers)")

    # --- Compute last_seen per tiger ---
    last_seen = {}
    for e in all_events:
        tid = str(e["tiger_id"])
        if tid not in last_seen or e["timestamp"] > last_seen[tid]["timestamp"]:
            last_seen[tid] = {
                "tiger_id":                 e["tiger_id"],
                "latitude":                 e["latitude"],
                "longitude":                e["longitude"],
                "timestamp":                e["timestamp"],
                "station_id":               e["camera_id"],
                "camera_id":                e["camera_id"],
                "zone_type":                e["zone"],
                "alert_level":              e["alert_level"],
                "range":                    e["range"],
                "nearest_village":          e["nearest_village"],
                "nearest_village_dist_km":  e["nearest_village_dist_km"],
                "anomaly_type":             e["anomaly_type"],
                "movement_state":           e["movement_state"],
                "behavioral_state":         e["behavioral_state"],
            }

    # --- Tiger territories for bundle (strictly aligned with simulated sightings) ---
    territories = {}
    for tiger in tigers:
        tiger_events = [e for e in all_events if e["tiger_id"] == tiger.tiger_id]
        if tiger_events:
            event_lats = [e["latitude"] for e in tiger_events]
            event_lons = [e["longitude"] for e in tiger_events]
            c_lat = float(np.mean(event_lats))
            c_lon = float(np.mean(event_lons))
            dists = [dist_km(lat, lon, c_lat, c_lon) for lat, lon in zip(event_lats, event_lons)]
            calc_radius = float(np.percentile(dists, 92))
            rad_km = round(max(2.2, min(5.5, calc_radius * 1.15)), 2)
            hr_km2 = round(math.pi * (rad_km ** 2), 1)
        else:
            c_lat = tiger.centroid[0]
            c_lon = tiger.centroid[1]
            rad_km = tiger.territory_radius_km
            hr_km2 = tiger.home_range_km2

        territories[str(tiger.tiger_id)] = {
            "tiger_id":               int(tiger.tiger_id),
            "sex":                    tiger.sex,
            "age_years":              tiger.age_years,
            "life_stage":             tiger.life_stage,
            "body_condition":         tiger.body_condition,
            "territorial_status":     tiger.territorial_status,
            "dispersal_status":       tiger.dispersal_status,
            "primary_range":          range_for_point(c_lat, c_lon),
            "centroid_lat":           round(c_lat, 6),
            "centroid_lon":           round(c_lon, 6),
            "home_range_km2":         hr_km2,
            "territory_radius_km":    rad_km,
            "core_area_fraction":     round(tiger.core_area_fraction, 2),
            "core_radius_km":         round(rad_km * math.sqrt(tiger.core_area_fraction), 2),
            "min_village_dist_km":    round(nearest_village(c_lat, c_lon)[1], 2),
            "habitat_preference":     tiger.habitat_preference,
            "water_preference":       round(tiger.water_preference, 2),
            "camera_detectability":   round(tiger.camera_detectability, 2),
            "human_avoidance":        round(tiger.human_avoidance, 2),
            "territory_shift_info":   shifts.get(tiger.tiger_id, {}),
        }

    # --- Alert summary ---
    alert_summary = {"SAFE": 0, "CAUTION": 0, "CRITICAL": 0}
    for ls in last_seen.values():
        alert_summary[ls["alert_level"]] = alert_summary.get(ls["alert_level"], 0) + 1

    # --- Sort events chronologically ---
    all_events.sort(key=lambda x: x["timestamp"])

    # --- Save sightings CSV ---
    df_meta = pd.DataFrame(all_events)
    df_meta.to_csv(os.path.join(OUTPUT_DIR, "pench_tiger_metadata_train.csv"), index=False)
    print(f"\n  -> Sightings CSV: {len(df_meta)} rows")

    # --- Save camera stations CSV ---
    df_cameras = pd.DataFrame([{
        "station_id":         c["camera_id"],
        "camera_id":          c["camera_id"],
        "range":              c["range"],
        "zone_type":          c["zone"],
        "latitude":           c["latitude"],
        "longitude":          c["longitude"],
        "habitat":            c["habitat"],
        "trail_type":         c["trail_type"],
        "camera_type":        c["camera_type"],
        "nearest_village":    c["nearest_village"],
        "nearest_village_km": c["nearest_village_km"],
        "nearest_water_km":   c["nearest_water_km"],
        "nearest_road_km":    c["nearest_road_km"],
        "trap_nights":        round(c["trap_nights"], 1),
        "total_detections":   c["total_detections"],
        "n_failures":         len(c["failure_log"]),
    } for c in network.cameras])
    df_cameras.to_csv(os.path.join(OUTPUT_DIR, "pench_camera_stations.csv"), index=False)

    # --- Save territories JSON ---
    with open(os.path.join(OUTPUT_DIR, "pench_tiger_territories.json"), "w") as f:
        json.dump(territories, f, indent=2, default=str)

    # --- Save villages JSON ---
    with open(os.path.join(OUTPUT_DIR, "pench_villages.json"), "w") as f:
        json.dump(VILLAGES, f, indent=2, default=str)

    # --- Save ground truth (separate) ---
    gt_path = os.path.join(OUTPUT_DIR, "pench_ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(ground_truth[:50000], f, default=str)   # cap for file size
    print(f"  -> Ground truth: {min(len(ground_truth),50000):,} records (NEVER sent to frontend)")

    # --- Save social events ---
    with open(os.path.join(OUTPUT_DIR, "pench_social_events.json"), "w") as f:
        json.dump(social_events, f, indent=2, default=str)

    # --- Save water sources ---
    with open(os.path.join(OUTPUT_DIR, "pench_water_sources.json"), "w") as f:
        json.dump(WATER_SOURCES, f, indent=2, default=str)

    # --- Save territory shifts ---
    shift_out = {str(k): v for k, v in shifts.items()}
    with open(os.path.join(OUTPUT_DIR, "pench_territory_shifts.json"), "w") as f:
        json.dump(shift_out, f, indent=2, default=str)

    # --- Train/Val/Test split metadata ---
    all_seeds = list(range(N_SEEDS))
    train_s, val_s, test_s = train_val_test_split(all_seeds)
    split_meta = {
        "description": "Simulation seeds split for ML training. Never split individual sightings.",
        "train_seeds": train_s,
        "val_seeds":   val_s,
        "test_seeds":  test_s,
        "note": "This run uses seed 0. Run with different RANDOM_SEED values for additional worlds."
    }
    with open(os.path.join(OUTPUT_DIR, "pench_train_test_split.json"), "w") as f:
        json.dump(split_meta, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("DONE! All outputs in:", OUTPUT_DIR)
    print("=" * 70)
    print(f"  Sightings CSV:       pench_tiger_metadata_train.csv  ({len(df_meta)} rows)")
    print(f"  Camera stations:     pench_camera_stations.csv        ({len(df_cameras)} cameras)")
    print(f"  Territories:         pench_tiger_territories.json     ({len(territories)} tigers)")
    print(f"  Ground truth:        pench_ground_truth.json          (ML labels only)")
    print(f"  Social events:       pench_social_events.json         ({len(social_events)} events)")
    print(f"  Water sources:       pench_water_sources.json         ({len(WATER_SOURCES)} sources)")
    print(f"  Territory shifts:    pench_territory_shifts.json      ({n_shifts} shift events)")
    print(f"  Alert summary:       SAFE={alert_summary['SAFE']}  CAUTION={alert_summary['CAUTION']}  CRITICAL={alert_summary['CRITICAL']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
