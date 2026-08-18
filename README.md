# TYGRIS: Pench Tiger Reserve Synthetic Dataset & Monitoring Dashboard

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-green.svg)](https://leafletjs.com/)
[![Dataset](https://img.shields.io/badge/Dataset-ATRW%20Amur%20Tigers-orange.svg)](https://www.kaggle.com/)
[![License](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)

An ecological synthetic dataset generation pipeline and high-performance GIS monitoring web application modeled after **Pench Tiger Reserve (Maharashtra/MP)**. Built on top of the **ATRW (Amur Tiger Re-ID in the Wild)** pose and re-identification benchmark dataset.

---

## 📌 Project Overview

TYGRIS integrates deep learning computer vision (tiger Re-ID and 15-point anatomical keypoint pose estimation) with ecological spatial modeling to create a comprehensive wildlife monitoring and early warning system:

1. **Ecological Synthetic Generator (`generate_pench_metadata.py`)**:
   - Simulates continuous correlated random walks across a 2 km² ecological habitat grid.
   - Enforces realistic demographic parameters, territory sizes (15–50 km²), seasonal water/prey drivers, and social encounters (mating, territorial fights, dispersal).
   - Generates realistic camera trap observation records (**20 to 90 sightings per tiger** across 123 grid-spaced stations).
2. **Camera Trap Network (123 Installed Stations)**:
   - Spatially constrained camera trap network ($\ge 1.25$ km minimum separation between adjacent stations).
   - Layer toggle for map-wide visualization, range-specific filtering, and station telemetry inspection.
3. **Tiger-Human Conflict Alert System**:
   - Classifies sightings into real-time threat levels (**🟢 SAFE / Core Forest**, **🟡 CAUTION / Buffer Zone**, **🔴 CRITICAL / Village Boundary**).
4. **Interactive GIS Satellite Dashboard**:
   - Pure HTML5 / CSS3 / Vanilla JavaScript + Leaflet.js dashboard.
   - Dual-tab sidebar (Tigers Directory vs. Camera Network).
   - Orbital multi-capture dispersal ensuring 100% visibility of all sighting markers without overlapping stacks.
   - Interactive dual-handle timeline slider, chronological photo gallery dock, and 15-point skeleton pose viewer.

---

## 📷 Dataset & Photos Setup

Due to file size considerations, image binaries (`.jpg`) inside the dataset folders are excluded via `.gitignore`. **All annotations, Re-ID mappings, and pose keypoint coordinates are included in this repository**.

### Download Image Binaries:
The photos correspond to the **ATRW (Amur Tiger Re-ID in the Wild)** benchmark dataset (CVPR/WACV). You can download them from:
- **Kaggle**: [ATRW Dataset / Amur Tigers Re-ID](https://www.kaggle.com/)
- **Benchmark Source**: Search for ATRW Re-ID Wild Dataset (`reid_list_train.csv`).

### Installation Directory:
1. Extract training photos into:
   ```
   Amur Tigers/train/*.jpg
   ```
2. Extract test photos into:
   ```
   Amur Tigers/test/*.jpg
   ```
*(The repository already contains `reid_list_train.csv`, `reid_list_test.csv`, `reid_keypoints_train.json`, and `reid_keypoints_test.json`).*

---

## 🚀 Quick Start Guide

### 1. Generate Synthetic Pench Metadata
Run the simulation script to generate zone-classified camera stations, realistic tiger trajectories, and sighting records:
```bash
python generate_pench_metadata.py
```
*Outputs generated metadata files into `Pench_Synthetic_Metadata/` (CSV & JSON).*

### 2. Bundle Data for Web Dashboard
Compile metadata, boundaries, sub-regions, and villages into `pench_web_bundle.json`:
```bash
python prepare_web_data.py
```

### 3. Launch Local Dashboard
Start the local HTTP server:
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your web browser.

---

## 🗺️ Key Features & Architecture

### 1. Dual-Tab Explorer Sidebar
- **Tigers Tab (107 Individuals)**:
  - Search by Tiger ID or Range name.
  - Quick filter chips: `All`, `Male`, `Female`, `Alerts`.
  - Individual cards showing sex, primary range, total sighting counts, and latest alert level.
- **Camera Network Tab (123 Stations)**:
  - Real-time station search (e.g. `CAM-0024`, `Saleghat`, `Wadamba`).
  - Filter chips: `All (123)`, `Core`, `Buffer`, `Active Detections`, `CCTV / Solar`.
  - Forest Range dropdown selector.
  - Camera cards displaying zone badges, detection totals, unique tigers identified, and trap-night effort.

### 2. Camera Network Layer & Telemetry Popups
- **1-Click Map Layer Toggle**: Turn on/off all 123 camera stations across Pench via the header checkbox or range dropdown.
- **Color-Coded Station Markers**:
  - 🟢 **Emerald**: Core Forest Wildlife Camera Trap
  - 🟡 **Amber**: Buffer Zone Camera Trap
  - 🟣 **Purple**: NH-44 Wildlife Corridor Camera
- **Rich Telemetry Popups**: Click any camera station to view trap effort, trail type, nearest water/village distances, list of identified tigers, and a scrollable recent capture photo strip.

### 3. 100% Sighting Visibility & Orbital Dispersal
- When a tiger is captured multiple times at the same camera station, sightings are arranged in a clean micro-orbital ring ($R \approx 45\text{m}-80\text{m}$) around the station hub with connecting spoke lines.
- **Zero Hidden Pins**: For a tiger with 30 sightings, **all 30 numbered markers (`#1` to `#30`)** remain distinctly visible, clickable, and hoverable simultaneously.
- **Chronological Trail Polyline**: Dashed trajectory vector connects each sighting sequentially ($1 \rightarrow 2 \rightarrow 3 \rightarrow \dots \rightarrow N$).

### 4. Interactive Sighting Window Timeline Slider
- Dual draggable range thumbs to inspect any chronological window of sightings.
- Preset window buttons: `5`, `10`, `15`, `25`, `All`.
- Toggleable territory home range polygon overlay (~15–50 km² area circle).

### 5. 15-Point AI Skeleton Pose Viewer
- Click **"Inspect Photo & Keypoints"** from any sighting popup or gallery thumbnail.
- Renders anatomical keypoints (nose, eyes, shoulders, elbows, paws, hips, knees, tail root) with toggleable joint lines and coordinates.

---

## 📊 Summary Statistics & Ground Truth

| Metric | Pench Simulation Specification |
| :--- | :--- |
| **Total Tiger Population** | 107 identified individuals |
| **Installed Camera Trap Stations** | 123 active stations (86 Core, 37 Buffer) |
| **Min Distance Between Cameras** | $\ge 1.25$ km grid spacing |
| **Total Sighting Records** | ~5,549 observations |
| **Sightings per Individual** | 20 to 90 sightings |
| **Monitored Perimeter Villages** | 44 border villages |
| **Sub-Regions / Ranges** | 11 ranges (East Pench, West Pench, Saleghat, Chorbahuli, Devalapar, Paoni, Nagalwadi, Sillari, etc.) |
| **Web Data Bundle Size** | ~7.1 MB (optimized JSON) |

---

## 📄 Repository Structure

```
├── Amur Tigers/
│   ├── reid_list_train.csv         # Train Re-ID labels
│   ├── reid_list_test.csv          # Test Re-ID labels
│   ├── reid_keypoints_train.json   # 15-point pose keypoints
│   ├── reid_keypoints_test.json
│   ├── train/                      # [Place training .jpg images here]
│   └── test/                       # [Place test .jpg images here]
├── Pench_Synthetic_Metadata/       # Generated CSVs & JSONs
│   ├── pench_tiger_metadata_train.csv
│   ├── pench_camera_stations.csv
│   ├── pench_tiger_territories.json
│   ├── pench_villages.json
│   ├── pench_water_sources.json
│   └── pench_social_events.json
├── app.js                          # Core Leaflet map logic & UI state
├── index.html                      # Modern responsive dashboard markup
├── styles.css                      # Glassmorphism dark aesthetic styling
├── generate_pench_metadata.py      # Scientific ecological data generator
├── prepare_web_data.py             # JSON data compiler & bundler
├── pench_web_bundle.json           # Compact production bundle for frontend
├── server.py                       # Local CORS-enabled HTTP server
└── README.md                       # Documentation
```
