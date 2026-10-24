// TIDOSZIT Control Center — client
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
import { getAuth, signInWithPopup, signOut, GoogleAuthProvider } from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";
import { t, lang, applyStatic, wireSwitches } from "./i18n.js";

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

function setMsg(text, cls = "info") { const m = $("loginMsg"); m.className = "msg " + cls; m.textContent = t(text); }

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
    setMsg(t("[LOCKED] Too many wrong passwords. Try again in {t}.", { t: `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}` }), "err");
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
    setMsg(`${t(r.data.error)} ${t("{n} attempt(s) left before lockout.", { n: r.data.failures_left })}`, "err");
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
  if (r.ok) { toast(`<b>[SYSTEM]</b> ${t("Control password set. Only its hash is stored.")}`); return startApp(true); }
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
  if (fresh) toast(`<b>[SYSTEM]</b> ${t("Welcome back, Player. Control center unlocked.")}`);
  await loadStatus();
  loadArmy();
  loadNotifications();
  if (!startApp.wired) {
    startApp.wired = true;
    document.querySelectorAll("#askBar button").forEach((b) => b.addEventListener("click", () => { askMode = b.dataset.mode; }));
    $("askBar").addEventListener("submit", (e) => { e.preventDefault(); runAsk(); });
    $("backupBtn").addEventListener("click", async () => {
      $("backupBtn").disabled = true;
      const r = await api("/api/backups", {});
      $("backupBtn").disabled = false;
      if (r.ok) { renderBackups(r.data.backups); toast(`<b>[SYSTEM]</b> ${t("Brain backed up.")}`); }
    });
  }
  loadLive();
  connectStream();
  refreshTimer = setInterval(() => { loadStatus(); if (!$("view-security").classList.contains("hidden")) loadSecurity(); }, 30000);
}

function startTimer(seconds) {
  expiresAt = Date.now() + seconds * 1000;
  clearInterval(sessionTimer);
  sessionTimer = setInterval(() => {
    const s = Math.max(0, Math.round((expiresAt - Date.now()) / 1000));
    const el = $("timer");
    el.textContent = t("session {t}", { t: `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}` });
    el.classList.toggle("low", s < 120);
    if (!s) { toast(`<b>[SYSTEM]</b> ${t("Session expired. Verify again.")}`); showLogin("login"); }
  }, 1000);
}

document.querySelectorAll(".tab[data-view]").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    for (const v of ["status", "live", "dungeons", "playbooks", "army", "evolution", "tools", "memory", "security"]) $("view-" + v).classList.toggle("hidden", v !== tab.dataset.view);
    if (tab.dataset.view === "army") loadArmyTab();
    if (tab.dataset.view === "tools") loadTools();
    if (tab.dataset.view === "evolution") loadEvolution();
    if (tab.dataset.view === "memory") loadMemory();
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
const LOCALE = lang === "ar" ? "ar-u-nu-latn" : undefined; // Arabic month names, Western digits (match the data)
const when = (iso) => { if (!iso) return ""; const d = new Date(iso); return d.toLocaleDateString(LOCALE, { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit", hour12: false }); };

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
  if (prev && p.level > prev) toast(`<b>[SYSTEM] ${t("LEVEL UP!")}</b><br>${esc(t("Level {a} → {b} · Rank {r}", { a: prev, b: p.level, r: p.rank }))}`, "levelup");
  store.set("tidoszit.level", String(p.level));

  const tot = d.totals;
  $("pTotals").innerHTML = [
    ["Sessions", fmt(tot.sessions)], ["Tasks", fmt(tot.tasks)], ["Cleared", fmt(tot.success)], ["Failed", fmt(tot.failure)],
    ["Tokens in", fmt(tot.tokens_in)], ["Tokens out", fmt(tot.tokens_out)], ["Player", esc(d.session.email)],
  ].map(([k, v]) => `<span class="muted">${t(k)}</span><b>${v}</b>`).join("");

  $("stats").innerHTML = d.stats.map((s) => `
    <div class="stat" title="${esc(t(s.hint))}"><span class="k">${esc(s.key)}</span>
      <span class="bar"><i></i></span><span class="v">${Number(s.value)}</span>
      <span class="stat-name">${esc(t(s.name))} — ${esc(t(s.hint))}</span></div>`).join("");
  // style attributes in HTML are blocked by the CSP; widths are applied through CSSOM instead
  $("stats").querySelectorAll(".bar i").forEach((el, i) => { el.style.width = Number(d.stats[i].value) + "%"; });

  $("quests").innerHTML = d.quests.map((q) => `
    <div class="quest ${q.done ? "done" : ""} ${q.failed ? "failed" : ""}">
      <span class="box">${q.done ? "✓" : q.failed ? "✕" : ""}</span>${esc(t(q.title))}
      <span class="p">${Math.min(q.progress, q.goal)}/${q.goal}</span></div>`).join("")
    + `<p class="small faint note">${t("Quests reset daily (UTC).")}</p>`;

  $("domains").innerHTML = d.domains.map((dm) => `
    <div class="row"><span class="rank ${esc(dm.rank)}">${esc(dm.rank)}</span>
      <span class="name">${esc(dm.name)}</span><span class="pill">Lv ${dm.level}</span>
      <span class="pill">${fmt(dm.xp)} XP</span><span class="pill ok">${dm.success}/${dm.tasks}</span></div>`).join("") || `<p class="muted">${t("No domains yet.")}</p>`;

  $("models").innerHTML = d.models.map((m) => `
    <div class="row"><span class="name">${esc(m.model)}</span><span class="pill">${t("{n} tasks", { n: fmt(m.tasks) })}</span>
      <span class="pill ${m.avg_score >= 0.6 ? "ok" : m.avg_score <= 0.4 ? "bad" : ""}">${t("avg {v}", { v: m.avg_score.toFixed(2) })}</span></div>`).join("") || `<p class="muted">${t("No models yet.")}</p>`;

  $("cleared").innerHTML = d.cleared.map((c) => `
    <div class="log-item"><span class="sys">${t("[QUEST CLEARED]")}</span><span class="faint">${esc(when(c.ts))} · ${esc(c.project)}</span><br>${esc(c.prompt)}</div>`).join("") || `<p class="muted">${t("No cleared quests yet.")}</p>`;
}

// ---- live
function eventLine(ev, isNew) {
  const div = document.createElement("div");
  div.className = "ev" + (ev.is_error ? " err" : "") + (isNew ? " new" : "");
  const ts = ev.ts ? new Date(ev.ts).toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }) : "";
  div.innerHTML = `<span class="t">${esc(ts)}</span><span class="e">${esc(ev.tool || ev.event)}</span><span class="s" title="${esc(ev.summary)}">${esc(ev.summary || ev.event)}</span>`;
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

async function loadSessionInfo() {
  const r = await api("/api/session");
  if (!r.ok) return;
  const s = r.data.session;
  $("sessInfo").innerHTML = s ? [
    ["Mode", `<span class="pill ${s.mode === "guide" ? "warn" : "ok"}">${esc(t((s.mode || "").toUpperCase()))}</span>`],
    ["Model", esc(s.model)], ["Tier", esc(s.tier)], ["Tool", esc(s.tool)], ["Project", esc(s.project)],
    ["Started", esc(when(s.started_at))],
  ].map(([k, v]) => `<span class="muted">${t(k)}</span><b>${v}</b>`).join("") : `<span class="muted">${t("No START TIDOS yet.")}</span><b></b>`;
  const pct = (x) => x.pass_rate === null ? '<span class="faint">—</span>' : `${x.pass_rate}%`;
  $("effectRows").innerHTML = r.data.effect.map((e) => `
    <tr><td>${esc(e.model.replace("opencode/", ""))}</td><td>${fmt(e.guided.tasks)}</td><td>${pct(e.guided)}</td>
    <td>${fmt(e.unguided.tasks)}</td><td>${pct(e.unguided)}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">${t("No weak-model work recorded yet.")}</td></tr>`;
}

async function loadLive() {
  loadSessionInfo();
  const [live, tasks, sec] = await Promise.all([api("/api/live?since=0"), api("/api/tasks"), api("/api/security")]);
  if (live.ok) {
    $("console").innerHTML = "";
    pushEvents(live.data.events, false);
    if (!live.data.events.length) $("console").innerHTML = `<p class="muted">${t("No live events yet. Install the brain hooks, then use Claude Code — events stream here in real time.")}</p>`;
    $("activeSessions").innerHTML = live.data.active.map((s) => `
      <div class="session-card"><span class="live-dot"></span><b>${esc(String(s.session_id || "?").slice(0, 8))}</b>
        <span class="faint"> · ${esc(s.cwd || "")}</span><br>
        ${esc(t("last: {t}", { t: s.last_tool || "—" }))} · ${t("{n} events", { n: fmt(s.events) })} · <span class="${s.errors ? "pill bad" : "pill"}">${t("{n} errors", { n: fmt(s.errors) })}</span></div>`).join("")
      || `<p class="muted">${t("No session active in the last 10 minutes.")}</p>`;
  }
  if (tasks.ok) {
    const tr = t; // `t` is a task row below
    $("tasks").innerHTML = tasks.data.tasks.map((t) => `
      <tr><td>${esc(when(t.started_at))}</td><td>${esc(t.project)}</td><td class="prompt" title="${esc(t.prompt)}">${esc(t.prompt)}</td>
      <td>${esc((t.model || "").replace("claude-", ""))}</td><td>${t.tool_calls}${t.tool_errors ? ` <span class="pill bad">${tr("{n} err", { n: t.tool_errors })}</span>` : ""}</td>
      <td>${t.verify_passed === null ? '<span class="faint">—</span>' : t.verify_passed ? `<span class="pill ok">${tr("pass")}</span>` : `<span class="pill bad">${tr("fail")}</span>`}</td>
      <td>${t.score === null ? "" : Number(t.score).toFixed(2)}</td>
      <td><span class="pill ${t.outcome === "success" ? "ok" : t.outcome === "failure" ? "bad" : ""}">${esc(tr(t.outcome))}</span>${t.corrected ? ` <span class="pill warn">${tr("corrected")}</span>` : ""}</td></tr>`).join("");
  }
  if (sec.ok) {
    const sw = sec.data.switches.find((s) => s.name === "tracing");
    $("tracingState").textContent = t(sw && sw.on ? "ON" : "PAUSED");
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
    <td>${b.lift === null ? '<span class="faint">—</span>' : `<span class="${b.lift > 0 ? "lift-up" : b.lift < 0 ? "lift-down" : ""}">${t("{n} pts", { n: (b.lift > 0 ? "+" : "") + b.lift })}</span>`}</td>
    <td>${b.cost ? "$" + b.cost.toFixed(2) : `<span class="faint">${t("free")}</span>`}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">${t("No raids yet. Run the command below.")}</td></tr>`;
  $("dungeonMeta").textContent = t("{n} dungeons · last raid {w} · lift = pass rate with TIDOS minus without.", { n: d.tasks.length, w: d.last_run ? when(d.last_run) : t("never") });
  const label = (c) => { const [m, x] = c.split("|"); return `${esc(m.replace("opencode:", "").replace("opencode/", ""))}<br>${{ 1: "+TIDOS", 2: "+GUIDE", 3: "+UNIT" }[x] || t("plain")}`; };
  $("matrixHead").innerHTML = `<tr><th>${t("Dungeon")}</th>${d.columns.map((c) => `<th>${label(c)}</th>`).join("")}</tr>`;
  $("matrixBody").innerHTML = d.tasks.map((k) => `
    <tr><td><span class="rank ${esc(k.difficulty)}">${esc(k.difficulty)}</span> <span title="${esc(k.title)}">${esc(k.id)}</span></td>
    ${d.columns.map((c) => { const x = d.cells[k.id + "|" + c];
      return `<td>${!x ? '<span class="cell none">·</span>' : x.passed ? `<span class="cell ok" title="${x.seconds}s">✓</span>` : `<span class="cell bad" title="${esc(x.error || t("failed"))}">✗</span>`}</td>`; }).join("")}</tr>`).join("");
}

// ---- evolution + notifications
async function loadNotifications() {
  const r = await api("/api/notifications");
  if (!r.ok) return;
  $("notes").innerHTML = r.data.notifications.map((n) => `
    <div class="log-item"><span class="sys">[SYSTEM]</span><span class="${n.level === "bad" ? "lift-down" : n.level === "ok" ? "lift-up" : ""}">${esc(t(n.text))}</span></div>`).join("")
    || `<p class="muted">${t("Nothing needs your attention.")}</p>`;
}

async function loadEvolution() {
  const r = await api("/api/evolution");
  if (!r.ok) return;
  const d = r.data;
  $("evoList").innerHTML = d.proposals.map((p) => `
    <tr><td>${p.id}</td><td><b>${esc(p.title)}</b><br><span class="small faint">${esc(p.reason)}</span>${p.branch ? `<br><code class="sys">${esc(p.branch)}</code>` : ""}</td>
    <td><span class="pill ${p.priority === "high" ? "warn" : ""}">${esc(t(p.priority))}</span></td>
    <td><span class="pill ${p.status === "accepted" || p.status === "implemented" ? "ok" : p.status === "rejected" ? "bad" : ""}">${esc(t(p.status))}</span></td>
    <td>${p.status === "new" ? `<button class="btn ghost evo" data-id="${p.id}" data-s="accepted">${t("Accept")}</button> <button class="btn ghost evo" data-id="${p.id}" data-s="rejected">${t("Reject")}</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="5" class="muted">${t("No proposals yet. Agents add them with tidos_propose; you with tidos_learn proposals --add.")}</td></tr>`;
  $("evoList").querySelectorAll(".evo").forEach((b) => b.addEventListener("click", async () => {
    const res = await api("/api/evolution/status", { id: Number(b.dataset.id), status: b.dataset.s });
    if (res.ok) { toast(`<b>[SYSTEM]</b> ${esc(t("Proposal #{id} {s}.", { id: b.dataset.id, s: t(b.dataset.s) }))}`); loadEvolution(); loadNotifications(); }
  }));
  $("evoReport").innerHTML = d.report ? `<span class="muted">${t("Last run")}</span><b>${esc(d.report.name)}</b><span class="muted">${t("Result")}</span><b>${esc(d.report.result)}</b>`
    : `<span class="muted">${t("Last run")}</span><b>${t("never")}</b>`;
  $("evoDrafts").innerHTML = [["Skill drafts", d.drafts.skills], ["Specialist drafts", d.drafts.agents], ["Issue drafts", d.drafts.issues]]
    .map(([k, v]) => `<span class="muted">${t(k)}</span><b>${v}</b>`).join("");
}

// ---- tool scout
async function loadTools() {
  const r = await api("/api/tools");
  if (!r.ok) return;
  const btn = (x, action, label) => `<button class="btn ghost tool" data-n="${esc(x.name)}" data-a="${action}">${t(label)}</button>`;
  const tr = t; // `t` is a tool row below
  $("toolList").innerHTML = r.data.tools.map((t) => `
    <tr><td><b>${esc(t.name)}</b><br><span class="small faint">${esc(t.why)}</span>
      ${t.status === "approved" && !t.installed ? `<br><code class="sys">${esc(t.auto || t.install)}</code>` : ""}</td>
    <td>${esc(t.capability)}</td>
    <td>${t.installed ? `<span class="pill ok">${tr("yes")}</span>` : `<span class="pill">${tr("no")}</span>`}</td>
    <td title="${esc(t.trust_reasons.join(" · "))}">${t.trust == null ? "?" : `<span class="pill ${t.trust >= 70 ? "ok" : t.trust >= 40 ? "warn" : "bad"}">${t.trust}</span>`}</td>
    <td>${t.usage ? `${t.usage.passed}/${t.usage.runs}` : "-"}</td>
    <td>${t.status ? `<span class="pill ${t.status === "blacklisted" ? "bad" : "ok"}">${esc(tr(t.status))}</span>` : "-"}</td>
    <td>${btn(t, "trust", "Trust")} ${t.installed ? btn(t, "vet", "Vet") : ""}
      ${t.status !== "approved" && !t.installed ? btn(t, "approved", "Approve") : ""}
      ${t.status === "approved" && !t.installed && t.auto ? btn(t, "install", "Install") : ""}
      ${t.by_tidos ? btn(t, "uninstall", "Uninstall") : ""}
      ${t.status === "blacklisted" ? btn(t, "none", "Unban") : btn(t, "blacklisted", "Ban")}</td></tr>`).join("");
  const rows = Object.fromEntries(r.data.tools.map((x) => [x.name, x]));
  $("toolList").querySelectorAll(".tool").forEach((b) => b.addEventListener("click", async () => {
    const tool = rows[b.dataset.n];
    if (b.dataset.a === "install" && !confirm(`${t("Install {name}?", { name: tool.name })}\n\n${tool.auto}\n\n${t("Trust {n}/100. Your user account only, no administrator rights. Logged; Uninstall removes it.", { n: tool.trust ?? "?" })}`)) return;
    if (b.dataset.a === "uninstall" && !confirm(t("Uninstall {name}?", { name: tool.name }))) return;
    b.disabled = true;
    if (b.dataset.a === "install") toast(`<b>[SYSTEM]</b> ${esc(t("Installing {name}… (can take a few minutes)", { name: tool.name }))}`);
    const res = await api("/api/tools/action", { name: b.dataset.n, action: b.dataset.a });
    if (!res.ok) { b.disabled = false; toast(`<b>[SYSTEM]</b> ${esc(b.dataset.n)}: ${esc(t(res.data.error || "failed"))}`, "warn"); return; }
    if (b.dataset.a === "install" || b.dataset.a === "uninstall") {
      const d = res.data;
      toast(`<b>[SYSTEM]</b> ${esc(b.dataset.n)}: ${esc(t(d.detail))}${d.vet ? ` · vet ${d.vet.ok ? "PASS" : "FAIL"} ${esc(d.vet.version || "")}` : ""}`, d.ok ? "" : "warn");
      loadTools();
      return;
    }
    if (res.ok) {
      const d = res.data;
      const msg = b.dataset.a === "trust" ? `trust ${d.score ?? "?"}` : b.dataset.a === "vet" ? `vet ${d.ok ? "PASS" : "FAIL"}: ${d.detail}` : b.dataset.a;
      toast(`<b>[SYSTEM]</b> ${esc(b.dataset.n)}: ${esc(msg)}`);
      loadTools();
    }
  }));
}

// ---- shadow army + memory
async function loadArmy() {
  const r = await api("/api/army");
  if (!r.ok) return;
  $("army").innerHTML = r.data.units.map((u) => `
    <div class="row"><span class="rank ${esc(u.rank)}">${esc(u.rank)}</span>
      <span class="name"><b>${esc(u.name)}</b> <span class="faint small">${esc(u.description)}</span></span>
      <span class="pill ${u.state === "draft" ? "warn" : "ok"}">${esc(t(u.state))}</span>
      <span class="pill">LV ${u.level}</span>
      <span class="pill">${lang === "ar" ? t("{n} mission(s)", { n: u.missions }) : `${u.missions} mission${u.missions === 1 ? "" : "s"}`}</span></div>`).join("")
    || `<p class="muted">${t("No subagents yet.")}</p>`;
}

async function showUnit(name, kind) {
  $("armyTitle").textContent = name;
  if (kind === "lessons") {
    const r = await api("/api/army/lessons?name=" + encodeURIComponent(name));
    $("armyView").textContent = r.ok ? r.data.text : t("No lessons yet (no recorded missions).");
  }
  document.querySelectorAll("#armyList tr").forEach((tr) => tr.classList.toggle("sel", tr.dataset.name === name));
}

async function loadArmyTab() {
  const r = await api("/api/army");
  if (!r.ok) return;
  const activated = new Set(r.data.activated);
  const units = Object.fromEntries(r.data.units.map((u) => [u.name, u]));
  const pct = (v) => v === null ? '<span class="faint">—</span>' : `<span class="pill ${v >= 0.6 ? "ok" : v <= 0.4 ? "bad" : "warn"}">${Math.round(v * 100)}%</span>`;
  const trial = (x) => !x ? '<span class="faint">—</span>'
    : `<span class="pill ${x.passed ? "ok" : "bad"}" title="${esc(x.agent)} · ${x.tasks} dungeons">${x.unit}% / ${x.plain}%</span>`;
  $("armyList").innerHTML = r.data.units.map((u) => `
    <tr data-name="${esc(u.name)}"><td><span class="rank ${esc(u.rank)}">${esc(u.rank)}</span></td>
      <td><b>${esc(u.name)}</b><br><span class="small faint unit-desc" title="${esc(u.description)}">${esc(u.description || (u.projects || []).join(", "))}</span></td>
      <td><span class="pill ${u.state === "active" ? "ok" : u.state === "draft" ? "warn" : ""}">${esc(t(u.state))}</span></td>
      <td class="nowrap">LV ${u.level} · ${fmt(u.xp)}</td><td>${fmt(u.missions)}</td><td>${pct(u.success)}</td><td>${trial(u.trial)}</td>
      <td>${u.has_lessons ? `<button class="btn ghost unit" data-a="lessons" data-n="${esc(u.name)}">${t("Lessons")}</button>` : ""}
        ${u.state === "draft" ? `<button class="btn ghost unit" data-a="activate" data-n="${esc(u.name)}">ARISE</button>` : ""}
        ${activated.has(u.name) ? `<button class="btn ghost unit" data-a="deactivate" data-n="${esc(u.name)}">${t("Deactivate")}</button>` : ""}</td></tr>`).join("")
    || `<tr><td colspan="8" class="muted">${t("No subagents yet.")}</td></tr>`;
  $("armyList").querySelectorAll(".unit").forEach((b) => b.addEventListener("click", async () => {
    const u = units[b.dataset.n];
    if (b.dataset.a === "lessons") return showUnit(u.name, "lessons");
    if (b.dataset.a === "activate") {
      const tr = u.trial;
      const msg = tr ? t("Activate {name}? Trial: {u}% with it vs {p}% plain on {n} dungeons.", { name: u.name, u: tr.unit, p: tr.plain, n: tr.tasks })
        : t("Activate {name}? It has NOT been trialled. Trial it first with: tidos_evals run --agent claude:haiku --unit {name}", { name: u.name });
      if (!confirm(msg)) return;
    }
    if (b.dataset.a === "deactivate" && !confirm(t("Deactivate {name}? Its draft is kept.", { name: u.name }))) return;
    b.disabled = true;
    const res = await api("/api/army/action", { name: u.name, action: b.dataset.a });
    toast(`<b>[SYSTEM]</b> ${esc(res.ok ? (b.dataset.a === "activate" ? t("ARISE: {name} joined your army.", { name: u.name }) : t("{name} returned to the drafts.", { name: u.name })) : t(res.data.error || "failed"))}`, res.ok ? "" : "warn");
    loadArmyTab(); loadArmy();
  }));
}

async function showMemory(path) {
  const r = await api("/api/memory/file?path=" + encodeURIComponent(path));
  $("memTitle").textContent = path;
  $("memView").textContent = r.ok ? r.data.text : t("Not found.");
  document.querySelectorAll("#memList tr").forEach((tr) => tr.classList.toggle("sel", tr.dataset.path === path));
}

async function loadMemory() {
  const r = await api("/api/memory");
  if (!r.ok) return;
  $("memList").innerHTML = r.data.items.map((m) => `
    <tr data-path="${esc(m.path)}"><td>${esc(m.path)}</td><td><span class="pill">${esc(m.kind)}</span></td><td>${m.lines}</td></tr>`).join("")
    || `<tr><td colspan="3" class="muted">${t("Memory is empty.")}</td></tr>`;
  $("memList").querySelectorAll("tr[data-path]").forEach((tr) => tr.addEventListener("click", () => showMemory(tr.dataset.path)));
}

// ---- playbooks
async function showPlaybook(path) {
  const r = await api("/api/playbook?path=" + encodeURIComponent(path));
  $("pbTitle").textContent = path;
  $("pbView").textContent = r.ok ? r.data.text : t("Not found.");
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
    || `<tr><td colspan="7" class="muted">${t("Nothing learned yet. Work with a strong model, then START TIDOS.")}</td></tr>`;
  $("pbMeta").textContent = t("{n} playbooks in {dir} · served = times a GUIDE brief gave it to a weaker model · switched off = never served.", { n: items.length, dir: r.data.dir });
  $("pbList").querySelectorAll("tr[data-path]").forEach((tr) => tr.addEventListener("click", (ev) => {
    if (!ev.target.classList.contains("toggle")) showPlaybook(tr.dataset.path);
  }));
  $("pbList").querySelectorAll(".toggle").forEach((btn) => btn.addEventListener("click", async () => {
    const disabled = btn.classList.contains("on");
    const res = await api("/api/playbooks/toggle", { path: btn.dataset.path, disabled });
    if (res.ok) { toast(`<b>[SYSTEM]</b> ${t(disabled ? "Playbook switched off." : "Playbook switched on.")}`); loadPlaybooks(); }
  }));
}

// ---- security
// ---- ask TIDOS + global search
let askMode = "ask";
const KIND_VIEW = { playbook: "playbooks", memory: "memory", eval: "dungeons", proposal: "evolution", task: "live" };

async function runAsk() {
  const q = $("askQ").value.trim();
  if (!q) return;
  $("askOut").classList.remove("hidden");
  if (askMode === "ask") {
    $("askTitle").textContent = t("Ask TIDOS");
    $("askBody").innerHTML = `<p class="muted">${t("Thinking over your traces…")}</p>`;
    const r = await api("/api/ask", { question: q, lang });
    if (!r.ok) { $("askBody").innerHTML = `<p class="lift-down">${esc(t(r.data.error || "failed"))}</p>`; return; }
    $("askBody").innerHTML = `<div class="answer">${esc(r.data.answer)}</div>
      <details class="mt"><summary class="small faint">${t(r.data.source === "llm" ? "Data TIDOS used (sent to the model)" : "Data TIDOS used (local only)")}</summary>
      <pre class="console">${esc(r.data.digest)}</pre></details>`;
    return;
  }
  $("askTitle").textContent = t("Search");
  const r = await api("/api/search?q=" + encodeURIComponent(q));
  if (!r.ok) return;
  $("askBody").innerHTML = r.data.results.map((h) => `
    <div class="hit"><span><span class="pill">${esc(h.kind)}</span></span>
      <div><a href="#" class="hitlink" data-kind="${esc(h.kind)}" data-path="${esc(h.path || "")}">${esc(h.title)}</a>
      <div class="detail">${esc([h.project, h.when, h.detail].filter(Boolean).join(" · "))}</div></div></div>`).join("")
    || `<p class="muted">${esc(t("No match for: {w}", { w: r.data.words.join(" ") }))}</p>`;
  $("askBody").querySelectorAll(".hitlink").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    const tab = document.querySelector(`.tab[data-view=${KIND_VIEW[a.dataset.kind]}]`);
    if (tab) tab.click();
    if (a.dataset.kind === "memory" && a.dataset.path) showMemory(a.dataset.path);
  }));
}

// ---- settings + backups
async function loadSettings() {
  const r = await api("/api/settings");
  if (!r.ok) return;
  $("settings").innerHTML = r.data.settings.map((s) => {
    let input;
    if (s.type === "bool") input = `<select data-key="${esc(s.key)}" data-type="bool"><option value="true" ${s.value ? "selected" : ""}>true</option><option value="false" ${s.value ? "" : "selected"}>false</option></select>`;
    else if (s.type === "int") input = `<input type="number" data-key="${esc(s.key)}" data-type="int" min="${s.range[0]}" max="${s.range[1]}" value="${s.value}">`;
    else input = `<select data-key="${esc(s.key)}" data-type="str">${s.choices.map((c) => `<option ${c === s.value ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>`;
    return `<div class="setting"><div><b>${esc(s.key)}</b><div class="small muted">${esc(t(s.help))}</div></div>${input}</div>`;
  }).join("");
  $("settings").querySelectorAll("[data-key]").forEach((el) => el.addEventListener("change", async () => {
    const value = el.dataset.type === "bool" ? el.value === "true" : el.dataset.type === "int" ? Number(el.value) : el.value;
    const res = await api("/api/settings", { key: el.dataset.key, value });
    $("settingsMsg").className = "msg " + (res.ok ? "ok" : "err");
    $("settingsMsg").textContent = res.ok ? t("Saved {k} = {v}", { k: el.dataset.key, v: value }) : t(res.data.error);
    if (!res.ok) loadSettings();
  }));
}

function renderBackups(list) {
  $("backups").innerHTML = list.length ? `<div class="kv">${list.map((b) => `<span class="muted">${esc(b.name)}</span><b>${(b.bytes / 1e6).toFixed(1)} MB</b>`).join("")}</div>`
    : `<p class="muted">${t("No backups yet.")}</p>`;
}

async function loadBackups() {
  const r = await api("/api/backups");
  if (r.ok) renderBackups(r.data.backups);
}

async function loadSecurity() {
  loadSettings();
  loadBackups();
  const r = await api("/api/security");
  if (!r.ok) return;
  const d = r.data;
  $("switches").innerHTML = d.switches.map((s) => `
    <div class="switch"><div class="d"><b>${esc(s.name)}</b><span class="small muted">${esc(t(s.description))}</span></div>
      <span class="pill ${s.on === s.default ? "" : "warn"}">${t(s.on === s.default ? "default" : "changed")}</span>
      <button class="toggle ${s.on ? "on" : ""}" data-name="${esc(s.name)}" aria-label="toggle ${esc(s.name)}" aria-pressed="${s.on}"></button></div>`).join("");
  $("switches").querySelectorAll(".toggle").forEach((btn) => btn.addEventListener("click", async () => {
    const on = !btn.classList.contains("on");
    const res = await api("/api/switches", { name: btn.dataset.name, on });
    if (res.ok) { toast(`<b>[SYSTEM]</b> ${esc(btn.dataset.name)} → ${on ? t("ON") : "OFF"}`); loadSecurity(); }
  }));
  $("secInfo").innerHTML = [
    ["Player", esc(d.session.email)], ["Session ends in", t("{n} min", { n: Math.floor(d.session.expires_in / 60) })],
    ["Lock", d.locked_until ? `<span class="pill bad">${esc(t("locked until {w}", { w: when(d.locked_until) }))}</span>` : `<span class="pill ok">${t("open")}</span>`],
    ["Attempts before lockout", d.failures_left], ["Brain", `${esc(d.brain.path)} · ${fmt(d.brain.size_kb)} KB`],
  ].map(([k, v]) => `<span class="muted">${t(k)}</span><b>${v}</b>`).join("");
  $("secLog").innerHTML = d.log.map((e) => `
    <tr><td>${esc(e.ts)}</td><td><span class="pill ${/fail|mismatch|rejected|lockout|blocked/.test(e.event) ? "bad" : /ok|set|changed/.test(e.event) ? "ok" : ""}">${esc(e.event)}</span></td><td>${esc(e.detail)}</td></tr>`).join("");
}

$("changeForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const msg = $("changeMsg");
  if ($("chgpw").value !== $("chgpw2").value) { msg.className = "msg err"; msg.textContent = t("New passwords do not match."); return; }
  const r = await api("/api/auth/change", { current: $("curpw").value, new: $("chgpw").value });
  for (const id of ["curpw", "chgpw", "chgpw2"]) $(id).value = "";
  msg.className = "msg " + (r.ok ? "ok" : "err");
  msg.textContent = r.ok ? t("Password changed.") : t(r.data.error || "Failed.");
  loadSecurity();
});

// ---------------------------------------------------------------- boot
(async function boot() {
  applyStatic();
  wireSwitches();
  const r = await api("/api/boot");
  if (!r.ok) { setMsg("Control center unavailable.", "err"); return; }
  firebaseAuth = getAuth(initializeApp(r.data.firebase));
  if (r.data.stage === "app") return startApp();
  showLogin(r.data.stage, r.data);
})();
