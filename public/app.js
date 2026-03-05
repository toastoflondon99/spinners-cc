/* ── Spinners Cycling Club — App ── */

const API = "";

// ── State ──
let currentRider = null;
let allRiders = [];
let stats = null;
let trainingData = null;
let allRides = [];
let currentTab = "dashboard";
let pendingDistance = 110;
let pendingFitness = "intermediate";

// ── Init ──
async function init() {
  initTheme();
  try {
    const res = await fetch(`${API}/api/index`);
    allRiders = await res.json();
  } catch (e) {
    console.error("Failed to load riders", e);
    allRiders = [];
  }
  renderLogin();
}

// ── Theme ──
function initTheme() {
  const root = document.documentElement;
  let theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  root.setAttribute("data-theme", theme);

  const toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    toggle.addEventListener("click", () => {
      theme = theme === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", theme);
      toggle.innerHTML = theme === "dark"
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    });
  }
}

// ── Login ──
function renderLogin() {
  const grid = document.getElementById("rider-grid");
  if (!grid) return;

  const sorted = [...allRiders].sort((a, b) => a.name.localeCompare(b.name));
  grid.innerHTML = sorted.map(r => {
    const initials = r.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
    return `<button class="rider-select-btn" onclick="selectRider(${r.id})">
      <span class="rider-avatar">${escHtml(initials)}</span>
      ${escHtml(r.name)}
    </button>`;
  }).join("");
}

async function selectRider(id) {
  try {
    const res = await fetch(`${API}/api/index/rider/${id}`);
    currentRider = await res.json();
  } catch (e) {
    console.error("Failed to select rider", e);
    return;
  }

  document.getElementById("login-screen").style.display = "none";
  document.getElementById("app").style.display = "block";
  document.getElementById("bottom-nav").style.display = "flex";

  const initials = currentRider.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  document.getElementById("header-avatar").textContent = initials;
  document.getElementById("header-name").textContent = currentRider.name.split(" ")[0];

  const targetEl = document.getElementById("countdown-target");
  if (targetEl) targetEl.textContent = currentRider.target_distance + "km target";

  pendingDistance = currentRider.target_distance;
  pendingFitness = currentRider.fitness_level;

  updateCountdown();
  loadDashboard();
}

function logout() {
  currentRider = null;
  document.getElementById("login-screen").style.display = "flex";
  document.getElementById("app").style.display = "none";
  document.getElementById("bottom-nav").style.display = "none";
  switchTab("dashboard");
}

// ── Countdown ──
function updateCountdown() {
  const eventDate = new Date("2026-04-12T06:00:00+10:00");
  const now = new Date();
  const diff = eventDate - now;
  const days = Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
  const el = document.getElementById("countdown-days");
  if (el) el.textContent = days + " days to go";
}

// ── Tab switching ──
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));

  const tabEl = document.getElementById(`tab-${tab}`);
  if (tabEl) {
    tabEl.style.display = "block";
    tabEl.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--color-text-faint)">Loading...</div>';
  }

  const navEl = document.querySelector(`.nav-item[data-tab="${tab}"]`);
  if (navEl) navEl.classList.add("active");

  switch (tab) {
    case "dashboard": loadDashboard(); break;
    case "training": loadTraining(); break;
    case "rides": loadRides(); break;
    case "group": loadGroup(); break;
  }
}

// ── Dashboard ──
async function loadDashboard() {
  try {
    const [statsRes, ridesRes] = await Promise.all([
      fetch(`${API}/api/stats`),
      fetch(`${API}/api/rides?rider_id=${currentRider.id}`)
    ]);
    stats = await statsRes.json();
    const myRides = await ridesRes.json();

    const myStats = stats.rider_stats.find(r => r.id === currentRider.id) || {};
    const totalGroupRides = stats.rider_stats.reduce((s, r) => s + r.total_rides, 0);
    const totalGroupKm = stats.rider_stats.reduce((s, r) => s + r.total_km, 0);
    const activeRiders = stats.rider_stats.filter(r => r.total_rides > 0).length;

    const container = document.getElementById("tab-dashboard");
    container.innerHTML = `
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Your Rides</div>
          <div class="stat-value green">${myStats.total_rides || 0}</div>
          <div class="stat-sub">${(myStats.total_km || 0).toFixed(0)}km total</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Your Target</div>
          <div class="stat-value orange">${currentRider.target_distance}km</div>
          <div class="stat-sub">${currentRider.fitness_level} level</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Group Rides</div>
          <div class="stat-value blue">${totalGroupRides}</div>
          <div class="stat-sub">${totalGroupKm.toFixed(0)}km combined</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Active Riders</div>
          <div class="stat-value green">${activeRiders}</div>
          <div class="stat-sub">of ${stats.total_riders} Spinners</div>
        </div>
      </div>

      ${stats.this_week_riders.length > 0 ? `
        <div class="card">
          <div class="card-header">
            <span class="card-title">Rode this week</span>
            <span style="font-size:var(--text-xs);color:var(--color-primary);font-weight:600">${stats.this_week_riders.length} riders</span>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:var(--space-2)">
            ${stats.this_week_riders.map(r => {
              const init = r.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
              return `<span style="display:flex;align-items:center;gap:6px;font-size:var(--text-xs);background:var(--color-primary-muted);padding:4px 10px;border-radius:var(--radius-full)">
                <span class="rider-avatar" style="width:18px;height:18px;font-size:9px">${init}</span>
                ${escHtml(r.name.split(" ")[0])}
              </span>`;
            }).join("")}
          </div>
        </div>
      ` : ""}

      <div class="card">
        <div class="card-header">
          <span class="card-title">Your Recent Rides</span>
          <button class="btn btn-sm btn-primary" onclick="openRideModal()">+ Log Ride</button>
        </div>
        ${myRides.length === 0
          ? `<div class="empty-state">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg>
              <p>No rides logged yet. Hit "Log Ride" to get started.</p>
            </div>`
          : `<div>${myRides.slice(0, 5).map(r => renderRideItem(r)).join("")}</div>`
        }
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Leaderboard — Total KM</span>
        </div>
        <ul class="rider-list">
          ${stats.rider_stats.filter(r => r.total_km > 0).slice(0, 10).map((r, i) => `
            <li class="rider-row">
              <span class="rider-rank ${i < 3 ? "top-3" : ""}">${i + 1}</span>
              <div class="rider-info">
                <div class="rider-name">${escHtml(r.name)}</div>
                <div class="rider-meta">${r.target_distance}km target · ${r.ride_days} ride days</div>
              </div>
              <div style="text-align:right">
                <div class="rider-km">${r.total_km.toFixed(0)}km</div>
                <div class="rider-rides">${r.total_rides} rides</div>
              </div>
            </li>
          `).join("")}
          ${stats.rider_stats.filter(r => r.total_km > 0).length === 0
            ? '<li style="padding:var(--space-4);text-align:center;color:var(--color-text-faint);font-size:var(--text-xs)">No rides logged yet — be the first!</li>'
            : ""}
        </ul>
      </div>
    `;
  } catch (e) {
    console.error("Dashboard load error", e);
    document.getElementById("tab-dashboard").innerHTML = '<div class="empty-state"><p>Failed to load dashboard. Try refreshing.</p></div>';
  }
}

// ── Training Plan ──
async function loadTraining() {
  const container = document.getElementById("tab-training");
  try {
    const res = await fetch(`${API}/api/training/${currentRider.id}`);
    trainingData = await res.json();

    const completedSet = new Set(trainingData.completed.map(c => `${c.week}-${c.day}`));
    const dayNames = { mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday", fri: "Friday", sat: "Saturday", sun: "Sunday" };

    let html = `
      <div class="section-header">
        <h2 class="section-title">Your Training Plan</h2>
        <button class="btn btn-sm btn-ghost" onclick="openSettings()">⚙ Settings</button>
      </div>
      <div style="display:flex;gap:var(--space-4);margin-bottom:var(--space-6);flex-wrap:wrap">
        <div style="font-size:var(--text-xs);color:var(--color-text-muted)">
          Target: <strong style="color:var(--color-primary)">${trainingData.target_distance}km</strong>
        </div>
        <div style="font-size:var(--text-xs);color:var(--color-text-muted)">
          Level: <strong style="color:var(--color-text)">${trainingData.fitness_level}</strong>
        </div>
        <div style="font-size:var(--text-xs);color:var(--color-text-muted)">
          Weeks to event: <strong style="color:var(--color-orange)">${trainingData.weeks_to_event}</strong>
        </div>
      </div>
    `;

    for (const week of trainingData.plan) {
      const dayEntries = Object.entries(week.days);
      const completedCount = dayEntries.filter(([k]) => completedSet.has(`${week.week}-${k}`)).length;

      html += `
        <div class="training-week">
          <div class="week-header">
            <div>
              <div class="week-label">Week ${week.week}</div>
              <div class="week-theme">${escHtml(week.theme)}</div>
            </div>
            <div class="week-progress">${completedCount}/${dayEntries.length}</div>
          </div>
      `;

      for (const [dayKey, day] of dayEntries) {
        const isCompleted = completedSet.has(`${week.week}-${dayKey}`);
        const isEvent = day.type === "event";

        html += `
          <div class="training-day ${isCompleted ? "completed" : ""} ${isEvent ? "event" : ""}"
               onclick="toggleTraining(${week.week}, '${dayKey}', ${isCompleted})">
            <div class="day-check">
              ${isCompleted ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' : ""}
            </div>
            <div class="day-content">
              <div class="day-label">${dayNames[dayKey] || dayKey}</div>
              <div class="day-title">${escHtml(day.title)}</div>
              <div class="day-desc">${escHtml(day.description)}</div>
              <div class="day-badges">
                ${day.duration ? `<span class="badge duration">${escHtml(day.duration)}</span>` : ""}
                ${day.zone ? `<span class="badge zone">${escHtml(day.zone)}</span>` : ""}
                ${day.type ? `<span class="badge type-${day.type}">${escHtml(day.type)}</span>` : ""}
              </div>
            </div>
          </div>
        `;
      }

      html += `</div>`;
    }

    html += `
      <div class="coottha-card">
        <div class="card-header">
          <span class="card-title">Mt Coot-tha — The Big Climb</span>
        </div>
        <div class="coottha-stats">
          <div>
            <div class="coottha-stat-label">Distance</div>
            <div class="coottha-stat-value">2km</div>
          </div>
          <div>
            <div class="coottha-stat-label">Gradient</div>
            <div class="coottha-stat-value">9%</div>
          </div>
          <div>
            <div class="coottha-stat-label">At km</div>
            <div class="coottha-stat-value">~67</div>
          </div>
        </div>
        <ul class="tip-list">
          ${trainingData.coottha.tips.map(t => `<li class="tip-item">${escHtml(t)}</li>`).join("")}
        </ul>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Race Day Nutrition</span></div>
        <ul class="tip-list">
          ${trainingData.nutrition.race_day.map(t => `<li class="tip-item">${escHtml(t)}</li>`).join("")}
        </ul>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Training Nutrition</span></div>
        <ul class="tip-list">
          ${trainingData.nutrition.training.map(t => `<li class="tip-item">${escHtml(t)}</li>`).join("")}
        </ul>
      </div>
    `;

    container.innerHTML = html;
  } catch (e) {
    console.error("Training load error", e);
    container.innerHTML = '<div class="empty-state"><p>Failed to load training plan. Try refreshing.</p></div>';
  }
}

async function toggleTraining(week, dayKey, isCompleted) {
  if (!currentRider) return;
  try {
    if (isCompleted) {
      await fetch(`${API}/api/training/complete?rider_id=${currentRider.id}&week_number=${week}&day_key=${dayKey}`, { method: "DELETE" });
    } else {
      await fetch(`${API}/api/training/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rider_id: currentRider.id, week_number: week, day_key: dayKey })
      });
    }
    loadTraining();
  } catch (e) {
    console.error("Toggle training error", e);
  }
}

// ── Rides ──
async function loadRides() {
  const container = document.getElementById("tab-rides");
  try {
    const [allRes, myRes] = await Promise.all([
      fetch(`${API}/api/rides`),
      fetch(`${API}/api/rides?rider_id=${currentRider.id}`)
    ]);
    allRides = await allRes.json();
    const myRides = await myRes.json();

    container.innerHTML = `
      <div class="section-header">
        <h2 class="section-title">Ride Log</h2>
        <button class="btn btn-sm btn-primary" onclick="openRideModal()">+ Log Ride</button>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Your Rides</span></div>
        ${myRides.length === 0
          ? '<div class="empty-state"><p>No rides yet. Get out there!</p></div>'
          : `<div>${myRides.map(r => renderRideItem(r, true)).join("")}</div>`
        }
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">All Spinners Activity</span></div>
        ${allRides.length === 0
          ? '<div class="empty-state"><p>No rides logged by anyone yet.</p></div>'
          : `<div>${allRides.slice(0, 20).map(r => renderRideItem(r)).join("")}</div>`
        }
      </div>
    `;
  } catch (e) {
    console.error("Rides load error", e);
    container.innerHTML = '<div class="empty-state"><p>Failed to load rides.</p></div>';
  }
}

function renderRideItem(ride, showDelete = false) {
  const typeIcon = ride.ride_type === "group" ? "🚴‍♂️" : ride.ride_type === "race" ? "🏆" : "🚲";
  const typeClass = ride.ride_type || "solo";
  const dateStr = formatDate(ride.ride_date);
  const speed = ride.duration_mins && ride.duration_mins > 0 ? (ride.distance_km / (ride.duration_mins / 60)).toFixed(1) : null;

  return `
    <div class="ride-item">
      <div class="ride-icon ${typeClass}">${typeIcon}</div>
      <div class="ride-details">
        <div class="ride-title">${escHtml(ride.rider_name || "")} — ${ride.distance_km}km</div>
        <div class="ride-subtitle">
          <span class="ride-stat">${dateStr}</span>
          ${ride.duration_mins ? `<span class="ride-stat">${formatDuration(ride.duration_mins)}</span>` : ""}
          ${speed ? `<span class="ride-stat">${speed} km/h avg</span>` : ""}
        </div>
        ${ride.notes ? `<div style="font-size:var(--text-xs);color:var(--color-text-faint);margin-top:4px">"${escHtml(ride.notes)}"</div>` : ""}
      </div>
      ${showDelete ? `<button class="btn btn-sm btn-ghost" onclick="deleteRide(${ride.id})" style="flex-shrink:0;color:var(--color-red)">✕</button>` : ""}
    </div>
  `;
}

// ── Group ──
async function loadGroup() {
  const container = document.getElementById("tab-group");
  try {
    const res = await fetch(`${API}/api/stats`);
    stats = await res.json();

    const sorted = [...stats.rider_stats].sort((a, b) => b.total_km - a.total_km);

    container.innerHTML = `
      <div class="section-header">
        <h2 class="section-title">The Spinners</h2>
        <span style="font-size:var(--text-xs);color:var(--color-text-muted)">${stats.total_riders} riders</span>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total Group KM</div>
          <div class="stat-value green">${sorted.reduce((s, r) => s + r.total_km, 0).toFixed(0)}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Rides</div>
          <div class="stat-value blue">${sorted.reduce((s, r) => s + r.total_rides, 0)}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">All Riders</span>
        </div>
        <ul class="rider-list">
          ${sorted.map((r, i) => `
            <li class="rider-row">
              <span class="rider-rank ${i < 3 && r.total_km > 0 ? "top-3" : ""}">${i + 1}</span>
              <div class="rider-info">
                <div class="rider-name">${escHtml(r.name)} ${r.id === currentRider.id ? '<span style="color:var(--color-primary);font-size:var(--text-xs)">(you)</span>' : ""}</div>
                <div class="rider-meta">
                  ${r.target_distance}km · ${r.fitness_level}
                  ${r.last_ride ? ` · Last ride: ${formatDate(r.last_ride)}` : " · No rides yet"}
                </div>
              </div>
              <div style="text-align:right">
                <div class="rider-km">${r.total_km.toFixed(0)}km</div>
                <div class="rider-rides">${r.total_rides} rides</div>
              </div>
            </li>
          `).join("")}
        </ul>
      </div>
    `;
  } catch (e) {
    console.error("Group load error", e);
    container.innerHTML = '<div class="empty-state"><p>Failed to load group data.</p></div>';
  }
}

// ── Ride Modal ──
function openRideModal() {
  const today = new Date().toISOString().split("T")[0];
  document.getElementById("ride-date").value = today;
  document.getElementById("ride-distance").value = "";
  document.getElementById("ride-duration").value = "";
  document.getElementById("ride-type").value = "group";
  document.getElementById("ride-notes").value = "";
  document.getElementById("ride-modal").classList.add("active");
}

function closeRideModal() {
  document.getElementById("ride-modal").classList.remove("active");
}

async function submitRide() {
  const data = {
    rider_id: currentRider.id,
    ride_date: document.getElementById("ride-date").value,
    distance_km: parseFloat(document.getElementById("ride-distance").value) || 0,
    duration_mins: parseInt(document.getElementById("ride-duration").value) || null,
    ride_type: document.getElementById("ride-type").value,
    notes: document.getElementById("ride-notes").value
  };

  if (!data.ride_date || data.distance_km <= 0) {
    return;
  }

  try {
    await fetch(`${API}/api/rides`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    closeRideModal();
    switchTab(currentTab);
  } catch (e) {
    console.error("Submit ride error", e);
  }
}

async function deleteRide(id) {
  try {
    await fetch(`${API}/api/rides/${id}`, { method: "DELETE" });
    loadRides();
  } catch (e) {
    console.error("Delete ride error", e);
  }
}

// ── Settings Modal ──
function openSettings() {
  pendingDistance = currentRider.target_distance;
  pendingFitness = currentRider.fitness_level;
  updatePillToggles();
  document.getElementById("settings-modal").classList.add("active");
}

function closeSettings() {
  document.getElementById("settings-modal").classList.remove("active");
}

function setDistance(val) {
  pendingDistance = val;
  updatePillToggles();
}

function setFitness(val) {
  pendingFitness = val;
  updatePillToggles();
}

function updatePillToggles() {
  document.querySelectorAll("#distance-toggle .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.val) === pendingDistance);
  });
  document.querySelectorAll("#fitness-toggle .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.val === pendingFitness);
  });
}

async function saveSettings() {
  try {
    const res = await fetch(`${API}/api/index/rider/${currentRider.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_distance: pendingDistance, fitness_level: pendingFitness })
    });
    currentRider = await res.json();
    document.getElementById("countdown-target").textContent = currentRider.target_distance + "km target";
    closeSettings();
    loadTraining();
  } catch (e) {
    console.error("Save settings error", e);
  }
}

// ── Helpers ──
function escHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-AU", { day: "numeric", month: "short" });
  } catch {
    return dateStr;
  }
}

function formatDuration(mins) {
  if (!mins) return "";
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

// Close modals on overlay click
document.getElementById("ride-modal").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeRideModal();
});
document.getElementById("settings-modal").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) closeSettings();
});

// Boot
init();
