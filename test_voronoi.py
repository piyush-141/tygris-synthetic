import json
from shapely.geometry import Polygon
from scipy.spatial import Voronoi
import numpy as np

buffer_boundary = [
    [21.765, 79.120], [21.775, 79.200], [21.770, 79.295],
    [21.750, 79.350], [21.720, 79.395], [21.670, 79.400],
    [21.610, 79.395], [21.560, 79.370], [21.520, 79.310],
    [21.495, 79.250], [21.500, 79.185], [21.520, 79.140],
    [21.555, 79.110], [21.600, 79.100], [21.670, 79.100],
    [21.730, 79.105],
]

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

buffer_poly = Polygon(buffer_boundary)
centers = np.array([reg["center"] for reg in sub_regions])

# Bounding dummy points
dummy_points = np.array([
    [22.5, 80.5], [20.5, 80.5], [22.5, 78.5], [20.5, 78.5],
    [23.0, 79.2], [20.0, 79.2], [21.6, 81.0], [21.6, 77.0]
])
all_pts = np.vstack([centers, dummy_points])

vor = Voronoi(all_pts)

for i, reg in enumerate(sub_regions):
    region_idx = vor.point_region[i]
    region_vertices = vor.regions[region_idx]
    if -1 in region_vertices:
        print(f"Region {reg['id']} has an open vertex!")
        continue
    vor_poly = Polygon([vor.vertices[v] for v in region_vertices])
    
    # ensure validity
    if not vor_poly.is_valid:
        vor_poly = vor_poly.buffer(0)
    
    clipped_poly = vor_poly.intersection(buffer_poly)
    if clipped_poly.is_empty:
        print(f"Region {reg['id']} is empty!")
    else:
        if clipped_poly.geom_type == 'MultiPolygon':
            clipped_poly = max(clipped_poly.geoms, key=lambda x: x.area)
        
        coords = list(clipped_poly.exterior.coords)
        reg["polygon"] = [[round(p[0], 5), round(p[1], 5)] for p in coords]

print(json.dumps(sub_regions, indent=2))
