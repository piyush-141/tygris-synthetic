/**
 * Pench Tiger Reserve - Zone Alert Monitoring Dashboard
 * app.js v2 — Zone boundaries, alert-level pins, village markers
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
  selectedTigerId: null,
  selectedSightingIndex: 0,
  activeSightingsList: [],
  selectedAreaRange: "NONE",
  filterSex: "all",
  showKeypoints: true,
  showZones: true,
  showSubRegions: true,
  showVillages: false
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
    populateAreaCamDropdown();
    renderTigerDirectory();
    renderTigersLastSeenOnMap();
    renderZoneBoundaries();
    renderSubRegions();
    updateAlertPanel();

    const totalTigers = Object.keys(state.tigersLastSeenMap).length;
    document.getElementById("total-tiger-count").textContent = totalTigers;
    document.getElementById("view-mode-text").innerHTML = `MAP MODE: <strong>TIGERS LAST SEEN (${totalTigers})</strong>`;

    console.log("Pench Tiger Zone Alert Dashboard ready!", {
      totalTigers,
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

function populateAreaCamDropdown() {
  const select = document.getElementById("select-area-cams");
  const ranges = {};
  state.data.stations.forEach(st => {
    if (!ranges[st.range]) ranges[st.range] = 0;
    ranges[st.range]++;
  });

  Object.entries(ranges).forEach(([name, count]) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = `${name} (${count} cams)`;
    select.appendChild(opt);
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
  state.layers.singleTigerTrail.clearLayers();
  state.layers.singleTigerTerritory.clearLayers();

  // Territory circle — subtle dashed outline only
  if (tInfo) {
    const circle = L.circle([tInfo.centroid_lat, tInfo.centroid_lon], {
      radius: tInfo.territory_radius_km * 1000,
      color: "#f59e0b",
      weight: 1.5,
      dashArray: "6, 8",
      fillColor: "#f59e0b",
      fillOpacity: 0.04
    });
    circle.bindTooltip(`Home Range: Tiger #${tigerId} (${tInfo.territory_radius_km} km radius)`, { sticky: true });
    state.layers.singleTigerTerritory.addLayer(circle);
  }

  // Trajectory polyline
  if (sightings.length > 1) {
    const latlngs = sightings.map(s => [s.latitude, s.longitude]);
    const polyline = L.polyline(latlngs, {
      color: "#ffffff",
      weight: 1.5,
      dashArray: "4, 8",
      opacity: 0.7
    });
    state.layers.singleTigerTrail.addLayer(polyline);
  }

  // Numbered trail markers
  sightings.forEach((s, idx) => {
    const isLatest = idx === sightings.length - 1;
    const alertColor = ALERT_COLORS[s.alert_level || "SAFE"];
    const customIcon = L.divIcon({
      className: "custom-trail-icon",
      html: `<div class="trail-step-pin" style="${isLatest ? `background:${alertColor};color:#fff;border-color:#fff;transform:scale(1.2)` : ''}">${idx + 1}</div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    const marker = L.marker([s.latitude, s.longitude], { icon: customIcon });
    marker.bindPopup(createSightingPopupHTML(s, idx + 1, sightings.length));
    state.layers.singleTigerTrail.addLayer(marker);
  });

  renderGalleryDock(sightings, tigerId);

  if (sightings.length > 0) {
    const bounds = L.latLngBounds(sightings.map(s => [s.latitude, s.longitude]));
    state.map.flyToBounds(bounds.pad(0.3), { duration: 1.0 });
  }
};

function clearTigerSelection() {
  state.selectedTigerId = null;
  state.activeSightingsList = [];

  const totalTigers = Object.keys(state.tigersLastSeenMap).length;
  document.getElementById("view-mode-pill").style.borderColor = "rgba(245, 158, 11, 0.35)";
  document.getElementById("view-mode-text").innerHTML = `MAP MODE: <strong>TIGERS LAST SEEN (${totalTigers})</strong>`;

  document.getElementById("active-tiger-banner").classList.add("hidden");
  document.getElementById("gallery-dock").classList.add("hidden");
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
// 7. AREA CAMERA NETWORK TOGGLE
// ---------------------------------------------------------------------------
function handleAreaCameraChange(rangeName) {
  state.selectedAreaRange = rangeName;
  state.layers.areaCameras.clearLayers();

  const legendCamItem = document.getElementById("legend-cam-item");

  if (rangeName === "NONE") {
    legendCamItem.style.display = "none";
    return;
  }

  legendCamItem.style.display = "flex";

  const areaStations = state.data.stations.filter(st => st.range === rangeName);

  areaStations.forEach(st => {
    const customIcon = L.divIcon({
      className: "custom-cam-icon",
      html: `<div class="area-camera-pin"><i class="fa-solid fa-video"></i></div>`,
      iconSize: [16, 16],
      iconAnchor: [8, 8]
    });

    const marker = L.marker([st.latitude, st.longitude], { icon: customIcon });
    marker.bindPopup(`
      <div class="popup-card" style="width:200px">
        <div class="popup-body">
          <div class="popup-title">${st.station_id}</div>
          <div class="popup-sub">${st.range} (${st.zone_type})</div>
          <div class="popup-meta">
            <span><strong>Type:</strong> ${st.camera_type}</span>
            <span><strong>Zone:</strong> ${st.zone_type}</span>
          </div>
        </div>
      </div>
    `);
    state.layers.areaCameras.addLayer(marker);
  });

  if (areaStations.length > 0) {
    const bounds = L.latLngBounds(areaStations.map(st => [st.latitude, st.longitude]));
    state.map.flyToBounds(bounds.pad(0.2), { duration: 1.0 });
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

  // Area Camera Dropdown
  document.getElementById("select-area-cams").addEventListener("change", (e) => {
    handleAreaCameraChange(e.target.value);
  });

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
  document.getElementById("btn-reset-view").addEventListener("click", clearTigerSelection);
  document.getElementById("btn-clear-tiger").addEventListener("click", clearTigerSelection);

  // Search & Filters
  document.getElementById("tiger-search").addEventListener("input", renderTigerDirectory);

  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
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
    document.getElementById("gallery-dock").classList.toggle("collapsed");
  });
}
