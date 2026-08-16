# TYGRIS: Pench Tiger Reserve Synthetic Dataset & Monitoring Dashboard

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Leaflet](https://img.shields.io/badge/Leaflet-1.9.4-green.svg)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

An ecological synthetic dataset generation pipeline and lightweight satellite monitoring web application modeled after **Pench Tiger Reserve (Maharashtra/MP)**. Built on top of the **ATRW (Amur Tiger Re-ID in the Wild)** pose & re-identification benchmark dataset.

---

## 📌 Project Overview

This repository provides:
1. **Ecologically Realistic Synthetic Generator**: Maps tiger Re-ID image annotations to GPS camera trap stations across core forest, buffer, and village boundary zones.
2. **Tiger-Human Conflict Alert System**: Classifies tiger sightings into real-time threat levels (**🟢 SAFE**, **🟡 CAUTION**, **🔴 CRITICAL**).
3. **Interactive Satellite Dashboard**: Pure HTML/CSS/JS Leaflet dashboard with sub-region dotted boundaries, village markers, and a 15-point anatomical pose keypoint viewer.

---

## 📷 Dataset & Photos Setup

Due to GitHub file size limits, image binaries (`.jpg`) inside the dataset folders are excluded via `.gitignore`. However, **all annotations, Re-ID lists, and pose keypoints are fully included** in this repository.

### Where to Find & Download the Tiger Photos
The photos correspond to the **ATRW (Amur Tiger Re-ID in the Wild)** dataset (CVPR WACV benchmark). You can obtain the image files from:
- **Kaggle**: [ATRW Dataset / Amur Tigers Re-ID](https://www.kaggle.com/datasets)
- **Official Benchmark Repo**: Search for ATRW Re-ID Wild Dataset (`reid_list_train.csv`).

### Installation of Image Files:
1. Download the ATRW image dataset.
2. Extract the training photos into:
   ```
   Amur Tigers/train/*.jpg
   ```
3. Extract the test photos into:
   ```
   Amur Tigers/test/*.jpg
   ```
*(The repository already contains `reid_list_train.csv`, `reid_list_test.csv`, `reid_keypoints_train.json`, and `reid_keypoints_test.json`).*

---

## 🚀 Quick Start Guide

### 1. Generate Synthetic Pench Metadata
Run the simulation script to generate zone-classified camera stations, realistic tiger territories (centroids ≥3 km from villages), and crepuscular sighting timestamps:
```bash
python generate_pench_metadata.py
```
*Outputs generated metadata files into `Pench_Synthetic_Metadata/`.*

### 2. Bundle Data for Web Frontend
Combine metadata, boundaries, and villages into `pench_web_bundle.json`:
```bash
python prepare_web_data.py
```

### 3. Launch Local Dashboard
Start the Python HTTP dev server:
```bash
python server.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 🗺️ Key Dashboard Features

- **Zone Boundaries**: Core Forest (439 km²) & Buffer Zone (301 km²) polygon overlays.
- **11 Sub-Regions**: Verified ranges (East Pench, Devalapar, Chorbahuli, Saleghat, Paoni, Nagalwadi, Sillari, NH-44 Corridor, etc.) with dotted boundary lines and centered labels.
- **Village Markers**: 44 perimeter village location markers.
- **Alert Levels**:
  - 🟢 **SAFE**: Sighted inside Core Forest.
  - 🟡 **CAUTION**: Sighted in Buffer Zone.
  - 🔴 **CRITICAL**: Sighted at boundary cameras near village perimeters.
- **15-Point Skeleton Pose Viewer**: Inspect tiger camera trap images with anatomical joint skeleton overlays.

---

## 📄 Repository Structure

```
├── Amur Tigers/
│   ├── reid_list_train.csv         # Train Re-ID labels
│   ├── reid_list_test.csv          # Test Re-ID labels
│   ├── reid_keypoints_train.json   # 15-point pose keypoints
│   ├── reid_keypoints_test.json
│   ├── train/                      # [Place .jpg images here]
│   └── test/                       # [Place .jpg images here]
├── Pench_Synthetic_Metadata/       # Generated CSV & JSON data
├── app.js                          # Leaflet map logic & UI state
├── index.html                      # App markup & controls
├── styles.css                      # Modern dark dashboard styling
├── generate_pench_metadata.py      # Synthetic data generator
├── prepare_web_data.py             # JSON bundler for frontend
└── server.py                       # Python HTTP server
```
