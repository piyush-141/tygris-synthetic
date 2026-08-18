/**
 * Pench Tiger Reserve - Zone Alert Monitoring Dashboard
 * app.js v3 — Zone boundaries, alert-level pins, village markers, and Camera Network View
 */

// Global State
let state = {
  data: null,
  map: null,
  layers: {
    satellite: null,
    labels: null,
    dark: null,
    zoneBoundaries: null,
    subRegions: null,
    villageMarkers: null,
    areaCameras: null,
    tigersLastSeen: null,
    singleTigerTrail: null,
    singleTigerTerritory: null
  },
  tigersLastSeenMap: {},
  tigerSightingsMap: {},
  cameraStationsMap: {},
  stationSightingsMap: {},
  stationMarkersMap: {},
  selectedTigerId: null,
  selectedStationId: null,
  selectedSightingIndex: 0,
  activeSightingsList: [],
  selectedAreaRange: "NONE",
  filterSex: "all",
  activeTab: "tigers",
  filterCamType: "all",
  filterCamRange: "ALL",
  showKeypoints: true,
  showZones: true,
  showSubRegions: true,
  showVillages: false,
  // Timeline state
  timeline: {
    startIdx: 0,   // sighting index (inclusive)
    endIdx: 14,    // sighting index (inclusive)
    showTerritory: true
  }
};

const ALERT_COLORS = {
  SAFE: "#22c55e",
  CAUTION: "#eab308",
  CRITICAL: "#ef4444"
};

// ---------------------------------------------------------------------------
// 1. INITIALIZATION
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  setupEventListeners();
  await loadData();
});

async function loadData() {
  try {
    const response = await fetch("pench_web_bundle.json");
    if (!response.ok) throw new Error("Failed to load pench_web_bundle.json");
    state.data = await response.json();
    
    processTigerSightings();
    processCameraStations();
    populateAreaCamDropdown();
    renderTigerDirectory();
    renderCameraDirectory();
    renderTigersLastSeenOnMap();
    renderZoneBoundaries();
    renderSubRegions();
    updateAlertPanel();

    const totalTigers = Object.keys(state.tigersLastSeenMap).length;
    const totalCams = state.data.stations ? state.data.stations.length : 0;
    
    const countTigerEl = document.getElementById("total-tiger-count");
    if (countTigerEl) countTigerEl.textContent = totalTigers;
    const countCamEl = document.getElementById("total-cam-count");
    if (countCamEl) countCamEl.textContent = totalCams;

    document.getElementById("view-mode-text").innerHTML = `MAP MODE: <strong>TIGERS LAST SEEN (${totalTigers})</strong>`;

    console.log("Pench Tiger Zone Alert Dashboard ready!", {
      totalTigers,
      totalCams,
      totalSightings: state.data.sightings.length,
      alertSummary: state.data.alert_summary
    });
  } catch (err) {
    console.error("Error loading bundle:", err);
    alert("Could not load dataset bundle. Make sure the server is running.");
  }
}

function processTigerSightings() {
  state.tigerSightingsMap = {};
  state.tigersLastSeenMap = {};

  state.data.sightings.forEach(s => {
    const tid = s.tiger_id;
    if (!state.tigerSightingsMap[tid]) {
      state.tigerSightingsMap[tid] = [];
    }
    state.tigerSightingsMap[tid].push(s);
  });

  // Use pre-computed last_seen from bundle (has alert_level)
  if (state.data.last_seen) {
    state.tigersLastSeenMap = state.data.last_seen;
  } else {
    for (const [tid, list] of Object.entries(state.tigerSightingsMap)) {
      list.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      state.tigersLastSeenMap[tid] = list[list.length - 1];
    }
  }

  // Sort sightings chronologically
  for (const list of Object.values(state.tigerSightingsMap)) {
    list.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }
}

function processCameraStations() {
  state.cameraStationsMap = {};
  state.stationSightingsMap = {};

  // Group sightings by station_id
  state.data.sightings.forEach(s => {
    const stId = s.station_id || s.camera_id;
    if (!stId) return;
    if (!state.stationSightingsMap[stId]) {
      state.stationSightingsMap[stId] = [];
    }
    state.stationSightingsMap[stId].push(s);
  });

  // Sort sightings chronologically for each station (newest first for recent photos)
  for (const list of Object.values(state.stationSightingsMap)) {
    list.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  }

  // Index stations and calculate aggregated stats
  state.data.stations.forEach(st => {
    const stId = st.station_id || st.camera_id;
    const sightings = state.stationSightingsMap[stId] || [];
    const uniqueTigers = Array.from(new Set(sightings.map(s => s.tiger_id)));

    state.cameraStationsMap[stId] = {
      ...st,
      station_id: stId,
      sightings,
      sighting_count: sightings.length,
      unique_tigers: uniqueTigers,
      recent_sightings: sightings.slice(0, 8)
    };
  });
}

function populateAreaCamDropdown() {
  const select = document.getElementById("select-area-cams");
  const sidebarSelect = document.getElementById("cam-sidebar-range-select");
  
  if (!select) return;

  const totalCams = state.data.stations ? state.data.stations.length : 0;
  const allOpt = select.querySelector('option[value="ALL"]');
  if (allOpt) allOpt.textContent = `All Stations (${totalCams})`;
  const chipAll = document.querySelector('[data-cam-filter="all"]');
  if (chipAll) chipAll.textContent = `All (${totalCams})`;

  // Preserve the first two options: NONE (Hidden) and ALL (All Stations)
  while (select.children.length > 2) {
    select.removeChild(select.lastChild);
  }
  if (sidebarSelect) {
    while (sidebarSelect.children.length > 1) {
      sidebarSelect.removeChild(sidebarSelect.lastChild);
    }
  }

  const ranges = {};
  state.data.stations.forEach(st => {
    const r = st.range || "Unknown";
    if (!ranges[r]) ranges[r] = 0;
    ranges[r]++;
  });

  const sortedRanges = Object.keys(ranges).sort();

  sortedRanges.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = `${name} (${ranges[name]} cams)`;
    select.appendChild(opt);

    if (sidebarSelect) {
      const sideOpt = document.createElement("option");
      sideOpt.value = name;
      sideOpt.textContent = `${name} (${ranges[name]})`;
      sidebarSelect.appendChild(sideOpt);
    }
  });
}

function updateAlertPanel() {
  let safe = 0, caution = 0, critical = 0;
  for (const ls of Object.values(state.tigersLastSeenMap)) {
    if (ls.alert_level === "SAFE") safe++;
    else if (ls.alert_level === "CAUTION") caution++;
    else if (ls.alert_level === "CRITICAL") critical++;
  }
  document.getElementById("count-safe").textContent = safe;
  document.getElementById("count-caution").textContent = caution;
  document.getElementById("count-critical").textContent = critical;
}

// ---------------------------------------------------------------------------
// 2. LEAFLET MAP SETUP
// ---------------------------------------------------------------------------
function initMap() {
  state.map = L.map("map", {
    center: [21.630, 79.250],
    zoom: 12,
    zoomControl: false
  });

  L.control.zoom({ position: "topright" }).addTo(state.map);

  state.layers.satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18, attribution: "Tiles &copy; Esri" }
  );

  state.layers.labels = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18 }
  );

  state.layers.dark = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { maxZoom: 19, attribution: "&copy; CartoDB" }
  );

  state.layers.satellite.addTo(state.map);
  state.layers.labels.addTo(state.map);

  state.layers.zoneBoundaries = L.layerGroup().addTo(state.map);
  state.layers.subRegions = L.layerGroup().addTo(state.map);
  state.layers.villageMarkers = L.layerGroup();
  state.layers.areaCameras = L.layerGroup().addTo(state.map);
  state.layers.tigersLastSeen = L.layerGroup().addTo(state.map);
  state.layers.singleTigerTrail = L.layerGroup().addTo(state.map);
  state.layers.singleTigerTerritory = L.layerGroup().addTo(state.map);
}

// ---------------------------------------------------------------------------
// 3. ZONE BOUNDARIES (Core Forest & Buffer Zone polygons)
// ---------------------------------------------------------------------------
function renderZoneBoundaries() {
  state.layers.zoneBoundaries.clearLayers();

  if (!state.showZones || !state.data.zone_boundaries) return;

  const core = state.data.zone_boundaries.core_forest;
  const buffer = state.data.zone_boundaries.buffer_zone;

  // Buffer zone (outer ring) - dashed yellow
  if (buffer) {
    const bufferPoly = L.polygon(buffer, {
      color: "#eab308",
      weight: 2,
      dashArray: "8, 6",
      fillColor: "#eab308",
      fillOpacity: 0.04
    });
    bufferPoly.bindTooltip("<strong>Buffer Zone</strong><br>301 km² — Restricted human activity", { sticky: true });
    state.layers.zoneBoundaries.addLayer(bufferPoly);
  }

  // Core forest (inner) - solid green
  if (core) {
    const corePoly = L.polygon(core, {
      color: "#22c55e",
      weight: 2.5,
      fillColor: "#22c55e",
      fillOpacity: 0.06
    });
    corePoly.bindTooltip("<strong>Core Forest</strong><br>439 km² — Primary tiger habitat", { sticky: true });
    state.layers.zoneBoundaries.addLayer(corePoly);
  }
}

// ---------------------------------------------------------------------------
// 3b. SUB-REGIONS (11 Dotted Regional Boundaries & Centroid Labels)
// ---------------------------------------------------------------------------
function renderSubRegions() {
  state.layers.subRegions.clearLayers();

  if (!state.showSubRegions || !state.data.sub_regions) return;

  state.data.sub_regions.forEach(reg => {
    // Dotted boundary polygon for region
    const poly = L.polygon(reg.polygon, {
      color: reg.color || "#10b981",
      weight: 1.8,
      dashArray: "4, 6",
      fillColor: reg.color || "#10b981",
      fillOpacity: 0.05
    });

    poly.bindTooltip(
      `<strong>${reg.name}</strong><br>Zone: ${reg.type}`,
      { sticky: true }
    );
    state.layers.subRegions.addLayer(poly);

    // Centroid Name Badge
    const icon = L.divIcon({
      className: "custom-subregion-icon",
      html: `<div class="subregion-label-pin" style="border-color:${reg.color}66;"><i class="fa-solid fa-location-crosshairs" style="color:${reg.color}"></i> ${reg.name}</div>`,
      iconSize: [130, 20],
      iconAnchor: [65, 10]
    });

    const labelMarker = L.marker(reg.center, { icon });
    state.layers.subRegions.addLayer(labelMarker);
  });
}

// ---------------------------------------------------------------------------
// 4. VILLAGE MARKERS
// ---------------------------------------------------------------------------
function renderVillageMarkers() {
  state.layers.villageMarkers.clearLayers();

  if (!state.showVillages || !state.data.villages) return;

  state.data.villages.forEach(v => {
    const icon = L.divIcon({
      className: "custom-village-icon",
      html: `<div class="village-marker-pin"><i class="fa-solid fa-house-chimney"></i> ${v.name}</div>`,
      iconSize: [80, 18],
      iconAnchor: [40, 9]
    });

    const marker = L.marker([v.lat, v.lon], { icon });
    marker.bindTooltip(
      `<strong>${v.name}</strong><br>Population: ~${v.population}`,
      { sticky: true }
    );
    state.layers.villageMarkers.addLayer(marker);
  });
}

// ---------------------------------------------------------------------------
// 5. TIGERS LAST SEEN - ALERT-COLORED PINS
// ---------------------------------------------------------------------------
function renderTigersLastSeenOnMap() {
  state.layers.singleTigerTrail.clearLayers();
  state.layers.singleTigerTerritory.clearLayers();
  state.layers.tigersLastSeen.clearLayers();

  const tigerIds = Object.keys(state.tigersLastSeenMap);

  tigerIds.forEach(tid => {
    const s = state.tigersLastSeenMap[tid];
    const tInfo = state.data.territories[tid];
    const alertLevel = s.alert_level || "SAFE";
    const pinClass = alertLevel === "CRITICAL" ? "pin-critical" : alertLevel === "CAUTION" ? "pin-caution" : "pin-safe";

    const customIcon = L.divIcon({
      className: "custom-tiger-icon",
      html: `<div class="tiger-lastseen-pin ${pinClass}">${tid}</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const marker = L.marker([s.latitude, s.longitude], { icon: customIcon });

    // Tooltip
    const alertEmoji = alertLevel === "CRITICAL" ? "🔴" : alertLevel === "CAUTION" ? "🟡" : "🟢";
    marker.bindTooltip(
      `<strong>Tiger #${tid} (${tInfo?.sex || 'Unknown'})</strong><br>` +
      `${alertEmoji} ${alertLevel} — ${s.zone_type}<br>` +
      `<span style="color:#94a3b8;font-size:10px">Last Seen: ${s.timestamp}</span>`,
      { sticky: true }
    );

    // Popup
    const alertColor = ALERT_COLORS[alertLevel];
    marker.bindPopup(`
      <div class="popup-card">
        <div class="popup-body">
          <div class="popup-title">Tiger #${tid} (${tInfo?.sex || '?'})</div>
          <div class="popup-alert-tag" style="background:${alertColor}22;color:${alertColor};border:1px solid ${alertColor}55">${alertEmoji} ${alertLevel}</div>
          <div class="popup-sub">${s.range} — ${s.station_id}</div>
          <div class="popup-meta">
            <span><i class="fa-regular fa-clock"></i> ${s.timestamp}</span>
            <span><i class="fa-solid fa-camera"></i> ${state.tigerSightingsMap[tid]?.length || 0} total sightings</span>
            ${s.nearest_village ? `<span><i class="fa-solid fa-house"></i> Near: ${s.nearest_village} (${s.nearest_village_dist_km} km)</span>` : ''}
          </div>
          <button class="btn-popup-action" onclick="selectTiger('${tid}')">
            <i class="fa-solid fa-route"></i> View Sighting Trail
          </button>
        </div>
      </div>
    `);

    state.layers.tigersLastSeen.addLayer(marker);
  });
}

// ---------------------------------------------------------------------------
// TIMELINE HELPERS
// ---------------------------------------------------------------------------

/**
 * Re-renders the sighting trail and territory based on the current
 * state.timeline.startIdx / endIdx window.
 */
function renderFilteredTrail() {
  const tigerId = state.selectedTigerId;
  if (!tigerId) return;

  const allSightings = state.tigerSightingsMap[tigerId] || [];
  const total = allSightings.length;
  if (total === 0) return;

  const tInfo = state.data.territories[tigerId];

  // Clamp indices to valid range
  const startIdx = Math.max(0, Math.min(state.timeline.startIdx, total - 1));
  const endIdx   = Math.max(startIdx, Math.min(state.timeline.endIdx, total - 1));

  const slice = allSightings.slice(startIdx, endIdx + 1);

  state.layers.singleTigerTrail.clearLayers();
  state.layers.singleTigerTerritory.clearLayers();

  // Territory circle (controlled by checkbox)
  if (state.timeline.showTerritory) {
    let centerLat = tInfo?.centroid_lat;
    let centerLon = tInfo?.centroid_lon;
    let radiusKm = tInfo?.territory_radius_km || 2.4;

    // Center directly on the visible sightings cluster to ensure perfect spatial coverage
    if (slice.length > 0) {
      const avgLat = slice.reduce((sum, s) => sum + s.latitude, 0) / slice.length;
      const avgLon = slice.reduce((sum, s) => sum + s.longitude, 0) / slice.length;
      centerLat = avgLat;
      centerLon = avgLon;

      const maxDistKm = Math.max(...slice.map(s => {
        const dlat = (s.latitude - avgLat) * 111.0;
        const dlon = (s.longitude - avgLon) * 103.0;
        return Math.sqrt(dlat * dlat + dlon * dlon);
      }));
      // Standard territory area 15-20 sq km (radius ~2.2 - 2.6 km)
      radiusKm = Math.max(2.2, Math.max(radiusKm, maxDistKm * 1.15));
    }

    if (centerLat && centerLon) {
      const areaKm2 = (Math.PI * radiusKm * radiusKm).toFixed(1);
      const circle = L.circle([centerLat, centerLon], {
        radius: radiusKm * 1000,
        color: "#f59e0b",
        weight: 1.8,
        dashArray: "6, 8",
        fillColor: "#f59e0b",
        fillOpacity: 0.05
      });
      circle.bindTooltip(`<strong>Tiger #${tigerId} Territory</strong><br>Area: ~${areaKm2} km² (Radius: ${radiusKm.toFixed(2)} km)`, { sticky: true });
      state.layers.singleTigerTerritory.addLayer(circle);
    }
  }

  // Group sightings in slice by station location to disperse multi-sightings at the same station
  const stationMap = new Map();
  slice.forEach((s, idx) => {
    const key = `${s.latitude.toFixed(6)},${s.longitude.toFixed(6)}`;
    if (!stationMap.has(key)) {
      stationMap.set(key, []);
    }
    stationMap.get(key).push({ sighting: s, sliceIdx: idx, globalIdx: startIdx + idx });
  });

  // Calculate distinct display coordinates for each sighting so NO TWO PINS OVERLAP
  const displayCoords = new Array(slice.length);

  stationMap.forEach((items, key) => {
    const [baseLatStr, baseLonStr] = key.split(",");
    const baseLat = parseFloat(baseLatStr);
    const baseLon = parseFloat(baseLonStr);
    const stationId = items[0].sighting.station_id || items[0].sighting.camera_id;

    if (items.length === 1) {
      displayCoords[items[0].sliceIdx] = [baseLat, baseLon];
    } else {
      // Multiple sightings at this station: render central station hub & orbital pins
      const hubIcon = L.divIcon({
        className: "station-hub-icon",
        html: `<div class="station-hub-node" title="Station ${stationId} (${items.length} Captures)"><i class="fa-solid fa-video"></i> <span>${items.length}</span></div>`,
        iconSize: [34, 18],
        iconAnchor: [17, 9]
      });
      const hubMarker = L.marker([baseLat, baseLon], { icon: hubIcon, zIndexOffset: 50 });
      hubMarker.bindTooltip(`<strong>Station: ${stationId}</strong><br>${items.length} captures of Tiger #${tigerId} in this time window`, { sticky: true });
      state.layers.singleTigerTrail.addLayer(hubMarker);

      // Distribute sighting pins in a circular orbit around the camera station
      const count = items.length;
      const radiusKm = 0.045 + Math.min(0.040, count * 0.0035); // 45m to 80m radius

      items.forEach((item, k) => {
        const angle = (2 * Math.PI * k) / count - Math.PI / 2;
        const dLat = (radiusKm * Math.cos(angle)) / 111.0;
        const dLon = (radiusKm * Math.sin(angle)) / (103.0 * Math.cos((baseLat * Math.PI) / 180));
        const dispLat = baseLat + dLat;
        const dispLon = baseLon + dLon;

        displayCoords[item.sliceIdx] = [dispLat, dispLon];

        // Draw spoke filament line connecting central station to individual sighting pin
        const spoke = L.polyline([[baseLat, baseLon], [dispLat, dispLon]], {
          color: "rgba(245, 158, 11, 0.45)",
          weight: 1,
          dashArray: "2, 3"
        });
        state.layers.singleTigerTrail.addLayer(spoke);
      });
    }
  });

  // Trail polyline connecting chronological display coordinates
  if (displayCoords.length > 1) {
    const polyline = L.polyline(displayCoords, {
      color: "#ffffff",
      weight: 1.8,
      dashArray: "5, 7",
      opacity: 0.85
    });
    state.layers.singleTigerTrail.addLayer(polyline);
  }

  // Numbered step markers for EVERY SINGLE SIGHTING
  slice.forEach((s, i) => {
    const globalIdx = startIdx + i;           // sighting number in full set (e.g. 1 to 30)
    const isLatest  = globalIdx === endIdx;
    const isFirst   = globalIdx === startIdx;
    const alertLevel = s.alert_level || "SAFE";
    const alertColor = ALERT_COLORS[alertLevel];
    const coords = displayCoords[i];

    const pinStyle = isLatest
      ? `background:${alertColor};color:#fff;border-color:#fff;box-shadow:0 0 10px ${alertColor};transform:scale(1.25);z-index:900;`
      : isFirst
      ? `background:#10b981;color:#fff;border-color:#fff;`
      : '';

    const customIcon = L.divIcon({
      className: "custom-trail-icon",
      html: `<div class="trail-step-pin" style="${pinStyle}">${globalIdx + 1}</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const marker = L.marker(coords, { icon: customIcon, zIndexOffset: isLatest ? 800 : globalIdx + 10 });
    marker.bindTooltip(
      `<strong>Sighting #${globalIdx + 1} of ${total}</strong><br>` +
      `<span style="color:#f59e0b">Station: ${s.station_id || s.camera_id}</span><br>` +
      `<span style="color:#94a3b8;font-size:10px">${s.timestamp} (${s.zone_type})</span>`,
      { sticky: true }
    );
    marker.bindPopup(createSightingPopupHTML(s, globalIdx + 1, total));
    state.layers.singleTigerTrail.addLayer(marker);
  });

  // Update timeline UI labels
  updateTimelineUI(slice, startIdx, endIdx, total);

  // Fit map to visible slice
  if (displayCoords.length > 0) {
    const bounds = L.latLngBounds(displayCoords);
    state.map.flyToBounds(bounds.pad(0.25), { duration: 0.6 });
  }
}

/** Updates the text labels and fill bar of the timeline widget */
function updateTimelineUI(slice, startIdx, endIdx, total) {
  const fmt = ts => ts ? ts.split(' ')[0] : '—';

  const fromTs = slice.length > 0 ? slice[0].timestamp : '—';
  const toTs   = slice.length > 0 ? slice[slice.length - 1].timestamp : '—';

  document.getElementById('timeline-date-from').textContent = fmt(fromTs);
  document.getElementById('timeline-date-to').textContent   = fmt(toTs);
  document.getElementById('timeline-count-badge').textContent = `${slice.length} / ${total}`;

  const n = slice.length;
  const label = n === total ? 'All sightings' : `Sightings ${startIdx + 1} – ${endIdx + 1}`;
  document.getElementById('timeline-window-label').textContent = label;

  // Update the amber fill bar between the two thumb handles
  const sliderStart = document.getElementById('timeline-start');
  const sliderEnd   = document.getElementById('timeline-end');
  const fill        = document.getElementById('timeline-fill');
  const max = parseInt(sliderEnd.max, 10) || 1;
  const leftPct  = (parseInt(sliderStart.value, 10) / max) * 100;
  const rightPct = (parseInt(sliderEnd.value,   10) / max) * 100;
  fill.style.left  = `${leftPct}%`;
  fill.style.width = `${rightPct - leftPct}%`;
}

/** Initialises the timeline widget for a newly selected tiger */
function initTimeline(tigerId) {
  const sightings = state.tigerSightingsMap[tigerId] || [];
  const total = sightings.length;
  const maxIdx = Math.max(0, total - 1);

  // Default: show ALL sightings by default
  const startIdx = 0;
  state.timeline.startIdx = startIdx;
  state.timeline.endIdx   = maxIdx;

  const sliderStart = document.getElementById('timeline-start');
  const sliderEnd   = document.getElementById('timeline-end');
  sliderStart.max = maxIdx;
  sliderEnd.max   = maxIdx;
  sliderStart.value = startIdx;
  sliderEnd.value   = maxIdx;

  // Set preset active state to "all"
  document.querySelectorAll('.btn-tl-preset').forEach(b => {
    b.classList.toggle('active', b.dataset.n === 'all');
  });

  // Position the widget: above dock when dock is visible
  const widget = document.getElementById('timeline-widget');
  const dock   = document.getElementById('gallery-dock');
  widget.classList.remove('hidden');
  widget.classList.toggle('above-dock', !dock.classList.contains('hidden'));
}

// ---------------------------------------------------------------------------
// 6. INDIVIDUAL TIGER FOCUS VIEW
// ---------------------------------------------------------------------------
window.selectTiger = function(tigerId) {
  state.selectedTigerId = tigerId;
  const tInfo = state.data.territories[tigerId];
  const sightings = state.tigerSightingsMap[tigerId] || [];
  state.activeSightingsList = sightings;

  const lastSeen = state.tigersLastSeenMap[tigerId];
  const alertLevel = lastSeen?.alert_level || "SAFE";

  // Update header
  document.getElementById("view-mode-pill").style.borderColor = ALERT_COLORS[alertLevel];
  document.getElementById("view-mode-text").innerHTML = `FOCUS: <strong>TIGER #${tigerId} (${tInfo?.sex}) — ${alertLevel}</strong>`;

  // Update sidebar banner
  const banner = document.getElementById("active-tiger-banner");
  banner.classList.remove("hidden");
  document.getElementById("active-tiger-name").textContent = `Tiger #${tigerId} (${tInfo?.sex})`;
  document.getElementById("active-tiger-info").textContent = `${tInfo?.primary_range} | ${sightings.length} Captures | ${alertLevel}`;
  document.getElementById("active-tiger-avatar").textContent = `#${tigerId}`;

  document.querySelectorAll(".tiger-card").forEach(c => {
    c.classList.toggle("selected", c.dataset.tigerId == tigerId);
  });

  // Clear map layers
  state.layers.tigersLastSeen.clearLayers();

  // Init timeline slider then render filtered trail
  initTimeline(tigerId);
  renderFilteredTrail();

  // Gallery dock
  renderGalleryDock(sightings, tigerId);

  // Push timeline widget above dock now that dock is shown
  document.getElementById('timeline-widget').classList.add('above-dock');
};

function clearTigerSelection() {
  state.selectedTigerId = null;
  state.activeSightingsList = [];

  const totalTigers = Object.keys(state.tigersLastSeenMap).length;
  document.getElementById("view-mode-pill").style.borderColor = "rgba(245, 158, 11, 0.35)";
  document.getElementById("view-mode-text").innerHTML = `MAP MODE: <strong>TIGERS LAST SEEN (${totalTigers})</strong>`;

  document.getElementById("active-tiger-banner").classList.add("hidden");
  document.getElementById("gallery-dock").classList.add("hidden");
  document.getElementById("timeline-widget").classList.add("hidden");
  document.querySelectorAll(".tiger-card").forEach(c => c.classList.remove("selected"));

  renderTigersLastSeenOnMap();
  state.map.flyTo([21.630, 79.250], 12, { duration: 1.0 });
}

function createSightingPopupHTML(s, stepNum, totalSteps) {
  const alertLevel = s.alert_level || "SAFE";
  const alertColor = ALERT_COLORS[alertLevel];
  const alertEmoji = alertLevel === "CRITICAL" ? "🔴" : alertLevel === "CAUTION" ? "🟡" : "🟢";

  return `
    <div class="popup-card">
      <div class="popup-img-wrap">
        <img src="Amur Tigers/train/${s.filename}" alt="Tiger ${s.tiger_id}" loading="lazy" />
        <span class="popup-tag">SIGHTING #${stepNum} of ${totalSteps}</span>
      </div>
      <div class="popup-body">
        <div class="popup-title">${s.station_id}</div>
        <div class="popup-alert-tag" style="background:${alertColor}22;color:${alertColor}">${alertEmoji} ${alertLevel} — ${s.zone_type}</div>
        <div class="popup-meta">
          <span><i class="fa-regular fa-clock"></i> ${s.timestamp}</span>
          <span><i class="fa-solid fa-temperature-half"></i> ${s.ambient_temp_c} °C • ${s.lighting_condition}</span>
          ${s.nearest_village ? `<span><i class="fa-solid fa-house"></i> Near: ${s.nearest_village}</span>` : ''}
        </div>
        <button class="btn-popup-action" onclick="openPhotoModal('${s.filename}')">
          <i class="fa-solid fa-expand"></i> Inspect Photo & Keypoints
        </button>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 7. CAMERA NETWORK LAYER & CONTROLS (Togglable for All or by Range)
// ---------------------------------------------------------------------------

/**
 * Sets visibility and filter of camera network on map
 * @param {boolean} visible Whether cameras should be shown
 * @param {string} range 'ALL', 'NONE', or specific range name
 * @param {boolean} fitBounds Whether to pan/zoom map to fit camera pins
 */
function setCameraVisibility(visible, range = "ALL", fitBounds = false) {
  const checkbox = document.getElementById("toggle-all-cameras");
  const select = document.getElementById("select-area-cams");

  if (!visible || range === "NONE") {
    state.selectedAreaRange = "NONE";
    if (checkbox) checkbox.checked = false;
    if (select) select.value = "NONE";
    renderCameraStationsOnMap("NONE");
    clearCameraFocus();
  } else {
    state.selectedAreaRange = range;
    if (checkbox) checkbox.checked = true;
    if (select) select.value = range;
    const stations = renderCameraStationsOnMap(range);
    if (fitBounds && stations && stations.length > 0) {
      const bounds = L.latLngBounds(stations.map(st => [st.latitude, st.longitude]));
      state.map.flyToBounds(bounds.pad(0.15), { duration: 0.8 });
    }
  }
}

/**
 * Renders camera markers onto map layer
 */
function renderCameraStationsOnMap(range = "ALL") {
  state.layers.areaCameras.clearLayers();
  state.stationMarkersMap = {};

  const legendCamItem = document.getElementById("legend-cam-item");
  const legendCamCount = document.getElementById("legend-cam-count");

  if (range === "NONE") {
    if (legendCamItem) legendCamItem.style.display = "none";
    return [];
  }

  let stations = state.data.stations || [];
  if (range !== "ALL") {
    stations = stations.filter(st => st.range === range);
  }

  if (legendCamItem) {
    legendCamItem.style.display = "flex";
    if (legendCamCount) legendCamCount.textContent = stations.length;
  }

  stations.forEach(st => {
    const marker = createStationMarker(st);
    state.layers.areaCameras.addLayer(marker);
    state.stationMarkersMap[st.station_id] = marker;
  });

  return stations;
}

/**
 * Creates an interactive Leaflet marker for a camera station
 */
function createStationMarker(st) {
  const fullSt = state.cameraStationsMap[st.station_id] || st;
  const isCore = (fullSt.zone_type || "").toLowerCase().includes("core");
  const isBuffer = (fullSt.zone_type || "").toLowerCase().includes("buffer");
  const isCorridor = (fullSt.zone_type || "").toLowerCase().includes("corridor");
  const isVillage = (fullSt.zone_type || "").toLowerCase().includes("village");

  const pinClass = isVillage ? "pin-village" : isCorridor ? "pin-corridor" : isBuffer ? "pin-buffer" : "pin-core";
  const detCount = Math.max(fullSt.sighting_count || 0, fullSt.total_detections || 0);
  const hasDetections = detCount > 0 ? "has-detections" : "";
  const isSelected = state.selectedStationId === fullSt.station_id ? "selected-station" : "";

  const customIcon = L.divIcon({
    className: "custom-station-icon",
    html: `<div class="station-map-pin ${pinClass} ${hasDetections} ${isSelected}" id="pin-${fullSt.station_id}" title="${fullSt.station_id}"><i class="fa-solid fa-video"></i></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9]
  });

  const marker = L.marker([fullSt.latitude, fullSt.longitude], { icon: customIcon });

  // Tooltip
  marker.bindTooltip(
    `<strong><i class="fa-solid fa-video"></i> ${fullSt.station_id}</strong><br>` +
    `${fullSt.range} (${fullSt.zone_type})<br>` +
    `<span style="color:#f59e0b;font-size:10px">${detCount} Captures • ${fullSt.unique_tigers ? fullSt.unique_tigers.length : 0} Tigers</span>`,
    { sticky: true }
  );

  // Bind Popup function (dynamically created on click)
  marker.bindPopup(() => createStationPopupHTML(fullSt), { maxWidth: 280 });

  marker.on("click", () => {
    focusCameraStation(fullSt.station_id, false);
  });

  return marker;
}

/**
 * Generates popup HTML for camera station inspection
 */
function createStationPopupHTML(st) {
  const fullSt = state.cameraStationsMap[st.station_id] || st;
  const isCore = (fullSt.zone_type || "").toLowerCase().includes("core");
  const isBuffer = (fullSt.zone_type || "").toLowerCase().includes("buffer");
  const isCorridor = (fullSt.zone_type || "").toLowerCase().includes("corridor");
  const tagClass = isCore ? "tag-core" : isBuffer ? "tag-buffer" : "tag-corridor";
  const zoneLabel = isCore ? "Core Forest" : isBuffer ? "Buffer Zone" : isCorridor ? "Corridor" : fullSt.zone_type;

  const detCount = Math.max(fullSt.sighting_count || 0, fullSt.total_detections || 0);
  const tigers = fullSt.unique_tigers || [];
  const recentPhotos = fullSt.recent_sightings || [];

  let tigersHTML = '<span style="color:#94a3b8;font-size:10px">No tiger captures recorded yet</span>';
  if (tigers.length > 0) {
    tigersHTML = tigers.map(tid => `
      <span class="station-tiger-tag" onclick="selectTiger('${tid}')" title="View Tiger #${tid} Sighting Trail">
        <i class="fa-solid fa-paw"></i> #${tid}
      </span>
    `).join("");
  }

  let photosHTML = "";
  if (recentPhotos.length > 0) {
    photosHTML = `
      <div class="popup-section-title">
        <span><i class="fa-solid fa-images"></i> RECENT CAPTURES</span>
        <span>${recentPhotos.length} photos</span>
      </div>
      <div class="station-recent-photos">
        ${recentPhotos.map((s) => `
          <div class="station-thumb-wrap" onclick="openPhotoModal('${s.filename}')" title="Tiger #${s.tiger_id} @ ${s.timestamp}">
            <img src="Amur Tigers/train/${s.filename}" alt="Tiger ${s.tiger_id}" loading="lazy" />
            <span class="station-thumb-badge">#${s.tiger_id}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  return `
    <div class="popup-station-card">
      <div class="popup-station-header">
        <div>
          <h3><i class="fa-solid fa-video" style="color:var(--accent-emerald)"></i> ${fullSt.station_id}</h3>
          <div style="font-size:11px;color:var(--accent-emerald)">${fullSt.range || 'Pench'} Range</div>
        </div>
        <span class="popup-station-tag ${tagClass}">${zoneLabel}</span>
      </div>

      <div class="station-meta-grid">
        <div class="station-meta-cell">
          <span class="meta-lbl">Total Detections</span>
          <span class="meta-val" style="color:var(--accent-amber)">${detCount} captures</span>
        </div>
        <div class="station-meta-cell">
          <span class="meta-lbl">Unique Tigers</span>
          <span class="meta-val" style="color:var(--accent-emerald)">${tigers.length} identified</span>
        </div>
        <div class="station-meta-cell">
          <span class="meta-lbl">Habitat & Trail</span>
          <span class="meta-val" title="${fullSt.habitat} / ${fullSt.trail_type}">${(fullSt.habitat || 'forest').replace('_', ' ')}</span>
        </div>
        <div class="station-meta-cell">
          <span class="meta-lbl">Trap Effort</span>
          <span class="meta-val">${fullSt.trap_nights ? `${fullSt.trap_nights}d effort` : 'Active'}</span>
        </div>
        <div class="station-meta-cell">
          <span class="meta-lbl">Nearest Village</span>
          <span class="meta-val" title="${fullSt.nearest_village}">${fullSt.nearest_village ? `${fullSt.nearest_village} (${fullSt.nearest_village_km}km)` : 'None'}</span>
        </div>
        <div class="station-meta-cell">
          <span class="meta-lbl">Camera Hardware</span>
          <span class="meta-val" title="${fullSt.camera_type}">${(fullSt.camera_type || 'Camera Trap').split(' ')[0]}</span>
        </div>
      </div>

      <div class="popup-section-title">
        <span><i class="fa-solid fa-paw"></i> TIGERS RECORDED HERE</span>
        <span>${tigers.length}</span>
      </div>
      <div class="station-tigers-tagwrap">
        ${tigersHTML}
      </div>

      ${photosHTML}
    </div>
  `;
}

/**
 * Focuses on a specific camera station from map or sidebar
 */
function focusCameraStation(stationId, shouldFly = true) {
  state.selectedStationId = stationId;
  const st = state.cameraStationsMap[stationId];
  if (!st) return;

  // Ensure camera layer is active
  if (state.selectedAreaRange === "NONE") {
    setCameraVisibility(true, "ALL", false);
  }

  // Update header pill
  const detCount = Math.max(st.sighting_count, st.total_detections || 0);
  document.getElementById("view-mode-pill").style.borderColor = "rgba(16, 185, 129, 0.6)";
  document.getElementById("view-mode-text").innerHTML = `CAMERA: <strong>${st.station_id} (${st.range}) — ${detCount} Detections</strong>`;

  // Update sidebar active banner
  const banner = document.getElementById("active-camera-banner");
  if (banner) {
    banner.classList.remove("hidden");
    document.getElementById("active-cam-name").textContent = `${st.station_id}`;
    document.getElementById("active-cam-info").textContent = `${st.range} | ${st.zone_type} | ${detCount} Detections`;
  }

  // Update card selection in sidebar
  document.querySelectorAll(".camera-card").forEach(c => {
    c.classList.toggle("selected", c.dataset.stationId === stationId);
  });

  // Highlight marker pin on map
  document.querySelectorAll(".station-map-pin").forEach(p => p.classList.remove("selected-station"));
  const pinEl = document.getElementById(`pin-${stationId}`);
  if (pinEl) pinEl.classList.add("selected-station");

  // Fly to camera station and open popup
  if (shouldFly) {
    state.map.flyTo([st.latitude, st.longitude], 15, { duration: 0.8 });
  }

  const marker = state.stationMarkersMap[stationId];
  if (marker) {
    setTimeout(() => {
      marker.openPopup();
    }, shouldFly ? 500 : 50);
  }
}

/**
 * Clears focused camera station
 */
function clearCameraFocus() {
  state.selectedStationId = null;
  const banner = document.getElementById("active-camera-banner");
  if (banner) banner.classList.add("hidden");
  document.querySelectorAll(".camera-card").forEach(c => c.classList.remove("selected"));
  document.querySelectorAll(".station-map-pin").forEach(p => p.classList.remove("selected-station"));
  
  if (state.selectedTigerId) {
    const lastSeen = state.tigersLastSeenMap[state.selectedTigerId];
    const alertLevel = lastSeen?.alert_level || "SAFE";
    document.getElementById("view-mode-pill").style.borderColor = ALERT_COLORS[alertLevel];
    document.getElementById("view-mode-text").innerHTML = `FOCUS: <strong>TIGER #${state.selectedTigerId} — ${alertLevel}</strong>`;
  } else {
    const totalTigers = Object.keys(state.tigersLastSeenMap).length;
    document.getElementById("view-mode-pill").style.borderColor = "rgba(245, 158, 11, 0.35)";
    document.getElementById("view-mode-text").innerHTML = `MAP MODE: <strong>TIGERS LAST SEEN (${totalTigers})</strong>`;
  }
}

/**
 * Renders the camera station cards in the sidebar directory
 */
function renderCameraDirectory() {
  const container = document.getElementById("camera-list");
  if (!container) return;
  container.innerHTML = "";

  const query = (document.getElementById("camera-search")?.value || "").trim().toLowerCase();
  const rangeFilter = document.getElementById("cam-sidebar-range-select")?.value || "ALL";

  let stations = Object.values(state.cameraStationsMap);

  stations = stations.filter(st => {
    const stId = (st.station_id || "").toLowerCase();
    const range = (st.range || "").toLowerCase();
    const habitat = (st.habitat || "").toLowerCase();
    const village = (st.nearest_village || "").toLowerCase();
    const zone = (st.zone_type || "").toLowerCase();
    const camType = (st.camera_type || "").toLowerCase();

    // Query search
    if (query && !stId.includes(query) && !range.includes(query) && !habitat.includes(query) && !village.includes(query)) {
      return false;
    }

    // Range dropdown filter
    if (rangeFilter !== "ALL" && st.range !== rangeFilter) {
      return false;
    }

    // Chip filter
    if (state.filterCamType === "core" && !zone.includes("core")) return false;
    if (state.filterCamType === "buffer" && !zone.includes("buffer")) return false;
    if (state.filterCamType === "active" && (st.sighting_count === 0 && (st.total_detections || 0) === 0)) return false;
    if (state.filterCamType === "cctv" && !camType.includes("cctv") && !camType.includes("solar")) return false;

    return true;
  });

  // Sort: highest detections first, then station ID
  stations.sort((a, b) => {
    const detA = Math.max(a.sighting_count, a.total_detections || 0);
    const detB = Math.max(b.sighting_count, b.total_detections || 0);
    if (detB !== detA) return detB - detA;
    return (a.station_id || "").localeCompare(b.station_id || "");
  });

  const visibleCountEl = document.getElementById("visible-cam-count");
  if (visibleCountEl) visibleCountEl.textContent = `${stations.length} Cameras`;

  stations.forEach(st => {
    const isCore = (st.zone_type || "").toLowerCase().includes("core");
    const isBuffer = (st.zone_type || "").toLowerCase().includes("buffer");
    const isCorridor = (st.zone_type || "").toLowerCase().includes("corridor");
    const zoneClass = isCore ? "zone-core" : isBuffer ? "zone-buffer" : isCorridor ? "zone-corridor" : "zone-core";
    const zoneName = isCore ? "Core Forest" : isBuffer ? "Buffer Zone" : isCorridor ? "Corridor" : "Reserve";

    const detCount = Math.max(st.sighting_count, st.total_detections || 0);
    const tigerCount = st.unique_tigers ? st.unique_tigers.length : 0;

    const card = document.createElement("div");
    card.className = `camera-card ${state.selectedStationId === st.station_id ? "selected" : ""}`;
    card.dataset.stationId = st.station_id;

    card.innerHTML = `
      <div class="cam-card-left">
        <div class="cam-icon-avatar ${zoneClass}">
          <i class="fa-solid fa-video"></i>
        </div>
        <div class="cam-card-info">
          <div class="cam-card-title">
            <span>${st.station_id}</span>
            <span class="cam-card-badge">${zoneName}</span>
          </div>
          <div class="cam-card-sub">
            <span>${st.range || 'Pench'}</span> • <span>${(st.habitat || '').replace('_', ' ')}</span>
          </div>
        </div>
      </div>
      <div class="cam-card-right">
        <span class="cam-badge-detections">${detCount} Detections</span>
        <span class="cam-badge-tigers"><i class="fa-solid fa-paw"></i> ${tigerCount} Tigers</span>
        <span class="cam-badge-nights">${st.trap_nights ? `${st.trap_nights}d effort` : ''}</span>
      </div>
    `;

    card.addEventListener("click", () => focusCameraStation(st.station_id));
    container.appendChild(card);
  });
}

function handleAreaCameraChange(rangeName) {
  if (rangeName === "NONE") {
    setCameraVisibility(false, "NONE");
  } else {
    setCameraVisibility(true, rangeName, true);
  }
}

// ---------------------------------------------------------------------------
// 8. SIDEBAR TIGER DIRECTORY
// ---------------------------------------------------------------------------
function renderTigerDirectory() {
  const container = document.getElementById("tiger-list");
  container.innerHTML = "";

  const query = (document.getElementById("tiger-search").value || "").trim().toLowerCase();
  
  let tigerIds = Object.keys(state.tigerSightingsMap).sort((a, b) => {
    return state.tigerSightingsMap[b].length - state.tigerSightingsMap[a].length;
  });

  tigerIds = tigerIds.filter(tid => {
    const tInfo = state.data.territories[tid];
    const sCount = state.tigerSightingsMap[tid].length;
    const lastSeen = state.tigersLastSeenMap[tid];
    const alertLevel = lastSeen?.alert_level || "SAFE";

    if (query && !tid.includes(query) && !tInfo?.primary_range?.toLowerCase().includes(query)) {
      return false;
    }

    if (state.filterSex === "male" && tInfo?.sex !== "Male") return false;
    if (state.filterSex === "female" && tInfo?.sex !== "Female") return false;
    if (state.filterSex === "alert" && alertLevel === "SAFE") return false;

    return true;
  });

  // Sort: CRITICAL first, then CAUTION, then SAFE
  tigerIds.sort((a, b) => {
    const alertOrder = { CRITICAL: 0, CAUTION: 1, SAFE: 2 };
    const aAlert = state.tigersLastSeenMap[a]?.alert_level || "SAFE";
    const bAlert = state.tigersLastSeenMap[b]?.alert_level || "SAFE";
    if (alertOrder[aAlert] !== alertOrder[bAlert]) return alertOrder[aAlert] - alertOrder[bAlert];
    return state.tigerSightingsMap[b].length - state.tigerSightingsMap[a].length;
  });

  document.getElementById("visible-tiger-count").textContent = `${tigerIds.length} Tigers`;

  tigerIds.forEach(tid => {
    const tInfo = state.data.territories[tid];
    const sCount = state.tigerSightingsMap[tid].length;
    const lastSeen = state.tigersLastSeenMap[tid];
    const alertLevel = lastSeen?.alert_level || "SAFE";
    const alertClass = `alert-${alertLevel.toLowerCase()}`;
    const tagClass = `tag-${alertLevel.toLowerCase()}`;

    const card = document.createElement("div");
    card.className = `tiger-card ${state.selectedTigerId == tid ? "selected" : ""}`;
    card.dataset.tigerId = tid;

    card.innerHTML = `
      <div class="tiger-card-left">
        <div class="tiger-badge-icon ${alertClass}">#${tid}</div>
        <div class="tiger-info-main">
          <span class="tiger-name">Tiger #${tid} (${tInfo?.sex || '?'})</span>
          <span class="tiger-range">${tInfo?.primary_range || 'Unknown'}</span>
        </div>
      </div>
      <div class="tiger-card-right">
        <span class="tiger-alert-tag ${tagClass}">${alertLevel}</span>
        <span class="tiger-sightings">${sCount} Sightings</span>
        <span class="tiger-last-date">${lastSeen ? lastSeen.timestamp.split(' ')[0] : ''}</span>
      </div>
    `;

    card.addEventListener("click", () => selectTiger(tid));
    container.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// 9. GALLERY DOCK
// ---------------------------------------------------------------------------
function renderGalleryDock(sightings, tigerId) {
  const dock = document.getElementById("gallery-dock");
  const dockStrip = document.getElementById("dock-strip");
  const dockTitle = document.getElementById("dock-tiger-title");
  const dockCount = document.getElementById("dock-count");

  dock.classList.remove("hidden");
  dockStrip.innerHTML = "";
  dockTitle.textContent = `TIGER #${tigerId}`;
  dockCount.textContent = `${sightings.length} Captures`;

  sightings.forEach((s, idx) => {
    const card = document.createElement("div");
    card.className = "thumb-card";
    card.title = `Sighting #${idx + 1} @ ${s.station_id} (${s.timestamp})`;
    card.innerHTML = `
      <img src="Amur Tigers/train/${s.filename}" alt="Tiger ${tigerId}" loading="lazy" />
      <span class="thumb-badge">#${idx + 1}</span>
    `;
    card.addEventListener("click", () => openPhotoModal(s.filename));
    dockStrip.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// 10. PHOTO MODAL
// ---------------------------------------------------------------------------
window.openPhotoModal = function(filename) {
  const sighting = state.data.sightings.find(s => s.filename === filename);
  if (!sighting) return;

  state.selectedSightingIndex = state.activeSightingsList.findIndex(s => s.filename === filename);
  const total = state.activeSightingsList.length || 1;
  const currentIdx = state.selectedSightingIndex >= 0 ? state.selectedSightingIndex + 1 : 1;

  const modal = document.getElementById("photo-modal");
  modal.classList.remove("hidden");

  const alertLevel = sighting.alert_level || "SAFE";
  const alertBadge = document.getElementById("modal-alert-badge");
  alertBadge.textContent = alertLevel;
  alertBadge.className = `modal-alert-badge badge-${alertLevel.toLowerCase()}`;

  document.getElementById("modal-tiger-badge").textContent = `TIGER #${sighting.tiger_id}`;
  document.getElementById("modal-station-title").textContent = sighting.station_id;
  document.getElementById("modal-landmark-name").textContent = `${sighting.range} — ${sighting.zone_type}`;
  document.getElementById("modal-timestamp").textContent = sighting.timestamp;
  document.getElementById("modal-range-zone").textContent = `${sighting.zone_type} (${alertLevel})`;
  document.getElementById("modal-coords").textContent = `${sighting.latitude.toFixed(6)}° N, ${sighting.longitude.toFixed(6)}° E`;
  document.getElementById("modal-temp").textContent = `${sighting.ambient_temp_c} °C`;
  document.getElementById("modal-lighting").textContent = sighting.lighting_condition;
  document.getElementById("modal-cam-type").textContent = sighting.camera_type;
  document.getElementById("modal-nearest-village").textContent = sighting.nearest_village ? `${sighting.nearest_village} (${sighting.nearest_village_dist_km} km)` : "None nearby";
  document.getElementById("modal-sighting-order").textContent = `Sighting #${currentIdx} of ${total}`;

  const img = document.getElementById("modal-tiger-img");
  const canvas = document.getElementById("modal-keypoint-canvas");

  img.src = `Amur Tigers/train/${sighting.filename}`;
  img.onload = () => {
    drawPoseKeypoints(img, canvas, sighting.keypoints || []);
  };
};

function drawPoseKeypoints(img, canvas, keypoints) {
  const ctx = canvas.getContext("2d");
  const rect = img.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!state.showKeypoints || !keypoints || keypoints.length < 45) {
    document.getElementById("modal-keypoints-count").textContent = "Keypoints Hidden";
    return;
  }

  const scaleX = rect.width / img.naturalWidth;
  const scaleY = rect.height / img.naturalHeight;

  const pts = [];
  for (let i = 0; i < 15; i++) {
    const x = keypoints[i * 3] * scaleX;
    const y = keypoints[i * 3 + 1] * scaleY;
    const v = keypoints[i * 3 + 2];
    pts.push({ x, y, v });
  }

  const SKELETON_BONES = [
    [0, 1], [0, 2], [1, 3], [2, 4],
    [0, 5], [5, 6], [5, 8],
    [6, 7], [8, 9],
    [5, 10], [10, 11], [10, 13],
    [11, 12], [13, 14],
    [10, 14]
  ];

  ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(245, 158, 11, 0.85)";
  ctx.shadowColor = "#f59e0b";
  ctx.shadowBlur = 8;

  SKELETON_BONES.forEach(([i1, i2]) => {
    const p1 = pts[i1];
    const p2 = pts[i2];
    if (p1 && p2 && p1.v > 0 && p2.v > 0 && (p1.x !== 0 || p1.y !== 0) && (p2.x !== 0 || p2.y !== 0)) {
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
    }
  });

  pts.forEach((p, idx) => {
    if (p.v > 0 && (p.x !== 0 || p.y !== 0)) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5, 0, 2 * Math.PI);
      ctx.fillStyle = idx === 0 ? "#ef4444" : "#10b981";
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();
    }
  });

  const validCount = pts.filter(p => p.v > 0 && (p.x !== 0 || p.y !== 0)).length;
  document.getElementById("modal-keypoints-count").textContent = `${validCount} / 15 Visible Joints`;
}

// ---------------------------------------------------------------------------
// 11. EVENT LISTENERS
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Sidebar Toggle
  document.getElementById("btn-toggle-sidebar").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("collapsed");
  });

  // Sidebar Tab Switcher (Tigers vs Camera Network)
  document.querySelectorAll(".sidebar-tab").forEach(tabBtn => {
    tabBtn.addEventListener("click", () => {
      document.querySelectorAll(".sidebar-tab").forEach(b => b.classList.remove("active"));
      tabBtn.classList.add("active");

      const targetTab = tabBtn.dataset.tab;
      state.activeTab = targetTab;

      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      if (targetTab === "tigers") {
        document.getElementById("pane-tigers")?.classList.add("active");
        document.getElementById("active-camera-banner")?.classList.add("hidden");
      } else if (targetTab === "cameras") {
        document.getElementById("pane-cameras")?.classList.add("active");
        // Automatically make camera network visible when entering camera tab if hidden
        if (state.selectedAreaRange === "NONE") {
          setCameraVisibility(true, "ALL", true);
        }
      }
    });
  });

  // All Cameras Header Toggle Checkbox
  const toggleAllCams = document.getElementById("toggle-all-cameras");
  if (toggleAllCams) {
    toggleAllCams.addEventListener("change", (e) => {
      setCameraVisibility(e.target.checked, "ALL", true);
    });
  }

  // Area Camera Dropdown
  document.getElementById("select-area-cams").addEventListener("change", (e) => {
    handleAreaCameraChange(e.target.value);
  });

  // Camera Directory Search & Filters
  document.getElementById("camera-search")?.addEventListener("input", renderCameraDirectory);

  document.querySelectorAll("#camera-filter-chips .chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll("#camera-filter-chips .chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.filterCamType = chip.dataset.camFilter;
      renderCameraDirectory();
    });
  });

  document.getElementById("cam-sidebar-range-select")?.addEventListener("change", (e) => {
    state.filterCamRange = e.target.value;
    renderCameraDirectory();
    if (e.target.value !== "ALL") {
      setCameraVisibility(true, e.target.value, true);
    } else {
      setCameraVisibility(true, "ALL", false);
    }
  });

  document.getElementById("btn-clear-cam-focus")?.addEventListener("click", clearCameraFocus);

  // Zone Boundaries Toggle
  document.getElementById("toggle-zones").addEventListener("change", (e) => {
    state.showZones = e.target.checked;
    if (state.showZones) {
      renderZoneBoundaries();
      state.layers.zoneBoundaries.addTo(state.map);
    } else {
      state.layers.zoneBoundaries.clearLayers();
    }
  });

  // Sub-Regions Toggle
  document.getElementById("toggle-subregions").addEventListener("change", (e) => {
    state.showSubRegions = e.target.checked;
    if (state.showSubRegions) {
      renderSubRegions();
      state.layers.subRegions.addTo(state.map);
    } else {
      state.map.removeLayer(state.layers.subRegions);
      state.layers.subRegions.clearLayers();
    }
  });

  // Village Markers Toggle
  document.getElementById("toggle-villages").addEventListener("change", (e) => {
    state.showVillages = e.target.checked;
    if (state.showVillages) {
      renderVillageMarkers();
      state.layers.villageMarkers.addTo(state.map);
    } else {
      state.map.removeLayer(state.layers.villageMarkers);
      state.layers.villageMarkers.clearLayers();
    }
  });

  // Basemap Switcher
  document.querySelectorAll(".btn-basemap").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-basemap").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const type = btn.dataset.map;
      if (type === "satellite") {
        state.map.removeLayer(state.layers.dark);
        state.layers.satellite.addTo(state.map);
        state.layers.labels.addTo(state.map);
      } else if (type === "hybrid") {
        state.map.removeLayer(state.layers.dark);
        state.layers.satellite.addTo(state.map);
        state.layers.labels.addTo(state.map);
      } else if (type === "dark") {
        state.map.removeLayer(state.layers.satellite);
        state.map.removeLayer(state.layers.labels);
        state.layers.dark.addTo(state.map);
      }
    });
  });

  // Reset View
  document.getElementById("btn-reset-view").addEventListener("click", () => {
    clearTigerSelection();
    clearCameraFocus();
  });
  document.getElementById("btn-clear-tiger").addEventListener("click", clearTigerSelection);

  // Tiger Search & Filters
  document.getElementById("tiger-search").addEventListener("input", renderTigerDirectory);

  document.querySelectorAll(".quick-filter-chips .chip[data-filter]").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".quick-filter-chips .chip[data-filter]").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.filterSex = chip.dataset.filter;
      renderTigerDirectory();
    });
  });

  // Modal Controls
  document.getElementById("btn-close-modal").addEventListener("click", () => {
    document.getElementById("photo-modal").classList.add("hidden");
  });

  document.getElementById("btn-toggle-keypoints").addEventListener("click", (e) => {
    state.showKeypoints = !state.showKeypoints;
    e.currentTarget.classList.toggle("active", state.showKeypoints);
    const img = document.getElementById("modal-tiger-img");
    const canvas = document.getElementById("modal-keypoint-canvas");
    const sighting = state.activeSightingsList[state.selectedSightingIndex];
    if (sighting) drawPoseKeypoints(img, canvas, sighting.keypoints || []);
  });

  document.getElementById("btn-prev-photo").addEventListener("click", () => {
    if (state.activeSightingsList.length === 0) return;
    state.selectedSightingIndex = (state.selectedSightingIndex - 1 + state.activeSightingsList.length) % state.activeSightingsList.length;
    openPhotoModal(state.activeSightingsList[state.selectedSightingIndex].filename);
  });

  document.getElementById("btn-next-photo").addEventListener("click", () => {
    if (state.activeSightingsList.length === 0) return;
    state.selectedSightingIndex = (state.selectedSightingIndex + 1) % state.activeSightingsList.length;
    openPhotoModal(state.activeSightingsList[state.selectedSightingIndex].filename);
  });

  // Gallery Dock Toggle
  document.getElementById("btn-dock-toggle").addEventListener("click", () => {
    const dock = document.getElementById("gallery-dock");
    dock.classList.toggle("collapsed");
    // Adjust timeline position based on dock expanded/collapsed state
    const widget = document.getElementById('timeline-widget');
    if (!widget.classList.contains('hidden')) {
      widget.classList.toggle('above-dock', !dock.classList.contains('collapsed'));
    }
  });

  // ---- TIMELINE SLIDER EVENTS ----
  const sliderStart = document.getElementById('timeline-start');
  const sliderEnd   = document.getElementById('timeline-end');

  function onSliderChange() {
    let s = parseInt(sliderStart.value, 10);
    let e = parseInt(sliderEnd.value,   10);
    // Prevent handles from crossing
    if (s > e) {
      if (this === sliderStart) { sliderStart.value = e; s = e; }
      else                      { sliderEnd.value   = s; e = s; }
    }
    state.timeline.startIdx = s;
    state.timeline.endIdx   = e;
    // Clear active preset when user drags manually
    document.querySelectorAll('.btn-tl-preset').forEach(b => b.classList.remove('active'));
    renderFilteredTrail();
  }

  sliderStart.addEventListener('input', onSliderChange);
  sliderEnd.addEventListener('input',   onSliderChange);

  // Preset quick-select buttons
  document.querySelectorAll('.btn-tl-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      const tid = state.selectedTigerId;
      if (!tid) return;
      const total = (state.tigerSightingsMap[tid] || []).length;
      const maxIdx = Math.max(0, total - 1);
      const n = btn.dataset.n;

      document.querySelectorAll('.btn-tl-preset').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      let startIdx, endIdx;
      if (n === 'all') {
        startIdx = 0;
        endIdx   = maxIdx;
      } else {
        const count = parseInt(n, 10);
        startIdx = Math.max(0, total - count);
        endIdx   = maxIdx;
      }

      state.timeline.startIdx = startIdx;
      state.timeline.endIdx   = endIdx;
      sliderStart.value = startIdx;
      sliderEnd.value   = endIdx;
      renderFilteredTrail();
    });
  });

  // Territory visibility toggle
  document.getElementById('tl-show-territory').addEventListener('change', (e) => {
    state.timeline.showTerritory = e.target.checked;
    renderFilteredTrail();
  });
}
