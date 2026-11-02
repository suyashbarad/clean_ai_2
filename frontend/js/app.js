// ==========================================================================
// CleanGreen AI 2.0 — Pune Smart City Waste Intelligence Platform
// ==========================================================================

const DEFAULT_COORDS = {
  lat: 18.5178,
  lng: 73.8151,
  address: "MIT World Peace University (MIT-WPU), Paud Road, Kothrud, Pune"
};

const state = {
  currentView: "landing",
  currentRole: "citizen",
  userCredits: 300,
  userId: "u1",
  selectedLat: DEFAULT_COORDS.lat,
  selectedLng: DEFAULT_COORDS.lng,
  selectedAddress: DEFAULT_COORDS.address,
  uploadedPhotoFile: null,
  exifCoords: null,
  activeResolveTaskId: null,
  cleanbotHistory: []
};

// Maps storage
let reportMap = null;
let reportMarker = null;
let cityMap = null;
let cityLayers = { bins: null, complaints: null, hotspots: null };
let workerMap = null;
let wardRiskChart = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
  initReportMap();
  loadCityStats();
  setupRoleVisibility();
});

// View Switcher
function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));

  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) targetPanel.classList.add("active");

  const targetNav = document.querySelector(`.nav-link[data-view="${viewName}"]`);
  if (targetNav) targetNav.classList.add("active");

  // View specific setups
  if (viewName === "map") {
    setTimeout(() => initCityMap(), 150);
  } else if (viewName === "tracker") {
    loadComplaintsList();
  } else if (viewName === "rewards") {
    loadRewardsData();
  } else if (viewName === "admin") {
    loadAdminComplaints();
    setTimeout(() => initAdminTruckMap(), 200);
  } else if (viewName === "worker") {
    loadWorkerDashboard();
  } else if (viewName === "hotspots") {
    runHotspotsAnalysis();
  } else if (viewName === "mclp") {
    runMCLPOptimization();
  } else if (viewName === "citizen") {
    setTimeout(() => {
      if (reportMap) reportMap.invalidateSize();
    }, 150);
  }
}

// Role Changing
function handleRoleChange(role) {
  state.currentRole = role;
  setupRoleVisibility();
  if (role === "admin") {
    switchView("admin");
  } else if (role === "worker") {
    switchView("worker");
  } else {
    switchView("citizen");
  }
}

function setupRoleVisibility() {
  const isAdmin = state.currentRole === "admin" || state.currentRole === "superadmin";
  const isWorker = state.currentRole === "worker";

  document.querySelectorAll(".admin-only").forEach(el => {
    el.style.display = isAdmin ? "flex" : "none";
  });
  document.querySelectorAll(".worker-only").forEach(el => {
    el.style.display = isWorker ? "flex" : "none";
  });
}

// ==========================================================================
// 1. Report Waste & AI Vision
// ==========================================================================

function initReportMap() {
  const container = document.getElementById("report-map");
  if (!container || reportMap) return;

  reportMap = L.map("report-map").setView([DEFAULT_COORDS.lat, DEFAULT_COORDS.lng], 16);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors"
  }).addTo(reportMap);

  reportMarker = L.marker([DEFAULT_COORDS.lat, DEFAULT_COORDS.lng], { draggable: true }).addTo(reportMap);
  reportMarker.bindPopup("<b>Waste Pin</b><br>Drag to adjust exact location.").openPopup();

  reportMarker.on("dragend", async (e) => {
    const pos = e.target.getLatLng();
    updateCoordsUI(pos.lat, pos.lng);
    await reverseGeocode(pos.lat, pos.lng);
  });

  reportMap.on("click", async (e) => {
    reportMarker.setLatLng(e.latlng);
    updateCoordsUI(e.latlng.lat, e.latlng.lng);
    await reverseGeocode(e.latlng.lat, e.latlng.lng);
  });
}

function updateCoordsUI(lat, lng) {
  state.selectedLat = lat;
  state.selectedLng = lng;
  document.getElementById("report-lat-val").textContent = lat.toFixed(6);
  document.getElementById("report-lng-val").textContent = lng.toFixed(6);
}

async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
    const data = await res.json();
    if (data && data.display_name) {
      state.selectedAddress = data.display_name;
      document.getElementById("report-resolved-address").textContent = data.display_name;
    }
  } catch (err) {
    console.warn("Reverse geocode fallback", err);
  }
}

function resetToMIT() {
  if (reportMarker) reportMarker.setLatLng([DEFAULT_COORDS.lat, DEFAULT_COORDS.lng]);
  if (reportMap) reportMap.setView([DEFAULT_COORDS.lat, DEFAULT_COORDS.lng], 16);
  updateCoordsUI(DEFAULT_COORDS.lat, DEFAULT_COORDS.lng);
  state.selectedAddress = DEFAULT_COORDS.address;
  document.getElementById("report-resolved-address").textContent = DEFAULT_COORDS.address;
}

function getUserCurrentLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        if (reportMarker) reportMarker.setLatLng([latitude, longitude]);
        if (reportMap) reportMap.setView([latitude, longitude], 17);
        updateCoordsUI(latitude, longitude);
        reverseGeocode(latitude, longitude);
      },
      (err) => alert("Could not fetch device GPS. Using Pune default.")
    );
  }
}

async function handlePhotoSelected(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  state.uploadedPhotoFile = file;

  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("image-preview").src = e.target.result;
    document.getElementById("preview-filename").textContent = file.name;
    document.getElementById("drop-prompt").classList.add("hidden");
    document.getElementById("preview-wrapper").classList.remove("hidden");
  };
  reader.readAsDataURL(file);

  // Extract EXIF GPS
  try {
    if (window.exifr) {
      const gps = await exifr.gps(file);
      if (gps && gps.latitude && gps.longitude) {
        state.exifCoords = gps;
        document.getElementById("exif-coords-display").textContent = `Lat: ${gps.latitude.toFixed(5)}, Lng: ${gps.longitude.toFixed(5)}`;
        document.getElementById("exif-alert").classList.remove("hidden");
      }
    }
  } catch (e) {
    console.log("No EXIF GPS found in image");
  }

  // Real-time AI preview call
  const formData = new FormData();
  formData.append("photo", file);
  formData.append("notes", document.getElementById("form-notes").value);

  try {
    const res = await fetch("/api/complaints/analyze-preview", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.analysis) {
      const a = data.analysis;
      document.getElementById("ai-vision-box").classList.remove("hidden");
      document.getElementById("ai-category-val").textContent = a.primary_category;
      document.getElementById("ai-conf-badge").textContent = `${Math.round(a.confidence * 100)}% Confidence`;
      document.getElementById("ai-severity-badge").textContent = a.severity;
      document.getElementById("ai-accumulation-val").textContent = a.accumulation_estimate;
      document.getElementById("ai-recommended-val").textContent = a.recommended_action;

      // Auto set form category
      document.getElementById("form-category").value = a.primary_category;
    }
  } catch (err) {
    console.error("AI preview error", err);
  }
}

function applyExifLocation() {
  if (state.exifCoords) {
    const { latitude, longitude } = state.exifCoords;
    if (reportMarker) reportMarker.setLatLng([latitude, longitude]);
    if (reportMap) reportMap.setView([latitude, longitude], 17);
    updateCoordsUI(latitude, longitude);
    reverseGeocode(latitude, longitude);
    document.getElementById("exif-alert").classList.add("hidden");
  }
}

function removeSelectedPhoto(e) {
  e.stopPropagation();
  state.uploadedPhotoFile = null;
  state.exifCoords = null;
  document.getElementById("photo-input").value = "";
  document.getElementById("preview-wrapper").classList.add("hidden");
  document.getElementById("drop-prompt").classList.remove("hidden");
  document.getElementById("ai-vision-box").classList.add("hidden");
  document.getElementById("exif-alert").classList.add("hidden");
}

async function submitWasteReport() {
  const btn = document.getElementById("btn-submit-report");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Analyzing & Registering...`;

  const formData = new FormData();
  formData.append("latitude", state.selectedLat);
  formData.append("longitude", state.selectedLng);
  formData.append("address", state.selectedAddress);
  formData.append("category", document.getElementById("form-category").value);
  formData.append("ward_id", document.getElementById("form-ward").value);
  formData.append("notes", document.getElementById("form-notes").value);

  if (state.uploadedPhotoFile) {
    formData.append("photo", state.uploadedPhotoFile);
  }

  try {
    const res = await fetch("/api/complaints", {
      method: "POST",
      body: formData
    });
    const result = await res.json();

    if (result.success) {
      state.userCredits += 50;
      updateHeaderCredits();
      switchView("tracker");
      setTimeout(() => openForensicModal(result.complaint.id), 350);
    } else {
      alert("Submission error: " + (result.detail || "Please try again."));
    }
  } catch (err) {
    alert("Network error submitting complaint.");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit Waste Complaint (+50 PTS)`;
  }
}

// ==========================================================================
// 2. Complaint Tracker
// ==========================================================================

async function loadComplaintsList() {
  const statusFilter = document.getElementById("tracker-filter-status").value;
  const searchFilter = document.getElementById("tracker-search").value;

  let url = `/api/complaints?status=${statusFilter}`;
  if (searchFilter) url += `&search=${encodeURIComponent(searchFilter)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    const container = document.getElementById("complaints-list");

    if (!data.complaints || data.complaints.length === 0) {
      container.innerHTML = `<div class="card text-center py-4"><p>No complaints found matching criteria.</p></div>`;
      return;
    }

    container.innerHTML = data.complaints.map(c => `
      <div class="complaint-card" onclick="openForensicModal('${c.id}')" style="cursor: pointer;">
        <img src="${c.image_url}" alt="Waste" class="complaint-thumb" onerror="this.src='https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600'" />
        <div class="complaint-info">
          <h4>${c.id} — ${c.category}</h4>
          <div class="complaint-meta">
            <span><i class="fa-solid fa-location-dot"></i> ${c.address}</span>
            <span><i class="fa-solid fa-shield"></i> ${c.ward_name}</span>
          </div>
          <p class="text-sm text-muted">${c.ai_description || c.notes || 'AI Verified report.'}</p>
          ${renderTimelineTrack(c.status)}
        </div>
        <div class="complaint-actions text-right" onclick="event.stopPropagation()">
          <span class="badge ${getSeverityBadge(c.severity)}">${c.severity} Severity</span>
          <p class="mono text-xs text-muted mt-2">${c.created_at}</p>
          <div class="flex gap-2 justify-end mt-2">
            <button type="button" class="btn btn-sm btn-outline text-emerald" onclick="openForensicModal('${c.id}')">
              <i class="fa-solid fa-file-waveform"></i> Forensic Audit
            </button>
            ${c.after_image_url ? `
              <a href="${c.after_image_url}" target="_blank" class="btn btn-sm btn-outline text-emerald">
                <i class="fa-solid fa-camera-rotate"></i> After
              </a>
            ` : ''}
          </div>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Load complaints failed", err);
  }
}

function renderTimelineTrack(status) {
  const steps = ["Submitted", "Verified", "Assigned", "Resolved"];
  const curIdx = steps.indexOf(status) !== -1 ? steps.indexOf(status) : 1;

  return `
    <div class="timeline-track">
      ${steps.map((st, idx) => `
        <div class="step-node ${idx <= curIdx ? 'completed' : ''} ${idx === curIdx ? 'current' : ''}">
          <div class="step-dot"></div>
          <span>${st}</span>
        </div>
      `).join("")}
    </div>
  `;
}

function getSeverityBadge(sev) {
  if (sev === "Critical") return "badge-danger";
  if (sev === "High") return "badge-warning";
  if (sev === "Low") return "badge-info";
  return "badge-success";
}

// ==========================================================================
// 3. Interactive City Map
// ==========================================================================

async function initCityMap() {
  const container = document.getElementById("city-map");
  if (!container) return;

  if (!cityMap) {
    cityMap = L.map("city-map").setView([18.5204, 73.8567], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors"
    }).addTo(cityMap);
  }

  cityMap.invalidateSize();

  // Load bins
  try {
    const binsRes = await fetch("/api/smart-bins");
    const binsData = await binsRes.json();
    binsData.bins.forEach(b => {
      const isOver = b.status === "Overflowing" || b.fill_level_pct >= 85;
      const icon = L.divIcon({
        className: 'custom-pin',
        html: `<div style="background:${isOver ? '#f59e0b' : '#10b981'};color:white;padding:6px;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);"><i class="fa-solid fa-trash-can" style="font-size:12px;"></i></div>`
      });
      L.marker([b.latitude, b.longitude], { icon })
        .bindPopup(`<b>${b.bin_code}</b> (${b.bin_type})<br>${b.address}<br>Fill Level: <b>${b.fill_level_pct}%</b> (${b.status})`)
        .addTo(cityMap);
    });

    // Load active complaints
    const compRes = await fetch("/api/complaints");
    const compData = await compRes.json();
    compData.complaints.forEach(c => {
      const isResolved = c.status === "Resolved";
      const icon = L.divIcon({
        className: 'custom-pin',
        html: `<div style="background:${isResolved ? '#3b82f6' : '#ef4444'};color:white;padding:6px;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);"><i class="fa-solid ${isResolved ? 'fa-check' : 'fa-triangle-exclamation'}" style="font-size:12px;"></i></div>`
      });
      L.marker([c.latitude, c.longitude], { icon })
        .bindPopup(`<b>${c.id}</b> — ${c.category}<br>${c.address}<br>Severity: <b>${c.severity}</b> | Status: <b>${c.status}</b>`)
        .addTo(cityMap);
    });

  } catch (err) {
    console.error("City map load error", err);
  }
}

// ==========================================================================
// 4. Rewards Hub & Pune Civic Vouchers
// ==========================================================================

async function loadRewardsData() {
  try {
    // 1. Fetch catalog
    const catRes = await fetch("/api/rewards/catalog");
    const catData = await catRes.json();
    const catalogContainer = document.getElementById("vouchers-catalog-grid");

    catalogContainer.innerHTML = catData.catalog.map(v => `
      <div class="voucher-card">
        <div>
          <span class="badge badge-info">${v.partner}</span>
          <h4 class="mt-2 font-bold text-base">${v.title}</h4>
          <p class="text-xs text-muted mt-1">${v.benefit}</p>
          <p class="text-xs text-muted mt-2">${v.instructions}</p>
        </div>
        <div class="mt-3 flex justify-between items-center">
          <span class="voucher-cost">${v.cost} PTS</span>
          <button class="btn btn-sm btn-primary" onclick="redeemVoucher('${v.id}')">
            Redeem Voucher
          </button>
        </div>
      </div>
    `).join("");

    // 2. Fetch user vouchers & balance
    const userRes = await fetch(`/api/rewards/user/${state.userId}`);
    const userData = await userRes.json();
    state.userCredits = userData.credits_balance;
    updateHeaderCredits();

    const userVouchersContainer = document.getElementById("user-vouchers-list");
    if (!userData.vouchers || userData.vouchers.length === 0) {
      userVouchersContainer.innerHTML = `<p class="text-sm text-muted">You have no active redeemed vouchers yet. Redeem from above catalog!</p>`;
    } else {
      userVouchersContainer.innerHTML = userData.vouchers.map(uv => `
        <div class="card mb-2 p-3 bg-emerald-light border-emerald">
          <div class="flex justify-between items-center">
            <div>
              <strong>${uv.title}</strong>
              <div class="mono text-xs font-bold text-emerald-dark mt-1">Code: ${uv.code}</div>
              <span class="text-xs text-muted">Expires: ${uv.expires_at}</span>
            </div>
            <span class="badge badge-success">Active QR Ready</span>
          </div>
        </div>
      `).join("");
    }

    // 3. Transactions
    const txContainer = document.getElementById("transactions-list");
    txContainer.innerHTML = userData.transactions.map(t => `
      <div class="flex justify-between py-2 border-b text-xs">
        <div>
          <strong>${t.reason}</strong>
          <div class="text-muted">${t.created_at}</div>
        </div>
        <span class="font-bold ${t.transaction_type === 'CREDIT' ? 'text-emerald' : 'text-red'}">
          ${t.transaction_type === 'CREDIT' ? '+' : '-'}${t.amount} PTS
        </span>
      </div>
    `).join("");

    // 4. Leaderboard
    const lbRes = await fetch("/api/rewards/leaderboard");
    const lbData = await lbRes.json();
    document.getElementById("leaderboard-list").innerHTML = lbData.leaderboard.map(lb => `
      <div class="flex justify-between items-center py-2 border-b text-sm">
        <div class="flex items-center gap-2">
          <span class="font-bold text-primary">#${lb.rank}</span>
          <div>
            <strong>${lb.name}</strong>
            <div class="text-xs text-muted">${lb.area} • ${lb.badge}</div>
          </div>
        </div>
        <span class="font-bold text-gold">${lb.credits} PTS</span>
      </div>
    `).join("");

  } catch (err) {
    console.error("Rewards load error", err);
  }
}

async function redeemVoucher(rewardId) {
  if (!confirm(`Redeem this voucher with your Green Credits balance?`)) return;

  const fd = new FormData();
  fd.append("user_id", state.userId);
  fd.append("reward_id", rewardId);

  try {
    const res = await fetch("/api/rewards/redeem", { method: "POST", body: fd });
    const data = await res.json();
    if (data.success) {
      alert(`Success! Voucher generated!\nCode: ${data.voucher_code}\nPresent this code or QR at ticket counter.`);
      loadRewardsData();
    } else {
      alert("Redemption failed: " + (data.detail || "Insufficient credits"));
    }
  } catch (e) {
    alert("Network error redeeming voucher.");
  }
}

function updateHeaderCredits() {
  document.getElementById("header-credits-val").textContent = state.userCredits;
  const balEl = document.getElementById("rewards-balance-val");
  if (balEl) balEl.textContent = state.userCredits;
}

// ==========================================================================
// 5. Municipal Admin Portal
// ==========================================================================

async function loadAdminComplaints() {
  const status = document.getElementById("admin-filter-status").value;
  try {
    const res = await fetch(`/api/complaints?status=${status}`);
    const data = await res.json();
    const tbody = document.getElementById("admin-complaints-tbody");

    // Fetch workers list for assignment
    const wRes = await fetch("/api/workers");
    const wData = await wRes.json();
    const workersOptions = wData.workers.map(w => `<option value="${w.id}">${w.name} (${w.zone})</option>`).join("");

    tbody.innerHTML = data.complaints.map(c => `
      <tr>
        <td class="mono font-bold"><a href="javascript:void(0)" onclick="openForensicModal('${c.id}')" class="text-emerald hover:underline">${c.id}</a></td>
        <td><img src="${c.image_url}" onclick="openForensicModal('${c.id}')" class="w-12 h-12 object-cover rounded cursor-pointer" onerror="this.src='https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600'" /></td>
        <td>
          <div class="font-bold text-xs">${c.address}</div>
          <div class="text-xs text-muted">${c.ward_name}</div>
        </td>
        <td>${c.category}</td>
        <td><span class="badge ${getSeverityBadge(c.severity)}">${c.severity}</span></td>
        <td><span class="badge badge-info">${c.status}</span></td>
        <td>${c.worker_name || '<em>Unassigned</em>'}</td>
        <td>
          <div class="flex items-center gap-1">
            <button class="btn btn-sm btn-outline text-emerald" onclick="openForensicModal('${c.id}')" title="Forensic Waste Audit">
              <i class="fa-solid fa-file-waveform"></i> Audit
            </button>
            ${c.status !== 'Resolved' ? `
              <select id="assign-select-${c.id}" class="form-input-sm text-xs" style="max-width: 120px;">
                ${workersOptions}
              </select>
              <button class="btn btn-sm btn-primary" onclick="assignWorkerToComplaint('${c.id}')">Assign</button>
            ` : '<span class="text-emerald font-bold text-xs ml-1">✓ Cleared</span>'}
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Admin load error", err);
  }
}

async function assignWorkerToComplaint(complaintId) {
  const sel = document.getElementById(`assign-select-${complaintId}`);
  const workerId = sel.value;

  const fd = new FormData();
  fd.append("worker_id", workerId);

  try {
    const res = await fetch(`/api/complaints/${complaintId}/assign`, { method: "POST", body: fd });
    const data = await res.json();
    if (data.success) {
      alert(data.message);
      loadAdminComplaints();
    }
  } catch (e) {
    alert("Assignment error");
  }
}

// ==========================================================================
// 6. Sanitation Worker Dashboard
// ==========================================================================

async function loadWorkerDashboard() {
  const workerId = "WRK-101"; // Ramesh Shinde
  try {
    const res = await fetch(`/api/workers/${workerId}/tasks`);
    const data = await res.json();

    const tasksContainer = document.getElementById("worker-tasks-list");
    if (!data.active_tasks || data.active_tasks.length === 0) {
      tasksContainer.innerHTML = `<div class="card text-center p-4"><p>No pending cleanup orders assigned! Great job.</p></div>`;
    } else {
      tasksContainer.innerHTML = data.active_tasks.map(t => `
        <div class="card mb-3 p-3 border-l-4 border-l-emerald">
          <div class="flex justify-between items-start">
            <div>
              <span class="badge badge-warning">Stop #${t.sequence_order}</span>
              <h4 class="font-bold text-sm mt-1">${t.complaint_id} — ${t.category}</h4>
              <p class="text-xs text-muted"><i class="fa-solid fa-map-pin"></i> ${t.address}</p>
              <p class="text-xs font-semibold text-primary mt-1"><i class="fa-solid fa-wrench"></i> ${t.ai_recommendation || 'Standard cleanup'}</p>
            </div>
            <img src="${t.complaint_image}" class="w-16 h-16 object-cover rounded" />
          </div>
          <div class="mt-3 flex gap-2">
            <a href="https://www.google.com/maps/dir/?api=1&destination=${t.latitude},${t.longitude}" target="_blank" class="btn btn-sm btn-outline text-primary">
              <i class="fa-solid fa-location-arrow"></i> Navigate
            </a>
            <button class="btn btn-sm btn-primary" onclick="openResolveModal('${t.id}', '${t.complaint_id}')">
              <i class="fa-solid fa-check"></i> Complete & Upload Proof
            </button>
          </div>
        </div>
      `).join("");
    }

    // Init worker route map
    setTimeout(() => {
      if (!workerMap) {
        workerMap = L.map("worker-route-map").setView([18.5140, 73.8180], 15);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19 }).addTo(workerMap);
      }
      workerMap.invalidateSize();
      data.active_tasks.forEach(t => {
        L.marker([t.latitude, t.longitude])
          .bindPopup(`<b>Stop #${t.sequence_order}</b><br>${t.complaint_id}<br>${t.address}`)
          .addTo(workerMap);
      });
    }, 150);

  } catch (err) {
    console.error("Worker load error", err);
  }
}

async function optimizeWorkerRoute(workerId) {
  try {
    const res = await fetch(`/api/workers/${workerId}/optimize-route`, { method: "POST" });
    const data = await res.json();
    if (data.success) {
      alert(`Route Optimized using TSP Nearest-Neighbor!\nTotal route distance: ${data.total_distance_km} km for ${data.optimized_count} stops.`);
      loadWorkerDashboard();
    }
  } catch (e) {
    alert("Route optimization error");
  }
}

function openResolveModal(taskId, complaintId) {
  state.activeResolveTaskId = taskId;
  document.getElementById("modal-task-title").innerHTML = `<strong>Order:</strong> ${taskId} (Complaint #${complaintId})`;
  document.getElementById("resolve-modal").classList.remove("hidden");
}

function closeResolveModal() {
  document.getElementById("resolve-modal").classList.add("hidden");
  state.activeResolveTaskId = null;
}

async function submitTaskResolution() {
  if (!state.activeResolveTaskId) return;

  const fd = new FormData();
  fd.append("cleanup_notes", document.getElementById("resolve-notes").value);
  const fileInput = document.getElementById("resolve-after-photo");
  if (fileInput.files[0]) {
    fd.append("after_photo", fileInput.files[0]);
  }

  try {
    const res = await fetch(`/api/workers/WRK-101/tasks/${state.activeResolveTaskId}/resolve`, {
      method: "POST",
      body: fd
    });
    const data = await res.json();
    if (data.success) {
      alert("Order marked completed! Before & After verified and +25 bonus points awarded to citizen.");
      closeResolveModal();
      loadWorkerDashboard();
    }
  } catch (e) {
    alert("Error completing task");
  }
}

// ==========================================================================
// 7. DBSCAN Hotspots Prediction
// ==========================================================================

async function runHotspotsAnalysis() {
  const eps = document.getElementById("dbscan-eps").value;
  try {
    const res = await fetch(`/api/hotspots?eps_meters=${eps}`);
    const data = await res.json();

    const list = document.getElementById("hotspot-clusters-list");
    if (!data.clusters || data.clusters.length === 0) {
      list.innerHTML = `<p class="text-sm text-muted">No high-density clusters found within ${eps}m radius.</p>`;
    } else {
      list.innerHTML = data.clusters.map(c => `
        <div class="card mb-2 p-3 border-l-4 border-l-red">
          <div class="flex justify-between items-center">
            <div>
              <strong class="text-primary">${c.ward_name} Hotspot Cluster</strong>
              <div class="text-xs text-muted mt-1"><i class="fa-solid fa-crosshairs"></i> Centroid: ${c.center_lat}, ${c.center_lng} (Radius: ${c.radius_meters}m)</div>
              <p class="text-xs text-emerald-dark font-semibold mt-1">${c.recommended_action}</p>
            </div>
            <div class="text-right">
              <span class="badge ${c.risk_tier === 'Critical' ? 'badge-danger' : 'badge-warning'}">${c.risk_tier} Risk (${c.severity_score} PTS)</span>
              <div class="text-xs text-muted mt-1">${c.complaint_count} complaints</div>
            </div>
          </div>
        </div>
      `).join("");
    }

    // Render Chart.js
    if (data.ward_risk_distribution) {
      renderWardChart(data.ward_risk_distribution);
    }
  } catch (err) {
    console.error("Hotspots error", err);
  }
}

function renderWardChart(wardStats) {
  const ctx = document.getElementById("ward-risk-chart");
  if (!ctx) return;

  if (wardRiskChart) wardRiskChart.destroy();

  wardRiskChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: wardStats.map(w => w.ward_name),
      datasets: [
        {
          label: "Total Reports",
          data: wardStats.map(w => w.total_reports),
          backgroundColor: "#10b981"
        },
        {
          label: "High/Critical Severity",
          data: wardStats.map(w => w.high_risk_count),
          backgroundColor: "#ef4444"
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });
}

// ==========================================================================
// 8. Smart Bins MCLP Optimizer
// ==========================================================================

async function runMCLPOptimization() {
  const k = document.getElementById("mclp-k-input").value;
  const fd = new FormData();
  fd.append("k_bins", k);
  fd.append("coverage_radius_meters", 350.0);

  try {
    const res = await fetch("/api/smart-bins/optimize", { method: "POST", body: fd });
    const data = await res.json();

    document.getElementById("mclp-baseline-pct").textContent = `${data.baseline_coverage_pct}%`;
    document.getElementById("mclp-optimized-pct").textContent = `${data.optimized_coverage_pct}%`;
    document.getElementById("mclp-delta-pct").textContent = `+${data.coverage_improvement_pct}%`;

    const locList = document.getElementById("mclp-locations-list");
    locList.innerHTML = data.selected_locations.map(loc => `
      <div class="card mb-2 p-3 bg-emerald-light border-emerald">
        <div class="flex justify-between items-center">
          <div>
            <span class="badge badge-success">Rank #${loc.rank}</span>
            <strong class="ml-2">${loc.location_name}</strong>
            <div class="text-xs text-muted mt-1">${loc.ward_name} (${loc.latitude}, ${loc.longitude})</div>
            <div class="text-xs font-semibold text-emerald-dark mt-1">${loc.recommended_capacity}</div>
          </div>
          <div class="text-right">
            <span class="font-bold text-emerald">+${loc.additional_points_covered} New Points</span>
            <div class="text-xs text-muted">Covers ${loc.total_points_in_radius} Total</div>
          </div>
        </div>
      </div>
    `).join("");

  } catch (err) {
    console.error("MCLP error", err);
  }
}

// ==========================================================================
// 9. CleanBot AI Assistant (Powered by Sarvam AI)
// ==========================================================================

function toggleCleanBot() {
  const drawer = document.getElementById("cleanbot-drawer");
  drawer.classList.toggle("hidden");
}

function sendCleanBotPrompt(promptText) {
  document.getElementById("cleanbot-input").value = promptText;
  sendCleanBotMessage();
}

async function sendCleanBotMessage() {
  const input = document.getElementById("cleanbot-input");
  const msg = input.value.trim();
  if (!msg) return;

  const chatBody = document.getElementById("cleanbot-chat-body");

  // Append user bubble
  chatBody.innerHTML += `
    <div class="chat-bubble user">
      <p>${msg}</p>
    </div>
  `;
  input.value = "";
  chatBody.scrollTop = chatBody.scrollHeight;

  // Append typing indicator
  const typingId = `typing-${Date.now()}`;
  chatBody.innerHTML += `
    <div id="${typingId}" class="chat-bubble bot text-muted">
      <i class="fa-solid fa-spinner fa-spin"></i> CleanBot is thinking with Sarvam AI...
    </div>
  `;
  chatBody.scrollTop = chatBody.scrollHeight;

  try {
    const res = await fetch("/api/cleanbot/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msg,
        role: state.currentRole,
        history: state.cleanbotHistory
      })
    });
    const data = await res.json();

    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    chatBody.innerHTML += `
      <div class="chat-bubble bot">
        <p>${data.reply.replace(/\n/g, '<br>')}</p>
        <span class="mono text-xs text-muted block mt-1"><i class="fa-solid fa-sparkles text-emerald"></i> ${data.model}</span>
      </div>
    `;

    state.cleanbotHistory.push({ role: "user", content: msg });
    state.cleanbotHistory.push({ role: "assistant", content: data.reply });

  } catch (err) {
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    chatBody.innerHTML += `
      <div class="chat-bubble bot text-red">
        <p>Sorry, CleanBot experienced a connection issue. Please try again.</p>
      </div>
    `;
  }
  chatBody.scrollTop = chatBody.scrollHeight;
}

// ==========================================================================
// 10. City Pulse Stats
// ==========================================================================

async function loadCityStats() {
  try {
    const res = await fetch("/api/analytics/dashboard");
    const data = await res.json();
    document.getElementById("stat-total-complaints").textContent = data.summary.total_complaints;
    document.getElementById("stat-resolution-rate").textContent = `${data.summary.resolution_rate_pct}%`;
    document.getElementById("stat-active-bins").textContent = data.summary.monitored_bins;
  } catch (err) {
    console.warn("Analytics error", err);
  }
}

// ==========================================================================
// 11. Forensic Waste Audit Modal (Garbage-Vision v2.0)
// ==========================================================================

let activeForensicComplaint = null;

async function openForensicModal(complaintId) {
  try {
    const res = await fetch(`/api/complaints/${complaintId}`);
    if (!res.ok) throw new Error("Complaint not found");
    const data = await res.json();
    const c = data.complaint;
    const f = data.forensic_report || {};
    activeForensicComplaint = { ...c, forensic: f };

    // Fill IDs and titles
    document.getElementById("forensic-report-id").textContent = c.id;
    document.getElementById("forensic-report-title").textContent = `Forensic Waste Audit — ${c.address}`;

    // Fill photos
    const origImg = document.getElementById("forensic-orig-img");
    const annotatedImg = document.getElementById("forensic-annotated-img");
    const photoUrl = c.image_url || 'https://images.unsplash.com/photo-1530587191325-3db32d826c18?w=600';
    origImg.src = photoUrl;
    annotatedImg.src = photoUrl;

    // Render bounding boxes over annotated image
    const bboxContainer = document.getElementById("forensic-bounding-boxes-layer");
    bboxContainer.innerHTML = "";
    if (f.bounding_boxes && f.bounding_boxes.length > 0) {
      bboxContainer.innerHTML = f.bounding_boxes.map(b => {
        const isSup = b.stream === "SUP_VIOLATION";
        return `
          <div class="bbox-rect ${isSup ? 'sup-violation' : ''}" style="top:${b.box[0]}%; left:${b.box[1]}%; height:${b.box[2] - b.box[0]}%; width:${b.box[3] - b.box[1]}%;">
            <span class="bbox-tag">${b.id}. ${b.label} (${b.conf}%)</span>
          </div>
        `;
      }).join("");
    }

    // 7 Key Metric Cards
    document.getElementById("f-severity-val").textContent = f.severity_label || `HIGH ${f.severity_index || 65}`;
    document.getElementById("f-total-items-val").textContent = f.total_items || 14;
    document.getElementById("f-sup-val").textContent = f.sup_infractions !== undefined ? f.sup_infractions : 1;
    document.getElementById("f-load-val").textContent = `${f.estimated_load_kg || 4.23} kg`;
    document.getElementById("f-pieces-val").textContent = `${f.total_pieces || 24} pieces`;
    document.getElementById("f-coverage-val").textContent = `${f.frame_coverage_pct || 66.8}%`;
    document.getElementById("f-conf-val").textContent = `${f.mean_confidence_pct || 86}%`;
    document.getElementById("f-segregation-val").textContent = f.segregation_type || "SINGLE-STREAM";
    document.getElementById("f-seg-sub-val").textContent = f.segregation_label || "Dry Recyclable";

    // Dispatch Action Banner
    document.getElementById("f-dispatch-action-text").textContent = f.dispatch_action || "Single-stream accumulation — schedule routine collection.";

    // Waste Stream Split
    document.getElementById("f-stream-summary-title").textContent = `WASTE STREAM SPLIT (${f.total_pieces || 24} PIECES · ${f.estimated_load_kg || 4.23} kg)`;
    document.getElementById("f-stream-legend-text").textContent = `${f.segregation_label || 'Dry Recyclable'} — 100% · ${f.estimated_load_kg || 4.23} kg`;

    // Engine & Vision Audit Note
    document.getElementById("f-engine-text").textContent = f.engine || "On-device CV sweep (Garbage-Vision v2.0)";
    document.getElementById("f-audit-note-text").textContent = f.vision_audit_note || f.description || "Multi-band sweep of the frame isolated 14 artifact cluster(s) over 66.8% of the image. Streams present: DRY_RECYCLABLE.";

    // Itemized Inventory Table
    const tbody = document.getElementById("forensic-inventory-tbody");
    const countSpan = document.getElementById("f-itemized-count");
    const inventory = f.itemized_inventory || [];
    countSpan.textContent = `${inventory.length} Artifacts Identified`;

    tbody.innerHTML = inventory.map(item => `
      <tr>
        <td class="font-bold">${item.name}</td>
        <td>
          <span class="${item.stream === 'SUP_VIOLATION' ? 'stream-tag-red' : 'stream-tag-blue'}">
            ${item.stream}
          </span>
        </td>
        <td class="mono font-semibold">${item.resin_code}</td>
        <td>
          <span class="${item.sup_violation && item.sup_violation.includes('YES') ? 'text-red font-bold' : 'text-emerald font-semibold'}">
            ${item.sup_violation && item.sup_violation.includes('YES') ? '⚠️ ' + item.sup_violation : '✓ ' + item.sup_violation}
          </span>
        </td>
        <td class="text-emerald font-semibold">${item.brand}</td>
        <td class="font-bold text-emerald">${item.confidence}</td>
      </tr>
    `).join("");

    // Status dropdown
    const statusSel = document.getElementById("forensic-status-select");
    statusSel.value = c.status;

    // Show Modal
    document.getElementById("forensic-modal").classList.remove("hidden");

  } catch (err) {
    alert("Error loading forensic report: " + err.message);
  }
}

function closeForensicModal() {
  document.getElementById("forensic-modal").classList.add("hidden");
  activeForensicComplaint = null;
}

async function deleteCurrentForensicReport() {
  if (!activeForensicComplaint) return;
  if (!confirm(`Are you sure you want to delete forensic report ${activeForensicComplaint.id}?`)) return;

  try {
    const res = await fetch(`/api/complaints/${activeForensicComplaint.id}`, { method: "DELETE" });
    const data = await res.json();
    if (data.success) {
      alert(`Report ${activeForensicComplaint.id} deleted.`);
      closeForensicModal();
      loadComplaintsList();
      loadAdminComplaints();
    }
  } catch (e) {
    alert("Delete failed.");
  }
}

async function updateForensicStatus() {
  if (!activeForensicComplaint) return;
  const newStatus = document.getElementById("forensic-status-select").value;

  const fd = new FormData();
  fd.append("new_status", newStatus);
  fd.append("notes", `Status updated to ${newStatus} from Forensic Audit viewer.`);

  try {
    const res = await fetch(`/api/complaints/${activeForensicComplaint.id}/status`, { method: "PATCH", body: fd });
    const data = await res.json();
    if (data.success) {
      alert(`Status updated to ${newStatus}`);
      activeForensicComplaint.status = newStatus;
      loadComplaintsList();
      loadAdminComplaints();
    }
  } catch (e) {
    alert("Status update error");
  }
}

function downloadForensicJson() {
  if (!activeForensicComplaint) return;
  const jsonStr = JSON.stringify(activeForensicComplaint, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `forensic_audit_${activeForensicComplaint.id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadForensicCsv() {
  if (!activeForensicComplaint) return;
  const inv = activeForensicComplaint.forensic?.itemized_inventory || [];
  let csv = "Item Name,Stream,Material Resin,SUP Violation,Brand EPR,Confidence\n";
  inv.forEach(i => {
    csv += `"${i.name}","${i.stream}","${i.resin_code}","${i.sup_violation}","${i.brand}","${i.confidence}"\n`;
  });
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `forensic_inventory_${activeForensicComplaint.id}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ==========================================================================
// 12. Live Toy Truck & MCLP Route Simulation
// ==========================================================================

let truckMap = null;
let truckMarker = null;
let truckRoutePolyline = null;
let truckRunning = false;
let truckSpeedMultiplier = 1; // 1x, 3x, 8x
let truckAnimationId = null;
let truckWaypoints = [];
let truckCurrentWaypointIndex = 0;
let truckPayloadKg = 0;
let truckBinsCleared = 0;

const MCLP_TRUCK_STATIONS = [
  { name: "Swargate Central PMC Depot", lat: 18.5018, lng: 73.8586, isDepot: true },
  { name: "Cummins College Road Smart Bin", lat: 18.4905, lng: 73.8188, waste: 95 },
  { name: "Garware College Metro Smart Bin", lat: 18.5122, lng: 73.8340, waste: 110 },
  { name: "Deccan Gymkhana Bus Terminal Bin", lat: 18.5165, lng: 73.8405, waste: 125 },
  { name: "Pune University Circle / SPPU Bin", lat: 18.5412, lng: 73.8290, waste: 90 },
  { name: "Swargate Central PMC Depot (Return)", lat: 18.5018, lng: 73.8586, isDepot: true }
];

function initAdminTruckMap() {
  const container = document.getElementById("admin-truck-map");
  if (!container) return;

  if (!truckMap) {
    truckMap = L.map("admin-truck-map").setView([18.5165, 73.8405], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors"
    }).addTo(truckMap);

    // Precompute smooth interpolated waypoints between all stations
    truckWaypoints = [];
    for (let i = 0; i < MCLP_TRUCK_STATIONS.length - 1; i++) {
      const p1 = MCLP_TRUCK_STATIONS[i];
      const p2 = MCLP_TRUCK_STATIONS[i + 1];
      const steps = 40; // 40 interpolation steps per leg
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        truckWaypoints.push({
          lat: p1.lat + (p2.lat - p1.lat) * t,
          lng: p1.lng + (p2.lng - p1.lng) * t,
          legIndex: i,
          station: s === steps ? p2 : null
        });
      }
    }

    // Draw route line
    const routeCoords = MCLP_TRUCK_STATIONS.map(s => [s.lat, s.lng]);
    truckRoutePolyline = L.polyline(routeCoords, {
      color: "#10b981",
      weight: 5,
      opacity: 0.8,
      dashArray: "10, 10"
    }).addTo(truckMap);

    // Place station markers
    MCLP_TRUCK_STATIONS.forEach((s, idx) => {
      if (idx === 0 || idx === MCLP_TRUCK_STATIONS.length - 1) {
        L.marker([s.lat, s.lng], {
          icon: L.divIcon({
            className: "depot-pin",
            html: `<div style="background:#0b3b2b;color:#10b981;border:2px solid white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);"><i class="fa-solid fa-warehouse" style="font-size:14px;"></i></div>`
          })
        }).bindPopup(`<b>${s.name}</b><br>PMC Central Dispatch Hub`).addTo(truckMap);
      } else {
        L.marker([s.lat, s.lng], {
          icon: L.divIcon({
            className: "mclp-bin-pin",
            html: `<div id="mclp-marker-${idx}" style="background:#f59e0b;color:white;border:2px solid white;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);"><i class="fa-solid fa-trash-can" style="font-size:13px;"></i></div>`
          })
        }).bindPopup(`<b>Stop #${idx}: ${s.name}</b><br>Target: Collect ${s.waste} kg`).addTo(truckMap);
      }
    });

    // Create animated Toy Truck marker
    const truckIcon = L.divIcon({
      className: "toy-truck-pin",
      html: `<div id="toy-truck-icon" class="toy-truck-marker truck-pulse"><i class="fa-solid fa-truck"></i></div>`
    });

    truckMarker = L.marker([truckWaypoints[0].lat, truckWaypoints[0].lng], { icon: truckIcon }).addTo(truckMap);
    truckMarker.bindPopup("<b>Smart Garbage Truck PMC-EV-01</b><br>Autonomous MCLP Collection Unit").openPopup();
  }

  truckMap.invalidateSize();
}

function toggleTruckSimulation() {
  truckRunning = !truckRunning;
  const btn = document.getElementById("btn-truck-play");

  if (truckRunning) {
    btn.innerHTML = `<i class="fa-solid fa-pause"></i> Pause Truck`;
    btn.classList.remove("btn-primary");
    btn.classList.add("btn-warning");
    runTruckStep();
  } else {
    btn.innerHTML = `<i class="fa-solid fa-play"></i> Resume Truck`;
    btn.classList.remove("btn-warning");
    btn.classList.add("btn-primary");
    if (truckAnimationId) clearTimeout(truckAnimationId);
  }
}

function setTruckSpeed(mult) {
  truckSpeedMultiplier = mult;
  document.querySelectorAll(".speed-btn").forEach(b => {
    b.classList.toggle("active", parseInt(b.dataset.speed) === mult);
  });
  const speedDisplay = mult === 8 ? "120 km/h (Turbo)" : mult === 3 ? "72 km/h (Fast)" : "48 km/h (Normal)";
  document.getElementById("truck-speed-display").textContent = speedDisplay;
}

function runTruckStep() {
  if (!truckRunning) return;

  if (truckCurrentWaypointIndex >= truckWaypoints.length - 1) {
    // Finished full tour
    document.getElementById("truck-status-text").textContent = "Tour Completed! All MCLP Smart Bins Collected.";
    document.getElementById("btn-truck-play").innerHTML = `<i class="fa-solid fa-rotate-left"></i> Restart Route`;
    truckRunning = false;
    return;
  }

  truckCurrentWaypointIndex++;
  const wp = truckWaypoints[truckCurrentWaypointIndex];
  truckMarker.setLatLng([wp.lat, wp.lng]);

  const targetStation = MCLP_TRUCK_STATIONS[wp.legIndex + 1];
  let delay = Math.max(10, Math.floor(50 / truckSpeedMultiplier));

  if (wp.station && !wp.station.isDepot) {
    // Truck reached an MCLP Smart Bin Station!
    truckBinsCleared++;
    truckPayloadKg += wp.station.waste || 90;

    document.getElementById("truck-status-text").textContent = `Emptying Bin at ${wp.station.name} (+${wp.station.waste} kg)...`;
    document.getElementById("truck-payload-display").textContent = `${truckPayloadKg} kg / 1,500 kg`;
    document.getElementById("truck-bins-display").textContent = `${truckBinsCleared} / 4`;

    const markerEl = document.getElementById(`mclp-marker-${wp.legIndex + 1}`);
    if (markerEl) {
      markerEl.style.background = "#10b981";
      markerEl.innerHTML = `<i class="fa-solid fa-check" style="font-size:13px;"></i>`;
    }

    // Brief collection stop
    delay = Math.floor(1000 / truckSpeedMultiplier);
  } else {
    document.getElementById("truck-status-text").textContent = `En Route to ${targetStation.name}...`;
  }

  truckAnimationId = setTimeout(runTruckStep, delay);
}

function resetTruckSimulation() {
  truckRunning = false;
  if (truckAnimationId) clearTimeout(truckAnimationId);
  truckCurrentWaypointIndex = 0;
  truckPayloadKg = 0;
  truckBinsCleared = 0;

  if (truckMarker && truckWaypoints.length > 0) {
    truckMarker.setLatLng([truckWaypoints[0].lat, truckWaypoints[0].lng]);
  }

  document.getElementById("btn-truck-play").innerHTML = `<i class="fa-solid fa-play"></i> Start Truck Route`;
  document.getElementById("btn-truck-play").classList.remove("btn-warning");
  document.getElementById("btn-truck-play").classList.add("btn-primary");

  document.getElementById("truck-status-text").textContent = "Ready at Swargate Depot";
  document.getElementById("truck-payload-display").textContent = "0 kg / 1,500 kg";
  document.getElementById("truck-bins-display").textContent = "0 / 4";

  // Reset station markers to yellow
  for (let i = 1; i <= 4; i++) {
    const markerEl = document.getElementById(`mclp-marker-${i}`);
    if (markerEl) {
      markerEl.style.background = "#f59e0b";
      markerEl.innerHTML = `<i class="fa-solid fa-trash-can" style="font-size:13px;"></i>`;
    }
  }
}
