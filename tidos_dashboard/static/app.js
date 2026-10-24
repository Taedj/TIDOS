// TIDOSZIT Control Center — client
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import { getAuth, signInWithPopup, signOut, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, { credentials: "same-origin", ...opts });
  let data = {};
  try { data = await res.json(); } catch { /* empty */ }
  if (res.status === 401 && path !== "/api/auth/password" && !path.startsWith("/api/auth/")) { showLogin("login"); }
  return { ok: res.ok, status: res.status, data };
}

function toast(html, cls = "") {
  const el = document.createElement("div");
  el.className = "toast " + cls;
  el.innerHTML = html;
  $("toasts").appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

// ---------------------------------------------------------------- login
let firebaseAuth = null;
let lockTimer = null;

function setMsg(text, cls = "info") { const m = $("loginMsg"); m.className = "msg " + cls; m.textContent = text; }

function showLogin(stage, info = {}) {
  stopApp();
  $("app").classList.add("hidden");
  $("login").classList.remove("hidden");
  for (const s of ["login", "password", "setup"]) $("stage-" + s).classList.toggle("hidden", s !== stage);
  $("step1").className = "step " + (stage === "login" ? "active" : "done");
  $("step2").className = "step " + (stage === "login" ? "" : "active");
  showLock(info);
  if (stage === "password") $("pw").focus();
  if (stage === "setup") $("newpw").focus();
}

function showLock(info) {
  clearInterval(lockTimer);
  if (!info.locked_until) return;
  const until = new Date(info.locked_until);
  const tick = () => {
    const s = Math.max(0, Math.round((until - new Date()) / 1000));
    setMsg(`[LOCKED] Too many wrong passwords. Try again in ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}.`, "err");
    if (!s) { clearInterval(lockTimer); setMsg("Lock lifted. You may try again.", "info"); }
  };
  tick();
  lockTimer = setInterval(tick, 1000);
}

$("googleBtn").addEventListener("click", async () => {
  const btn = $("googleBtn");
  btn.disabled = true;
  setMsg("Opening Google sign-in…");
  try {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    const cred = await signInWithPopup(firebaseAuth, provider);
    const idToken = await cred.user.getIdToken();
    await signOut(firebaseAuth); // the browser keeps no Firebase session; the server holds the token
    setMsg("Verifying owner identity…");
    const r = await api("/api/auth/google", { idToken });
    if (!r.ok) { setMsg(r.data.error || "Verification failed.", "err"); return; }
    setMsg(r.data.stage === "setup" ? "Owner verified. Set your control password." : "Owner verified.", "ok");
    showLogin(r.data.stage, r.data);
  } catch (e) {
    setMsg(e.code === "auth/popup-closed-by-user" ? "Sign-in cancelled." : (e.message || "Sign-in error."), "err");
  } finally {
    btn.disabled = false;
  }
});

$("stage-password").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const pw = $("pw");
  const r = await api("/api/auth/password", { password: pw.value });
  pw.value = "";
  if (r.ok) return startApp(true);
  if (r.status === 401 && r.data.failures_left !== undefined && !r.data.locked_until) {
    setMsg(`${r.data.error} ${r.data.failures_left} attempt(s) left before lockout.`, "err");
  } else if (r.data.locked_until) {
    showLock(r.data);
  } else {
    setMsg(r.data.error || "Login failed.", "err");
    if (r.status === 401) showLogin("login");
  }
});

$("stage-setup").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const a = $("newpw").value, b = $("newpw2").value;
  if (a !== b) return setMsg("Passwords do not match.", "err");
  const r = await api("/api/auth/setup", { password: a });
  $("newpw").value = $("newpw2").value = "";
  if (r.ok) { toast("<b>[SYSTEM]</b> Control password set. Only its hash is stored."); return startApp(true); }
  setMsg(r.data.error || "Setup failed.", "err");
});

// ---------------------------------------------------------------- app
let expiresAt = 0, sessionTimer = null, eventSource = null, lastEventId = 0, refreshTimer = null;

function stopApp() {
  clearInterval(sessionTimer); clearInterval(refreshTimer);
  if (eventSource) { eventSource.close(); eventSource = null; }
  $("liveDot").classList.add("off");
}

async function startApp(fresh = false) {
  $("login").classList.add("hidden");
  $("app").classList.remove("hidden");
  if (fresh) toast("<b>[SYSTEM]</b> Welcome back, Player. Control center unlocked.");
  await loadStatus();
  loadLive();
  connectStream();
  refreshTimer = setInterval(() => { loadStatus(); if (!$("view-security").classList.contains("hidden")) loadSecurity(); }, 30000);
}

function startTimer(seconds) {
  expiresAt = Date.now() + seconds * 1000;
  clearInterval(sessionTimer);
  sessionTimer = setInterval(() => {
    const s = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    const t = $("timer");
    t.textContent = `session ${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    t.classList.toggle("low", s < 120);
    if (!s) { toast("<b>[SYSTEM]</b> Session expired. Verify again."); showLogin("login"); }
  }, 1000);
}

document.querySelectorAll(".tab[data-view]").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    for (const v of ["status", "live", "dungeons", "playbooks", "security"]) $("view-" + v).classList.toggle("hidden", v !== tab.dataset.view);
    if (tab.dataset.view === "live") loadLive();
    if (tab.dataset.view === "dungeons") loadDungeons();
    if (tab.dataset.view === "playbooks") loadPlaybooks();
    if (tab.dataset.view === "security") loadSecurity();
  }));
document.querySelectorAll(".tab.locked").forEach((tab) =>
  tab.addEventListener("click", () => toast(`<b>[SYSTEM]</b> ${esc(tab.title)}.`)));

$("logoutBtn").addEventListener("click", async () => { await api("/api/auth/logout", {}); showLogin("login"); setMsg("Logged out.", "info"); });

// ---- status
const fmt = (n) => Number(n || 0).toLocaleString();
const when = (iso) => { if (!iso) return ""; const d = new Date(iso); return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false }); };

async function loadStatus() {
  const r = await api("/api/status");
  if (!r.ok) return;
  const d = r.data, p = d.player;
  startTimer(d.session.expires_in);
  const pct = Math.min(100, Math.round(100 * (p.xp - p.floor_xp) / Math.max(1, p.next_xp - p.floor_xp)));
  for (const id of ["chipRank", "pRank"]) { $(id).textContent = p.rank; $(id).className = "rank " + p.rank + (id === "pRank" ? " lg" : ""); }
  $("chipLevel").textContent = $("pLevel").textContent = p.level;
  $("chipXp").style.width = $("pXpBar").style.width = pct + "%";
  $("pXp").textContent = fmt(p.xp); $("pNext").textContent = fmt(p.next_xp);

  const prev = Number(store.get("tidoszit.level") || 0);
  if (prev && p.level > prev) toast(`<b>[SYSTEM] LEVEL UP!</b><br>Level ${prev} → ${p.level} · Rank ${esc(p.rank)}`, "levelup");
  store.set("tidoszit.level", String(p.level));

  const t = d.totals;
  $("pTotals").innerHTML = [
    ["Sessions", fmt(t.sessions)], ["Tasks", fmt(t.tasks)], ["Cleared", fmt(t.success)], ["Failed", fmt(t.failure)],
    ["Tokens in", fmt(t.tokens_in)], ["Tokens out", fmt(t.tokens_out)], ["Player", esc(d.session.email)],
  ].map(([k, v]) => `<span class="muted">${k}</span><b>${v}</b>`).join("");

  $("stats").innerHTML = d.stats.map((s) => `
    <div class="stat" title="${esc(s.hint)}"><span class="k">${esc(s.key)}</span>
      <span class="bar"><i></i></span><span class="v">${Number(s.value)}</span>
      <span class="stat-name">${esc(s.name)} — ${esc(s.hint)}</span></div>`).join("");
  // style attributes in HTML are blocked by the CSP; widths are applied through CSSOM instead
  $("stats").querySelectorAll(".bar i").forEach((el, i) => { el.style.width = Number(d.stats[i].value) + "%"; });

  $("quests").innerHTML = d.quests.map((q) => `
    <div class="quest ${q.done ? "done" : ""} ${q.failed ? "failed" : ""}">
      <span class="box">${q.done ? "✓" : q.failed ? "✕" : ""}</span>${esc(q.title)}
      <span class="p">${Math.min(q.progress, q.goal)}/${q.goal}</span></div>`).join("")
    + `<p class="small faint note">Quests reset daily (UTC).</p>`;

  $("domains").innerHTML = d.domains.map((dm) => `
    <div class="row"><span class="rank ${esc(dm.rank)}">${esc(dm.rank)}</span>
      <span class="name">${esc(dm.name)}</span><span class="pill">Lv ${dm.level}</span>
      <span class="pill">${fmt(dm.xp)} XP</span><span class="pill ok">${dm.success}/${dm.tasks}</span></div>`).join("") || `<p class="muted">No domains yet.</p>`;

  $("models").innerHTML = d.models.map((m) => `
    <div class="row"><span class="name">${esc(m.model)}</span><span class="pill">${fmt(m.tasks)} tasks</span>
      <span class="pill ${m.avg_score >= 0.6 ? "ok" : m.avg_score <= 0.4 ? "bad" : ""}">avg ${m.avg_score.toFixed(2)}</span></div>`).join("") || `<p class="muted">No models yet.</p>`;

  $("cleared").innerHTML = d.cleared.map((c) => `
    <div class="log-item"><span class="sys">[QUEST CLEARED]</span><span class="faint">${esc(when(c.ts))} · ${esc(c.project)}</span><br>${esc(c.prompt)}</div>`).join("") || `<p class="muted">No cleared quests yet.</p>`;
}

// ---- live
function eventLine(ev, isNew) {
  const div = document.createElement("div");
  div.className = "ev" + (ev.is_error ? " err" : "") + (isNew ? " new" : "");
  const t = ev.ts ? new Date(ev.ts).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }) : "";
  div.innerHTML = `<span class="t">${esc(t)}</span><span class="e">${esc(ev.tool || ev.event)}</span><span class="s" title="${esc(ev.summary)}">${esc(ev.summary || ev.event)}</span>`;
  return div;
}

function pushEvents(events, isNew) {
  const box = $("console");
  for (const ev of events) {
    box.prepend(eventLine(ev, isNew));
    lastEventId = Math.max(lastEventId, ev.id);
  }
  while (box.children.length > 400) box.lastChild.remove();
  if (isNew && events.some((e) => e.event === "Stop")) loadStatus();
}

async function loadLive() {
  const [live, tasks, sec] = await Promise.all([api("/api/live?since=0"), api("/api/tasks"), api("/api/security")]);
  if (live.ok) {
    $("console").innerHTML = "";
    pushEvents(live.data.events, false);
    if (!live.data.events.length) $("console").innerHTML = `<p class="muted">No live events yet. Install the brain hooks, then use Claude Code — events stream here in real time.</p>`;
    $("activeSessions").innerHTML = live.data.active.map((s) => `
      <div class="session-card"><span class="live-dot"></span><b>${esc(String(s.session_id || "?").slice(0, 8))}</b>
        <span class="faint"> · ${esc(s.cwd || "")}</span><br>
        last: ${esc(s.last_tool || "—")} · ${fmt(s.events)} events · <span class="${s.errors ? "pill bad" : "pill"}">${fmt(s.errors)} errors</span></div>`).join("")
      || `<p class="muted">No session active in the last 10 minutes.</p>`;
  }
  if (tasks.ok) {
    $("tasks").innerHTML = tasks.data.tasks.map((t) => `
      <tr><td>${esc(when(t.started_at))}</td><td>${esc(t.project)}</td><td class="prompt" title="${esc(t.prompt)}">${esc(t.prompt)}</td>
      <td>${esc((t.model || "").replace("claude-", ""))}</td><td>${t.tool_calls}${t.tool_errors ? ` <span class="pill bad">${t.tool_errors} err</span>` : ""}</td>
      <td>${t.verify_passed === null ? '<span class="faint">—</span>' : t.verify_passed ? '<span class="pill ok">pass</span>' : '<span class="pill bad">fail</span>'}</td>
      <td>${t.score === null ? "" : Number(t.score).toFixed(2)}</td>
      <td><span class="pill ${t.outcome === "success" ? "ok" : t.outcome === "failure" ? "bad" : ""}">${esc(t.outcome)}</span>${t.corrected ? ' <span class="pill warn">corrected</span>' : ""}</td></tr>`).join("");
  }
  if (sec.ok) {
    const tr = sec.data.switches.find((s) => s.name === "tracing");
    $("tracingState").textContent = tr && tr.on ? "ON" : "PAUSED";
  }
}

function connectStream() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`/api/stream?since=${lastEventId}`);
  eventSource.addEventListener("open", () => $("liveDot").classList.remove("off"));
  eventSource.addEventListener("live", (e) => pushEvents(JSON.parse(e.data), true));
  eventSource.addEventListener("expired", () => { eventSource.close(); showLogin("login"); });
  eventSource.addEventListener("error", () => $("liveDot").classList.add("off"));
}

// ---- dungeons
async function loadDungeons() {
  const r = await api("/api/dungeons");
  if (!r.ok) return;
  const d = r.data;
  const pct = (v, n) => v === null ? '<span class="faint">—</span>' : `${v}% <span class="faint">(${n[0]}/${n[1]})</span>`;
  $("leaderboard").innerHTML = d.leaderboard.map((b) => `
    <tr><td>${esc(b.model)}</td><td>${pct(b.off, b.off_n)}</td><td>${pct(b.on, b.on_n)}</td>
    <td>${b.lift === null ? '<span class="faint">—</span>' : `<span class="${b.lift > 0 ? "lift-up" : b.lift < 0 ? "lift-down" : ""}">${b.lift > 0 ? "+" : ""}${b.lift} pts</span>`}</td>
    <td>${b.cost ? "$" + b.cost.toFixed(2) : '<span class="faint">free</span>'}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">No raids yet. Run the command below.</td></tr>`;
  $("dungeonMeta").textContent = `${d.tasks.length} dungeons · last raid ${d.last_run ? when(d.last_run) : "never"} · lift = pass rate with TIDOS minus without.`;
  const label = (c) => { const [m, t] = c.split("|"); return `${esc(m.replace("opencode:", "").replace("opencode/", ""))}<br>${t === "1" ? "+TIDOS" : "plain"}`; };
  $("matrixHead").innerHTML = `<tr><th>Dungeon</th>${d.columns.map((c) => `<th>${label(c)}</th>`).join("")}</tr>`;
  $("matrixBody").innerHTML = d.tasks.map((t) => `
    <tr><td><span class="rank ${esc(t.difficulty)}">${esc(t.difficulty)}</span> <span title="${esc(t.title)}">${esc(t.id)}</span></td>
    ${d.columns.map((c) => { const x = d.cells[t.id + "|" + c];
      return `<td>${!x ? '<span class="cell none">·</span>' : x.passed ? `<span class="cell ok" title="${x.seconds}s">✓</span>` : `<span class="cell bad" title="${esc(x.error || "failed")}">✗</span>`}</td>`; }).join("")}</tr>`).join("");
}

// ---- playbooks
async function showPlaybook(path) {
  const r = await api("/api/playbook?path=" + encodeURIComponent(path));
  $("pbTitle").textContent = path;
  $("pbView").textContent = r.ok ? r.data.text : "Not found.";
  document.querySelectorAll("#pbList tr").forEach((tr) => tr.classList.toggle("sel", tr.dataset.path === path));
}

async function loadPlaybooks() {
  const r = await api("/api/playbooks");
  if (!r.ok) return;
  const items = r.data.playbooks;
  $("pbList").innerHTML = items.map((p) => `
    <tr data-path="${esc(p.path)}" class="${p.disabled ? "off" : ""}">
      <td>${esc(p.project)}</td><td>${esc(p.type)}</td>
      <td>${/^[EDCBAS]$/.test(p.rank) ? `<span class="rank ${esc(p.rank)}">${esc(p.rank)}</span>` : `<span class="pill">${esc(p.rank)}</span>`}</td>
      <td>${esc(p.confidence)}</td><td class="small">${esc(p.evidence)}</td>
      <td>${p.served ? `${p.served}x` : '<span class="faint">0</span>'}</td>
      <td><button class="toggle ${p.disabled ? "" : "on"}" data-path="${esc(p.path)}" aria-label="toggle playbook"></button></td></tr>`).join("")
    || `<tr><td colspan="7" class="muted">Nothing learned yet. Work with a strong model, then START TIDOS.</td></tr>`;
  $("pbMeta").textContent = `${items.length} playbooks in ${r.data.dir} · served = times a GUIDE brief gave it to a weaker model · switched off = never served.`;
  $("pbList").querySelectorAll("tr[data-path]").forEach((tr) => tr.addEventListener("click", (ev) => {
    if (!ev.target.classList.contains("toggle")) showPlaybook(tr.dataset.path);
  }));
  $("pbList").querySelectorAll(".toggle").forEach((btn) => btn.addEventListener("click", async () => {
    const disabled = btn.classList.contains("on");
    const res = await api("/api/playbooks/toggle", { path: btn.dataset.path, disabled });
    if (res.ok) { toast(`<b>[SYSTEM]</b> Playbook ${disabled ? "switched off" : "switched on"}.`); loadPlaybooks(); }
  }));
}

// ---- security
async function loadSecurity() {
  const r = await api("/api/security");
  if (!r.ok) return;
  const d = r.data;
  $("switches").innerHTML = d.switches.map((s) => `
    <div class="switch"><div class="d"><b>${esc(s.name)}</b><span class="small muted">${esc(s.description)}</span></div>
      <span class="pill ${s.on === s.default ? "" : "warn"}">${s.on === s.default ? "default" : "changed"}</span>
      <button class="toggle ${s.on ? "on" : ""}" data-name="${esc(s.name)}" aria-label="toggle ${esc(s.name)}" aria-pressed="${s.on}"></button></div>`).join("");
  $("switches").querySelectorAll(".toggle").forEach((btn) => btn.addEventListener("click", async () => {
    const on = !btn.classList.contains("on");
    const res = await api("/api/switches", { name: btn.dataset.name, on });
    if (res.ok) { toast(`<b>[SYSTEM]</b> ${esc(btn.dataset.name)} → ${on ? "ON" : "OFF"}`); loadSecurity(); }
  }));
  $("secInfo").innerHTML = [
    ["Player", esc(d.session.email)], ["Session ends in", `${Math.floor(d.session.expires_in / 60)} min`],
    ["Lock", d.locked_until ? `<span class="pill bad">locked until ${esc(when(d.locked_until))}</span>` : '<span class="pill ok">open</span>'],
    ["Attempts before lockout", d.failures_left], ["Brain", `${esc(d.brain.path)} · ${fmt(d.brain.size_kb)} KB`],
  ].map(([k, v]) => `<span class="muted">${k}</span><b>${v}</b>`).join("");
  $("secLog").innerHTML = d.log.map((e) => `
    <tr><td>${esc(e.ts)}</td><td><span class="pill ${/fail|mismatch|rejected|lockout|blocked/.test(e.event) ? "bad" : /ok|set|changed/.test(e.event) ? "ok" : ""}">${esc(e.event)}</span></td><td>${esc(e.detail)}</td></tr>`).join("");
}

$("changeForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const msg = $("changeMsg");
  if ($("chgpw").value !== $("chgpw2").value) { msg.className = "msg err"; msg.textContent = "New passwords do not match."; return; }
  const r = await api("/api/auth/change", { current: $("curpw").value, new: $("chgpw").value });
  for (const id of ["curpw", "chgpw", "chgpw2"]) $(id).value = "";
  msg.className = "msg " + (r.ok ? "ok" : "err");
  msg.textContent = r.ok ? "Password changed." : (r.data.error || "Failed.");
  loadSecurity();
});

// ---------------------------------------------------------------- boot
(async function boot() {
  const r = await api("/api/boot");
  if (!r.ok) { setMsg("Control center unavailable.", "err"); return; }
  firebaseAuth = getAuth(initializeApp(r.data.firebase));
  if (r.data.stage === "app") return startApp();
  showLogin(r.data.stage, r.data);
})();
