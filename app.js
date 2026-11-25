/* LEONIDA LIVE — GTA VI × Flagsmith Flag Command Center
   Flip a flag. Change Vice City. Instantly. No patch. No restart.

   Three modes, same UI:
   1. MOCK API  — talks to mock/server.py (http://localhost:8001) when reachable
   2. LOCAL     — built-in seed + localStorage (always works, even offline / in preview)
   3. REAL      — official Flagsmith JS SDK (flagsmith.init + onChange) when you paste a key

   The Flagsmith SDK integration pattern (see connectRealFlagsmith below):
     flagsmith.init({ environmentID, api, cacheFlags:true, onChange })
     flagsmith.hasFeature('leonida_expansion') / flagsmith.getValue('double_xp_weekend')
*/
"use strict";

/* ---------- Seed (mirrors seed-flags.json — used for LOCAL mode) ---------- */
const SEED = [
  { name:"leonida_expansion", label:"Leonida Expansion", icon:"🗺️", category:"World", rollout:100,
    description:"Unlock the Leonida Keys & Port Gellhorn. New islands, new heists, zero app update.",
    affects:"Map: Keys + Port Gellhorn appear", values:{production:false, staging:true, dev:true} },
  { name:"neon_nights_event", label:"Neon Nights Event", icon:"🌃", category:"Event", rollout:100,
    description:"Vice City Neon Nights weekend. Clubs open, skyline lit, double cash on races.",
    affects:"Map: night mode + neon glow", values:{production:false, staging:true, dev:false} },
  { name:"hurricane_ian", label:"Hurricane Ian", icon:"🌪️", category:"World", rollout:100,
    description:"Dynamic hurricane weather rolls into Leonida. Rain, wind, flooded streets.",
    affects:"Map: rain + storm overlay", values:{production:false, staging:false, dev:true} },
  { name:"double_xp_weekend", label:"Double XP Weekend", icon:"⭐", category:"Economy", rollout:100,
    description:"2× XP and cash across all Online modes. The classic live-ops lever.",
    affects:"Stats: XP multiplier ×2", values:{production:false, staging:true, dev:true} },
  { name:"ps5_beta_access", label:"PS5 Beta Access", icon:"🎮", category:"Platform", rollout:25,
    description:"PS5-exclusive beta: 4K/120Hz, DualSense haptics, 3D audio. Invite-only rollout.",
    affects:"Badge: 4K/120Hz + player count", values:{production:false, staging:true, dev:true} },
  { name:"police_pursuit_ai", label:"Police Pursuit AI", icon:"🚔", category:"Gameplay", rollout:100,
    description:"Smarter cops. Helicopters, roadblocks and a 5-star wanted system that actually hunts.",
    affects:"Map: police cars + wanted stars", values:{production:false, staging:false, dev:true} },
  { name:"lowrider_culture_pack", label:"Lowrider Culture Pack", icon:"🚗", category:"Content", rollout:100,
    description:"Lowrider car meet at Ocean Drive. Hydraulics, neon underglow, new paint jobs.",
    affects:"Map: car meet marker", values:{production:false, staging:true, dev:false} },
  { name:"crossplay_enabled", label:"Crossplay", icon:"🔗", category:"Platform", rollout:50,
    description:"PS5 ↔ Xbox ↔ PC crossplay. One lobby, every platform, instant matchmaking.",
    affects:"Stats: players online ×3", values:{production:false, staging:true, dev:true} },
  { name:"new_weapon_smg", label:"Silenced SMG Drop", icon:"🔫", category:"Content", rollout:100,
    description:"New weapon drop: suppressed SMG with custom attachments. No patch needed.",
    affects:"Loadout: weapon appears", values:{production:false, staging:false, dev:true} },
  { name:"traffic_density_high", label:"Rush Hour Traffic", icon:"🚦", category:"Gameplay", rollout:100,
    description:"High-density traffic AI. Vice City feels alive — and impossible to drive through.",
    affects:"Map: traffic speed + density", values:{production:false, staging:true, dev:true} },
];

const MOCK_API = "http://localhost:8001";
const LS_KEY = "leonida_state_v1";
const LS_FS = "leonida_flagsmith_cfg";

/* ---------- State ---------- */
let env = "production";
let flags = [];            // [{name,label,icon,category,rollout,description,affects,enabled,environment}]
let events = [];           // [{ts,flag,enabled,environment,actor}]
let mode = "local";        // local | mock | real
let focusedIdx = 0;
let lastFlip = null;
let trafficTimer = null;

/* ---------- DOM ---------- */
const $ = (s) => document.querySelector(s);
const flagListEl = $("#flagList"), logEl = $("#eventLog"), toastEl = $("#toast");
const connPill = $("#connPill");

/* ---------- Local persistence ---------- */
function loadLocal() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
}
function saveLocal() {
  try {
    const values = {};
    flags.forEach(f => { values[f.name] = values[f.name] || {}; values[f.name][env] = f.enabled; });
    // merge with existing so switching envs keeps other envs
    const prev = loadLocal() || { values: {} };
    Object.keys(values).forEach(k => { prev.values[k] = { ...(prev.values[k] || {}), ...values[k] }; });
    prev.events = events.slice(0, 30);
    localStorage.setItem(LS_KEY, JSON.stringify(prev));
  } catch {}
}
function localFlagsFor(e) {
  const saved = loadLocal();
  return SEED.map(s => ({
    name: s.name, label: s.label, icon: s.icon, category: s.category, rollout: s.rollout,
    description: s.description, affects: s.affects, environment: e,
    enabled: !!(saved && saved.values[s.name] && saved.values[s.name][e] !== undefined
      ? saved.values[s.name][e] : s.values[e]),
  }));
}

/* ---------- Mock API client ---------- */
async function fetchJSON(url, opts = {}, timeoutMs = 1800) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...opts, signal: ctrl.signal });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}
async function tryMockFlags(e) {
  const data = await fetchJSON(`${MOCK_API}/api/v1/flags/?environment=${e}`);
  return data.map(f => ({ ...f, environment: e }));
}
async function mockToggle(name, e, enabled) {
  return fetchJSON(`${MOCK_API}/api/v1/flags/${name}/toggle`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ environment: e, enabled, actor: "dashboard" }),
  }, 3000);
}

/* ---------- Real Flagsmith SDK client ----------
   Loads the official SDK from CDN and inits it exactly as the docs show:
     flagsmith.init({ environmentID, api, cacheFlags:true, onChange })
   Reads via hasFeature()/getValue(). Writes need a server-side token, so in
   real mode we attempt the mock REST toggle as the write path and otherwise
   guide the user to flip the flag in the Flagsmith dashboard — the read
   path (what the game actually consumes) is 100% real SDK. */
let fsReady = false;
async function connectRealFlagsmith(apiUrl, key) {
  await new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/flagsmith@2.6.0/index.js";
    s.onload = resolve; s.onerror = () => reject(new Error("SDK failed to load (check internet)"));
    document.head.appendChild(s);
  });
  const fs = window.flagsmith;
  if (!fs) throw new Error("flagsmith global not found after load");
  await fs.init({
    environmentID: key,
    api: apiUrl || undefined,
    cacheFlags: true,
    enableAnalytics: false,
    onChange: (oldFlags, params) => {
      if (params && params.isFromServer) { refreshFromReal(); }
    },
  });
  fsReady = true;
  mode = "real";
  setConn("live", "● REAL FLAGSMITH");
  await refreshFromReal();
  toast("✅ Connected to Flagsmith via official JS SDK. Live values incoming…");
}
async function refreshFromReal() {
  const fs = window.flagsmith;
  if (!fs || !fsReady) return;
  try { await fs.getFlags(); } catch {}
  const all = fs.getAllFlags ? fs.getAllFlags() : [];
  const byName = {};
  (all || []).forEach(f => { byName[f.flagName || f.name] = f; });
  flags = SEED.map(s => {
    const f = byName[s.name];
    const enabled = f ? !!f.enabled : !!(s.values[env]);
    return { ...s, environment: env, enabled };
  });
  renderAll();
}

/* ---------- Data loading ---------- */
async function loadFlags() {
  if (mode === "real" && fsReady) { await refreshFromReal(); return; }
  try {
    flags = await tryMockFlags(env);
    if (mode !== "mock") { mode = "mock"; setConn("mock", "● MOCK API :8001"); }
  } catch {
    flags = localFlagsFor(env);
    if (mode !== "local") { mode = "local"; setConn("mock", "● LOCAL MODE"); }
  }
  renderAll();
}

async function toggleFlag(name, force) {
  const cur = flags.find(f => f.name === name);
  if (!cur) return;
  const next = force !== undefined ? force : !cur.enabled;
  const t0 = performance.now();

  if (mode === "real" && fsReady) {
    // Write path: try mock REST (works when mock runs alongside real Flagsmith),
    // else flip locally and tell the user where the real switch lives.
    try {
      await mockToggle(name, env, next);
    } catch {
      toast("ℹ️ Real Flagsmith: flip this flag in your Flagsmith dashboard — the game reads it live via SDK.");
    }
    cur.enabled = next;
  } else if (mode === "mock") {
    try {
      const out = await mockToggle(name, env, next);
      cur.enabled = !!out.enabled;
    } catch {
      cur.enabled = next; mode = "local"; setConn("mock", "● LOCAL MODE");
    }
  } else {
    cur.enabled = next;
  }

  const ms = Math.max(1, Math.round(performance.now() - t0));
  lastFlip = new Date();
  pushEvent(name, cur.enabled, "dashboard");
  saveLocal();
  renderAll();
  toast(`⚡ ${name} → ${cur.enabled ? "ON" : "OFF"} (${env}) in ${ms}ms — no restart, no patch.`);
}

function pushEvent(flag, enabled, actor) {
  events.unshift({ ts: Date.now(), flag, enabled, environment: env, actor });
  events = events.slice(0, 30);
}

/* ---------- Rendering ---------- */
function setConn(cls, text) { connPill.className = "conn-pill " + cls; connPill.textContent = text; }

function visibleFlags() {
  const q = ($("#search").value || "").toLowerCase().trim();
  const cat = $("#catFilter").value;
  return flags.filter(f =>
    (!cat || f.category === cat) &&
    (!q || (f.name + " " + f.label + " " + f.description).toLowerCase().includes(q)));
}

function renderFlags() {
  const list = visibleFlags();
  if (!list.length) { flagListEl.innerHTML = `<div class="empty">No flags match. Try clearing search. 🌴</div>`; return; }
  focusedIdx = Math.min(focusedIdx, list.length - 1);
  flagListEl.innerHTML = list.map((f, i) => `
    <article class="flag-card ${f.enabled ? "on" : ""} ${i === focusedIdx ? "focused" : ""}" data-name="${f.name}" role="listitem">
      <div class="flag-icon">${f.icon}</div>
      <div class="flag-body">
        <div class="flag-title"><code>${f.name}</code><span class="flag-cat">${f.category}</span><span class="flag-cat">${f.rollout}% rollout</span></div>
        <p class="flag-desc"><strong>${f.label}.</strong> ${f.description}</p>
        <div class="flag-affects">Affects: <b>${f.affects}</b></div>
      </div>
      <div class="flag-side">
        <button class="toggle" role="switch" aria-checked="${f.enabled}" data-toggle="${f.name}" aria-label="Toggle ${f.name}"></button>
        <span class="toggle-label" style="color:${f.enabled ? "var(--green)" : "var(--muted)"}">${f.enabled ? "ON" : "OFF"}</span>
      </div>
    </article>`).join("");
  flagListEl.querySelectorAll("[data-toggle]").forEach(b =>
    b.addEventListener("click", () => toggleFlag(b.dataset.toggle)));
  flagListEl.querySelectorAll(".flag-card").forEach(c =>
    c.addEventListener("click", (e) => {
      if (e.target.closest(".toggle")) return;
      const idx = visibleFlags().findIndex(f => f.name === c.dataset.name);
      if (idx >= 0) { focusedIdx = idx; renderFlags(); }
    }));
}

function flagOn(name) { const f = flags.find(x => x.name === name); return !!(f && f.enabled); }

function renderMap() {
  // Expansion
  const exp = flagOn("leonida_expansion");
  $("#keysGroup").classList.toggle("locked", !exp);
  $("#gellhornGroup").classList.toggle("locked", !exp);
  $("#keysGroup").querySelector(".map-sub").textContent = exp ? "✅ OPEN — new heists live" : "🔒 Locked — flip leonida_expansion";
  // Night
  const night = flagOn("neon_nights_event");
  $("#nightOverlay").setAttribute("opacity", night ? "0.55" : "0");
  $("#sun").setAttribute("opacity", night ? "0.25" : "0.9");
  $("#eventBanner").classList.toggle("hidden", !night);
  // Hurricane
  const storm = flagOn("hurricane_ian");
  $("#rainLayer").setAttribute("opacity", storm ? "1" : "0");
  $("#stormBanner").classList.toggle("hidden", !storm);
  // Police + lowrider
  $("#policeLayer").classList.toggle("show", flagOn("police_pursuit_ai"));
  $("#lowriderLayer").classList.toggle("show", flagOn("lowrider_culture_pack"));
  startTraffic(flagOn("traffic_density_high"));
}

function renderStats() {
  const base = 12400;
  let players = base;
  if (flagOn("crossplay_enabled")) players += 24100;
  if (flagOn("ps5_beta_access")) players += 8300;
  if (flagOn("leonida_expansion")) players += 5200;
  $("#statPlayers").textContent = players.toLocaleString();
  $("#statPlayersSub").textContent = flagOn("crossplay_enabled") ? "PS5 + Xbox + PC" : (flagOn("ps5_beta_access") ? "PS5 beta 4K/120Hz" : "PS5 only");
  $("#statXp").textContent = flagOn("double_xp_weekend") ? "×2" : "×1";
  $("#statXp").style.color = flagOn("double_xp_weekend") ? "var(--yellow)" : "";
  $("#statWanted").textContent = flagOn("police_pursuit_ai") ? "★★★★★" : "☆☆☆☆☆";
  $("#statWantedSub").textContent = flagOn("police_pursuit_ai") ? "pursuit AI hunting" : "calm streets";
  const on = flags.filter(f => f.enabled).length;
  $("#statFlags").textContent = `${on}/${flags.length}`;
  $("#statLast").textContent = lastFlip ? lastFlip.toLocaleTimeString() : "—";
  $("#envName").textContent = env[0].toUpperCase() + env.slice(1);
}

function renderLog() {
  if (!events.length) { logEl.innerHTML = `<li>No flips yet. Toggle a flag — this is your audit trail. 📡</li>`; return; }
  logEl.innerHTML = events.map(e => {
    const t = new Date(e.ts).toLocaleTimeString();
    return `<li>${t} · <code>${e.flag}</code> → <b style="color:${e.enabled ? "var(--green)" : "var(--muted)"}">${e.enabled ? "ON" : "OFF"}</b> · ${e.environment} · by ${e.actor}</li>`;
  }).join("");
}

function renderAll() { renderFlags(); renderMap(); renderStats(); renderLog(); }

/* ---------- Traffic animation ---------- */
const TRAFFIC_PATHS = [
  "M260 80 L560 70", "M260 160 L570 150", "M270 240 L575 230", "M280 320 L560 310",
  "M320 60 L340 390", "M420 55 L430 385", "M510 50 L520 380",
];
function buildRain() {
  const g = $("#rainLayer");
  if (g.childElementCount) return;
  let s = "";
  for (let i = 0; i < 90; i++) {
    const x = Math.random() * 800, y = Math.random() * 560;
    s += `<line x1="${x}" y1="${y}" x2="${x - 8}" y2="${y + 22}" stroke="#7fd4ff" stroke-width="1.4" opacity=".7"/>`;
  }
  g.innerHTML = s;
}
function startTraffic(high) {
  const layer = $("#trafficLayer");
  if (trafficTimer) { clearInterval(trafficTimer); trafficTimer = null; }
  layer.innerHTML = "";
  const count = high ? 16 : 8;
  const speed = high ? 55 : 28;
  const dots = [];
  for (let i = 0; i < count; i++) {
    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    c.setAttribute("r", high ? "4" : "3.4");
    c.setAttribute("fill", high ? "#ffd166" : "#00e5ff");
    layer.appendChild(c);
    dots.push({ el: c, path: TRAFFIC_PATHS[i % TRAFFIC_PATHS.length], t: Math.random() });
  }
  const step = () => {
    dots.forEach(d => {
      d.t = (d.t + 0.008 * (speed / 30)) % 1;
      const [a, b] = d.path.replace("M", "").split("L").map(s => s.trim().split(/\s+/).map(Number));
      const x = a[0] + (b[0] - a[0]) * d.t, y = a[1] + (b[1] - a[1]) * d.t;
      d.el.setAttribute("cx", x); d.el.setAttribute("cy", y);
    });
  };
  step();
  trafficTimer = setInterval(step, 50);
}

/* ---------- Toast ---------- */
let toastTimer = null;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.add("hidden"), 3200);
}

/* ---------- Env tabs / filters ---------- */
document.querySelectorAll(".env-tab").forEach(t => t.addEventListener("click", async () => {
  document.querySelectorAll(".env-tab").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  env = t.dataset.env;
  focusedIdx = 0;
  await loadFlags();
  toast(`🌍 Switched to ${env.toUpperCase()} — flags re-evaluated live.`);
}));
$("#search").addEventListener("input", () => { focusedIdx = 0; renderFlags(); });
$("#catFilter").addEventListener("change", () => { focusedIdx = 0; renderFlags(); });
$("#resetBtn").addEventListener("click", async () => {
  if (mode === "mock") { try { await fetchJSON(`${MOCK_API}/api/v1/flags/reset`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); } catch {} }
  localStorage.removeItem(LS_KEY);
  events = [];
  await loadFlags();
  toast("↺ Reset to seed values across environments.");
});

/* ---------- Keyboard (PS5-style navigation) ---------- */
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input, select, textarea")) return;
  const list = visibleFlags();
  if (!list.length) return;
  if (e.key === "ArrowDown") { focusedIdx = Math.min(focusedIdx + 1, list.length - 1); renderFlags(); e.preventDefault(); }
  else if (e.key === "ArrowUp") { focusedIdx = Math.max(focusedIdx - 1, 0); renderFlags(); e.preventDefault(); }
  else if (e.key === " " || e.key === "Enter") { toggleFlag(list[focusedIdx].name); e.preventDefault(); }
  else if (/^[1-9]$/.test(e.key)) { const i = Number(e.key) - 1; if (list[i]) toggleFlag(list[i].name); }
});

/* ---------- Gamepad (DualSense) ---------- */
let padPrev = {};
window.addEventListener("gamepadconnected", () => toast("🎮 DualSense connected — D-pad navigates, ✕ (A) toggles."));
setInterval(() => {
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const p of pads) {
    if (!p) continue;
    const list = visibleFlags();
    const pressed = (i) => !!(p.buttons[i] && p.buttons[i].pressed);
    if (pressed(13) && !padPrev.down) { focusedIdx = Math.min(focusedIdx + 1, list.length - 1); renderFlags(); }
    if (pressed(12) && !padPrev.up) { focusedIdx = Math.max(focusedIdx - 1, 0); renderFlags(); }
    if (pressed(0) && !padPrev.a && list[focusedIdx]) toggleFlag(list[focusedIdx].name);
    padPrev = { down: pressed(13), up: pressed(12), a: pressed(0) };
    break;
  }
}, 120);

/* ---------- Connect modal ---------- */
const modal = $("#modal");
$("#connectBtn").addEventListener("click", () => {
  const cfg = JSON.parse(localStorage.getItem(LS_FS) || "{}");
  $("#fsApi").value = cfg.api || ""; $("#fsKey").value = cfg.key || "";
  modal.classList.remove("hidden");
});
$("#fsClose").addEventListener("click", () => modal.classList.add("hidden"));
$("#fsMock").addEventListener("click", () => { modal.classList.add("hidden"); mode = "mock"; loadFlags(); toast("● Mock mode — start mock/server.py for shared state."); });
$("#fsSave").addEventListener("click", async () => {
  const api = $("#fsApi").value.trim(), key = $("#fsKey").value.trim();
  if (!key) { toast("Paste your Flagsmith environment key first."); return; }
  localStorage.setItem(LS_FS, JSON.stringify({ api, key }));
  modal.classList.add("hidden");
  setConn("mock", "● CONNECTING…");
  try { await connectRealFlagsmith(api, key); }
  catch (err) { setConn("mock", "● LOCAL MODE"); toast("❌ " + err.message); }
});
modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.add("hidden"); });

/* ---------- Polling (like Flagsmith SDK polling) ---------- */
setInterval(async () => {
  if (mode === "real" && fsReady) { await refreshFromReal(); return; }
  if (mode !== "mock") return; // local mode: nothing remote to poll
  try {
    const fresh = await tryMockFlags(env);
    const changed = fresh.some(f => { const o = flags.find(x => x.name === f.name); return o && o.enabled !== f.enabled; });
    if (changed) {
      flags = fresh;
      renderAll();
      toast("📡 Remote flag change detected — world updated live.");
    }
  } catch { /* mock went away; stay on last known state */ }
}, 2000);

/* ---------- Boot ---------- */
(function boot() {
  const cats = [...new Set(SEED.map(s => s.category))];
  $("#catFilter").innerHTML = `<option value="">All categories</option>` + cats.map(c => `<option>${c}</option>`).join("");
  buildRain();
  const saved = loadLocal();
  if (saved && saved.events) events = saved.events;
  // Auto-connect real Flagsmith if previously configured
  const cfg = JSON.parse(localStorage.getItem(LS_FS) || "{}");
  if (cfg.key) {
    connectRealFlagsmith(cfg.api, cfg.key).catch(() => loadFlags());
  } else {
    loadFlags();
  }
  setTimeout(() => toast("🌴 Welcome to Leonida. Flip a flag — watch Vice City change. No patch. No restart."), 600);
})();
