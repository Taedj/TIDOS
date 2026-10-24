# TIDOS Enhancement Plan (v4.1 → v6.0)

> **Source**: Deep review + design discussion (2026-10-24).
> **Rule**: Each task is checked `[x]` only when it is implemented **and verified** (tests/commands pass, or the user confirmed).
> Append the completion date and evidence after the task, e.g. `— done 2026-10-25 (pytest 95/95)`.
> **North star**: TIDOS must *enforce* (code, hooks, tools, evals), not only *request* (prose).

---

## Progress Overview

| Phase | Name | Goal | Status |
| :--- | :--- | :--- | :--- |
| 0 | Review & Design | Understand TIDOS, agree on the vision | ✅ Done |
| 1 | v4.1 — Fix & Clean | Stop data loss, security holes, inconsistencies | 🔄 In progress (9/30) |
| 2 | Brain & Traces | Record every task outside the repo (`~/.tidos/brain.db`) | 🔄 In progress (7/11 — 2.3 waits for hook install) |
| 3 | `/TIDOSZIT` Control Center (core) | Secure dashboard: Google + Firestore password gate | 🔄 In progress (13/15) |
| 4 | v4.5 — Measure (Evals / Dungeons) | Ground-truth scoring of models and TIDOS | 🔄 In progress (5/8) |
| 5 | LEARN mode | TIDOS learns from strong-model sessions (START TIDOS) | 🔄 In progress (5/9) |
| 6 | GUIDE mode | TIDOS detects weak models and guides them with the user | 🔄 In progress (2/9) |
| 7 | v5.0 — Runtime (MCP, Hooks, Plugin, Subagents) | Make TIDOS a real agent kernel | ⬜ Not started |
| 8 | Skills Library | Feed TIDOS reusable `SKILL.md` skills | ⬜ Not started |
| 9 | v5.5 — Solo Leveling (Auto-Learn) | XP, ranks, eval-gated promotion | ⬜ Not started |
| 10 | Auto-Develop | Self-PR bot, mutation testing, scheduled quests | ⬜ Not started |
| 11 | Tool Scout | Auto-discover, vet, propose tools | ⬜ Not started |
| 12 | Control Center (full) | All dashboard panels | ⬜ Not started |
| 13 | v6.0 — Swarm & TIDOS-native Model | Federated community + fine-tuned model | ⬜ Not started |

---

## Phase 0 — Review & Design ✅

- [x] **0.1** Deep review of the TIDOS codebase (docs, core, engines, scripts, browser relay) — done 2026-10-24
- [x] **0.2** Run the relay test suite — done 2026-10-24 (pytest 89/89)
- [x] **0.3** Write the v5 vision (agent kernel, auto-learn, auto-develop, LLM growth, subagents, skills, tool scout) — done 2026-10-24
- [x] **0.4** Design "learn from strong models → drive weak models" pipeline — done 2026-10-24
- [x] **0.5** Design the `/TIDOSZIT` control center and its security model — done 2026-10-24
- [x] **0.6** Write this plan (`docs/ENHANCEMENT_PLAN.md`) — done 2026-10-24
- [ ] **0.7** User answers open questions (see [Open Questions](#open-questions)) — Q1, Q2, Q3 answered 2026-10-24; Q4 pending

---

## Phase 1 — v4.1: Fix & Clean

### 1A. Critical bugs (data loss & broken code)
- [x] **1.1** `scripts/sanitizer.py:43` — fix `\U` bad-escape crash in `sanitize_text()` (`--sanitize` mode crashes on every input) — done 2026-10-24 (regression test `test_does_not_crash_on_plain_text`; also fixed Windows user names with spaces, e.g. `C:\Users\Dr Jane Doe`)
- [x] **1.2** `scripts/sanitizer.py:161` — fix `%e` format bug in error handler (use `%s`) — done 2026-10-24
- [x] **1.3** `scripts/sanitizer.py` — use `ALLOWED_DIRECTORIES`; add path/PII checks to `--check` mode — done 2026-10-24 (dir whitelist on by default, `--any-dir` to scan elsewhere; user paths, e-mails, non-loopback IPs flagged)
- [ ] **1.4** *(partial 2026-10-24: new patterns + false-positive fixes done and tested; gitleaks hook written but **unverified** — gitleaks is not installed on this machine)* Sanitizer detection: integrate **gitleaks** (or trufflehog) as primary scanner; keep regex as fallback; add patterns for `sk-ant-`, `AKIA…`, JWT `eyJ…`, Slack `xox?-`; remove false positives on prose ("Bearer tokens", "password: never hardcode")
- [x] **1.5** Add `tests/test_sanitizer.py` covering crash, true positives, false positives — done 2026-10-24 (13 tests + 19 subtests pass; full suite 102/102)
- [x] **1.6** `scripts/update.ps1` / `update.sh` — remove `"."` from candidate paths; refuse to run if the directory is not a genuine TIDOS checkout — done 2026-10-24 (markers: `TIDSTART.md` + `core/kernel.md` + `config/framework.md`; git must be the directory's own top-level, never a parent project)
- [x] **1.7** `scripts/update.ps1` / `update.sh` — never `git remote set-url`; abort with a clear message if `origin` is not TIDOS (protects forks and user projects) — done 2026-10-24
- [x] **1.8** `scripts/update.ps1` / `update.sh` — `git clean` must never delete untracked `personas/tidos*.md` (generated personas) — done 2026-10-24 (`git clean` removed entirely: untracked files are always user work; update is also skipped when tracked system files have local edits or commits are unpushed)
- [x] **1.9** `scripts/update.ps1` — stop silencing errors (`2>$null`) on backup/restore of `memory/` and `evolution/`; abort if backup fails — done 2026-10-24 (both `.ps1` and `.sh`; a restore failure keeps the backup and prints its path). Verified by `tests/update_gate_scenarios.sh`: sh 8/8, ps1 8/8

### 1B. Security
- [x] **1.10** Update gate: pin to **signed release tags** instead of `main`; show a diff and require user approval before applying — done 2026-10-24 (channel `release` = newest vX.Y.Z tag by default, `main` for maintainers; update is REPORTED (commits, diffstat, tag signature) and installed only with `-Apply`/`-ApplyUpdate`; `TIDOS_REQUIRE_SIGNED=1` refuses unsigned tags; never downgrades a newer checkout; scenarios sh 12/12, ps1 12/12)
- [x] **1.11** `scripts/factory_sync.ps1` / `.sh` — stop auto-pushing to `main`; open a PR instead — done 2026-10-24 (persona on a `persona/<name>-<date>` branch + `gh pr create` or compare link; firewall on all 3 files in both scripts. Found and fixed on the way: bash version never ran the firewall, never detected new personas (`sed` `\?` bug), PowerShell crashed on git push output under `ErrorActionPreference=Stop`, bash scripts called `python3` which does not exist in Git Bash on Windows, sanitizer whitelist broke on 8.3 short paths. Verified in a temp repo with a fake remote: sh + ps1 open a branch, main untouched, leaked key rejected)
- [x] **1.12** `scripts/google_auth_server.py` — add `state` nonce to `/callback`, verify the ID token server-side, reject unexpected origins — done 2026-10-24 (one-time `state` nonce embedded in the page, Host + Origin checks, ID token verified server-side with Google (Identity Toolkit), identity taken from Google not from the page; `tests/test_auth_server.py`)
- [x] **1.13** Store the refresh token securely (OS keyring via `keyring`, or at least restricted file permissions) — done 2026-10-24 (session file ACL restricted to the current Windows user via `icacls` (chmod 600 elsewhere), verified; the short-lived ID token is no longer stored)
- [x] **1.14** `scripts/auth_verify.ps1` / `.sh` — remove `-Password` CLI argument (shell history leak); prompt securely instead — done 2026-10-24 (no `-Password` argument: hidden prompt (`Read-Host -AsSecureString` / `read -rs`), and it fails fast instead of hanging when an agent runs it without a keyboard)
- [x] **1.15** Make the Google auth gate **opt-in** (required only for features that need identity: community sync, `/TIDOSZIT`) — done 2026-10-24 (`auth_gate` kill switch, OFF by default, editable in /TIDOSZIT; START TIDOS asks for Google sign-in only when it is on; /TIDOSZIT keeps its own owner login)
- [x] **1.16** `browser_relay/` (GPTID) — experimental, off by default, ToS risk documented — done 2026-10-24 (`gptid` switch OFF by default and enforced in `scripts/gptid.*`; `docs/gptid.md` status banner: ToS risk, fragility, third-party data, supported alternative = second model via official API/CLI, planned in Phase 7)
- [x] **1.17** `personas/tidostrade.md` — add risk disclaimer and "paper-trading only / never execute real trades" constraint — done 2026-10-24 (risk notice + hard constraints at the top of `personas/tidostrade.md`: never trade real money or change credentials/limits, research/backtest/paper mode only, explicit written OK per live action, no guaranteed-profit claims)

### 1C. Privacy
- [x] **1.18** Remove personal project data from the public repo (`memory/LESSONS.md`, `memory/PROJECT_HISTORY.md`, `memory/USER_PROFILE.md`, etc.); ship only empty templates — done 2026-10-24 (repo memory/ holds templates only; ULTIDOS_persona.md (jailbreak-style prompt with a plain-text password) removed from the repo and kept only privately - treat that password as public)
- [x] **1.19** Move user memory to `~/.tidos/memory/` (outside repo); add `memory/*` user files to `.gitignore` — done 2026-10-24 (tidos_session/memory.py: START TIDOS migrates personal memory to ~/.tidos/memory/ without overwriting; rule memory/X.md = ~/.tidos/memory/X.md in TIDSTART + memory/README; uncommitted edits preserved (37/37 lines); test added)
- [ ] **1.20** *(waiting for the user: needs git filter-repo + force-push of the public repo; personal files and the ULTIDOS password stay in git history until then)* Purge personal data from git history (optional, `git filter-repo`) — needs user approval

### 1D. Consistency & cleanup
- [ ] **1.21** Unify version numbers everywhere (README, TIDSTART, VERSION, engines, start banners) — single source in `config/framework.md`
- [ ] **1.22** Remove or archive the duplicated legacy `.tidos/` tree; reconcile `plugins/` vs `.tidos/plugins/` (keep `figma.md`, `github.md`)
- [ ] **1.23** Fix `README.md` (duplicate `examples/` line, false CI/CD claim)
- [ ] **1.24** Fix `docs/tools/claude-code.md` (wrong URL `tidjani/TIDOS`; no `systemPrompt` setting — use `CLAUDE.md` / skills / hooks / plugin)
- [ ] **1.25** Audit and fix all other `docs/tools/*.md` guides against each tool's real configuration
- [ ] **1.26** Mark the "80/80 weak model benchmark" in `docs/THE_BIG_IDEA.md` as unverified until Phase 4 produces real numbers

### 1E. CI
- [x] **1.30** *(found and fixed 2026-10-24)* `scripts/factory_sync.ps1` never parsed on Windows since v4.0 (unclosed `if` block + UTF-8 `✓` read as a smart quote by PowerShell 5.1) — fixed; all `.ps1` files now parse and are ASCII-only. CI should run a PowerShell parse check (see 1.27)
- [ ] **1.27** Add `.github/workflows/ci.yml`: pytest, ruff, markdown-lint, link check, gitleaks secret scan, PowerShell lint (PSScriptAnalyzer), shellcheck
- [ ] **1.28** Add persona/skill schema validator (required sections, routing signals) to CI
- [ ] **1.29** Release v4.1.0 (changelog, tag)

---

## Phase 2 — Brain & Traces (foundation for learning + dashboard)

- [x] **2.1** Design `~/.tidos/brain.db` SQLite schema: `sessions`, `tasks`, `steps`, `tool_calls`, `verifications`, `corrections`, `playbooks`, `facts`, `models`, `evals`, `xp_events`, `security_log` — done 2026-10-24 (`tidos_brain/db.py`, schema v1 via `PRAGMA user_version`; corrections stored as `tasks.corrected`, steps as `tool_calls`; also `live_events` for the Live Monitor; WAL mode for hooks + dashboard)
- [x] **2.2** Implement `tidos_brain` Python package (stdlib `sqlite3`, migrations, typed API) — done 2026-10-24 (CLI: `hook`, `import-claude`, `stats`, `prune`, `install-hooks`)
- [ ] **2.3** *(partial 2026-10-24: hook handler + safe installer built and tested — PostToolUse ~300 ms, Stop returns in ~480 ms with background import, never prints or fails; installer keeps existing hooks, backs up settings, `--uninstall` restores. **Waiting for user approval to install into `~/.claude/settings.json`.**)* Trace collector — **Claude Code**: `PostToolUse` / `Stop` / `UserPromptSubmit` hooks writing to brain.db
- [x] **2.4** Trace collector — Claude Code transcript importer (`~/.claude/projects/*.jsonl`) — done 2026-10-24 (real history: 11 sessions → 248 tasks in 3.3 s; skips sidechains/injected messages; dedupes split messages; counts cached tokens)
- [ ] **2.5** Trace collector — Gemini CLI session logs
- [ ] **2.6** Trace collector — OpenAI Codex / OpenCode session logs
- [ ] **2.7** Trace collector — API router (LiteLLM proxy) for Grok / OpenRouter / Ollama requests
- [x] **2.8** Outcome scoring: verify-pass, user-accepted, retries, reverts, user corrections → `task.score` — done 2026-10-24 (v1 heuristics in `tidos_brain/scoring.py`: tests/lint/build detection, pass/fail parsing, EN+FR correction detection, tool errors; first run on real history: 56 success / 25 failure / 167 unknown)
- [x] **2.9** Privacy: sanitizer runs on every trace before storage; secrets never stored — done 2026-10-24 (scan of the real import: **0 leaks**; sanitizer extended to redact this machine's user name in every spelling — spaces, dashes, Claude's `C--Users-…` encoding, 8.3 short name; home-folder sessions stored as project `~`)
- [x] **2.10** Retention & size limits (rotate/compact old traces) — done 2026-10-24 (`prune --live-days 14 --session-days N` + VACUUM; tested)
- [x] **2.11** Tests for brain package and collectors — done 2026-10-24 (`tests/test_brain.py`; full suite 116 passed, 23 subtests)

---

## Phase 3 — `/TIDOSZIT` Control Center (core)

### 3A. Security gate
- [x] **3.1** Firestore document `admin/tidoszit` = `{ hash, salt, algo, iterations, updatedAt }` (never the plaintext password) — done 2026-10-24 (format implemented + tested; the document itself is created by the first-run setup in the browser)
- [ ] **3.2** *(partial 2026-10-24: `firebase/firestore.rules` (owner-only `admin/*`, deny everything else) + `firebase/firebase.json` written. **Deploy blocked for the agent (production deploy) — user runs it.**)* Firestore security rules: `admin/*` readable/writable **only** by the owner UID; deploy to `tidos-framework`
- [x] **3.3** `scripts/tidoszit_setpass.py` — set/change password locally (PBKDF2-SHA256 or argon2), writes only the hash — done 2026-10-24 (design change: no CLI script (a password typed in a terminal can end up in AI transcripts) — first-run setup + "Change password" happen in the browser; PBKDF2-SHA256 600k iterations)
- [x] **3.4** Login step 1: Google sign-in, must match owner UID — done 2026-10-24 (server verifies the ID token with Google (Identity Toolkit) and requires uid == owner_uid)
- [x] **3.5** Login step 2: password typed **in the browser** (never through the AI chat/terminal) and verified against the Firestore hash — done 2026-10-24 (hash read from Firestore with the owner token, constant-time compare)
- [x] **3.6** Session cookie (HttpOnly, SameSite=Strict, 30-min expiry), bound to `127.0.0.1` only — done 2026-10-24 (HttpOnly + SameSite=Strict, 5-min pending + 30-min full session, 127.0.0.1 only; plus Host check (DNS rebinding), Origin check (CSRF), CSP, X-Frame-Options)
- [x] **3.7** Brute-force protection: 5 failures → 15-min lockout; every attempt logged in `security_log` — done 2026-10-24 (lockout persisted in brain.security_log (survives restarts); refused attempts during lockout do not extend it)
- [x] **3.8** Security tests (wrong UID, wrong password, lockout, expired session, CSRF) — done 2026-10-24 (`tests/test_dashboard.py` 11 tests: wrong account, forged token, CSRF, bad Host, lockout, setup replay, expiry, path traversal; suite 127 passed)

### 3B. Command & app
- [x] **3.9** `/TIDOSZIT` slash command for Claude Code (`.claude/commands` or skill) + `scripts/tidoszit.ps1` / `.sh` for other tools — done 2026-10-24 (`.claude/commands/TIDOSZIT.md` (works inside the TIDOS repo; copy to `~/.claude/commands/` for every project) + `scripts/tidoszit.ps1` / `.sh` (background start, `-Stop`))
- [x] **3.10** Backend: FastAPI + SQLite (reads brain.db), WebSocket live stream — done 2026-10-24 (design change (Q3): Python stdlib `ThreadingHTTPServer` + Server-Sent Events instead of FastAPI/WebSocket — zero dependencies, offline)
- [x] **3.11** Frontend: React + Tailwind, dark "System Window" theme (Solo Leveling style), built and served locally — done 2026-10-24 (design change (Q3): plain HTML/CSS/JS, no build step; "System Window" theme; verified with Playwright screenshots desktop + mobile, 0 console/CSP errors, no horizontal overflow)
- [x] **3.12** Panel: 🜲 **Status Window** (level, XP bar, rank, today's quests, recent level-ups) — done 2026-10-24 (level / XP / E-S rank, 5 stats (INT PRE DIS WIS AGI), daily quests, domains, models, quest log — provisional XP from task scores until Phase 9)
- [x] **3.13** Panel: 📡 **Live Monitor** (running sessions, current step, active model, gates, live log; pause/kill) — done 2026-10-24 (active sessions, live SSE event stream, recent tasks table; "kill session" replaced by the tracing pause switch (a running Claude Code session cannot be killed safely from outside))
- [x] **3.14** Panel: 🛡 **Security** + kill switches (auto-update, persona factory, auto-sync, GPTID) — done 2026-10-24 (switches in `~/.tidos/control.json` ENFORCED by code: hook (tracing), start_tidos (auto_update), factory_sync, community_sync, gptid scripts; security log + lock status + change password)
- [ ] **3.15** *(pending: needs hooks installed (2.3) + rules deployed (3.2) + one real Google login by the owner)* End-to-end test: `/TIDOSZIT` → login → see live trace from a real Claude Code session

---

## Phase 4 — v4.5: Measure (Evals = "Dungeons")

- [x] **4.1** Eval task format (task prompt, repo fixture, verify command, expected outcome) — done 2026-10-24 (`evals/dungeons/<suite>/<name>/` = `task.json` + `fixture/` + `hidden/` (tests copied in only AFTER the agent finishes, so they cannot be read or gamed) + `solution/`)
- [x] **4.2** Write 30–50 golden tasks across user stacks — done 2026-10-24 (30 tasks E..S: python 17, teaching 4, javascript 3, sql 2, powershell 2, dart 2; all validated fail-untouched / pass-with-solution)
- [x] **4.3** Eval runner (sandboxed worktree/Docker, runs any model through the router, records results in brain.db) — done 2026-10-24 (`tidos_evals/`: isolated workdirs in `~/.tidos/eval-runs/`, agents `claude:<model>` (restricted tools, budget cap) and `opencode:<provider/model>` (per-run sandbox config, `--dir` + pinned PWD), results in `brain.evals` (schema v2) + per-run logs; `validate` proves every task fails untouched and passes with its reference solution (17/17 valid))
- [ ] **4.4** *(partial 2026-10-24: Claude Haiku 32/32 without TIDOS; Opus/Sonnet/Gemini still to run)* Baseline: strong models (Claude, Gemini, Grok, GPT) **without** TIDOS
- [ ] **4.5** *(in progress 2026-10-24: free `opencode/glm-5.3-flash-free` clean run on 30 tasks; no local Ollama installed)* Baseline: weak/local models (Ollama 7B/8B) **without** TIDOS
- [ ] **4.6** *(partial 2026-10-24: Haiku with TIDOS 31/32 vs 32/32 without, +55% cost, +60% time — no measurable gain from the v4 prose protocol; needs --repeat 3 for significance)* Baseline: same models **with** current TIDOS v4.1 — real answer to the "Big Idea" claim
- [x] **4.7** "Turn a fixed bug into a golden task" helper (every real bug grows the dungeon) — done 2026-10-24 (`tidos_evals new --suite S --name N --source <buggy project>` scaffolds a task (copies the project without .git/node_modules/.env), then `validate`)
- [x] **4.8** Panel: 🏰 **Dungeons** (suites, pass/fail history, regressions, "Run" button) — done 2026-10-24 (Dungeons tab: Arena leaderboard (pass rate without / with TIDOS, lift, cost) + Dungeon map (task x agent matrix); verified with Playwright, no overflow, 0 console errors)

---

## Phase 5 — LEARN mode: TIDOS learns from strong models (START TIDOS on Claude, Gemini Pro…)

> Goal (user, 2026-10-24): develop TIDOS itself. TIDOS learns while a strong model works with the user,
> and later guides weak/free models with that knowledge. No model training, no model benchmarking.

- [x] **5.1** Model & tool detection at START TIDOS: which tool (Claude Code / OpenCode / Gemini CLI…) and which model is running — done 2026-10-24 (`tidos_session`: tool from env/args; model from args, else Claude Code transcript or OpenCode state (`~/.local/state/opencode/model.json`) — weak models do not need to know their own id)
- [x] **5.2** Model registry `models/registry.yaml`: model → tier (frontier / medium / weak), user-editable; unknown models default to "weak" (safe side) — done 2026-10-24 (`config/models.json` (fnmatch rules, first match wins) + user override `~/.tidos/models.json`; unknown -> weak)
- [x] **5.3** Mode switch: frontier → LEARN mode, medium/weak → GUIDE mode; shown in the startup report and the control center — done 2026-10-24 (START TIDOS (`scripts/start_tidos.ps1|.sh`, `-Tool/-Model`) prints the session report + brief; saved to `~/.tidos/session.json` and `brief.md`. Verified live: OpenCode big-pickle -> weak -> GUIDE (ZTAP), this Claude session -> claude-opus-5-5 -> frontier -> LEARN)
- [x] **5.4** Task classifier on traces (task type × stack: bugfix/python, feature/flutter, deploy/firebase, teaching/TP…) — done 2026-10-24 (`tidos_learn/classify.py`: type from request words (EN+FR) and, when words say nothing ("Phase 1", "go"), from actions; stack from files touched and commands)
- [x] **5.5** Playbook distiller: from successful strong-model tasks (brain traces), extract HOW it worked: steps, files it read first, commands it verified with, pitfalls, user corrections → `~/.tidos/playbooks/<type>/<stack>.md` (private, outside repo) — done 2026-10-24 (`tidos_learn/distill.py`: per-project + general playbooks in `~/.tidos/playbooks/` from strong-model successes and verified checks: where the code lives, files read/changed, reusable checks with pass counts, pitfalls (checks that failed first, user corrections, informative failures), example requests. Real history: 24 playbooks (ZTAP 5, Dev/TIDOS 4, SMARTRAD 2, SYLLAB 1 + general))
- [ ] **5.6** *(partial 2026-10-24: LEARN brief asks the strong model to leave advice with `tidos_learn note` (kept across regenerations, ranked first for its project); every START TIDOS re-imports sessions and regenerates playbooks (~3 s). Automatic end-of-session summary by the strong model still to do)* Distillation runs at session end in LEARN mode (the strong model summarizes its own session — cheap, high quality), plus `tidos learn` to process older sessions
- [ ] **5.7** *(partial 2026-10-24: project facts (stack, checks, deploy/git notes) + per-project playbooks + your corrections as pitfalls; learned user preferences still to do)* User & project knowledge: preferences, recurring corrections, project facts (stack, test command, deploy steps) learned per project
- [ ] **5.8** *(partial 2026-10-24: confidence + E-S rank from verified evidence and strong-model share, idempotent regeneration (merges), stale generated playbooks removed, notes kept; decay of unused playbooks still to do)* Playbook quality: confidence from outcomes (verified success, no correction), merge duplicates, decay unused ones
- [ ] **5.9** Panel: 📜 Playbook Library in /TIDOSZIT (view, edit, approve, delete)

---

## Phase 6 — GUIDE mode: TIDOS guides weak/free models with the user

- [x] **6.1** Compact guided brief (< 4 KB, not the 86 KB v4 boot): user profile, project facts, weak-model protocol, top playbooks for this project — done 2026-10-24 (GUIDE brief hard-capped at 4 KB: rules, project facts (stack, check commands, deploy/git notes), matching playbooks from `~/.tidos/playbooks`)
- [x] **6.2** Weak-model protocol (from what the evals showed): one small step at a time, relative paths only, read before edit, run the project's checks after every change, never claim "done" without check output, ask the user when unsure — done 2026-10-24 (7 rules in `tidos_session/brief.py` (small steps, read before edit, relative paths, checks first, verify after every change, never "done" without output, ask on risky actions, stop after 3 identical errors and suggest a strong model))
- [ ] **6.3** Just-in-time guidance: on each user prompt, TIDOS picks the matching playbook and injects only that (Claude Code `UserPromptSubmit` hook; OpenCode/Gemini via MCP tool `tidos_guide(task)`)
- [ ] **6.4** Checks-first for risky tasks: TIDOS asks the model to write/locate the checks before editing (driver lesson: "define done" first)
- [ ] **6.5** Stuck detection: repeated failures / same error loop → TIDOS tells the user and suggests switching to a strong model for this step (or, with consent, asks a strong model for a hint)
- [ ] **6.6** *(partial 2026-10-24: the brief is delivered through START TIDOS output, which works in every tool; `TIDSTART.md` tells agents to follow it and to skip the long specs in GUIDE mode; per-tool files still to do)* Delivery per tool: Claude Code (hooks + CLAUDE.md block), OpenCode (AGENTS.md + instructions + plugin), Gemini CLI (GEMINI.md), others via AGENTS.md
- [ ] **6.7** Every guided session is traced too, so TIDOS learns which guidance helped weak models
- [ ] **6.8** Measure TIDOS guidance with dungeons: free model inside its own agent WITH the TIDOS guide vs WITHOUT (quality check of TIDOS, not a model benchmark)
- [ ] **6.9** Panel: mode, model tier and guidance used per session in the Live Monitor

> Built 2026-10-24 before this realignment and kept as tools: `tidos_driver/` (external orchestrator — its lessons feed 6.2/6.4/6.5),
> `tidos_evals/` dungeons (used by 6.8). Earlier model baselines: Claude Haiku 32/32 without vs 31/32 with the v4 prose protocol
> (+55% cost) → the long v4 boot text does not help; GUIDE mode must be short and task-specific.

---

## Phase 7 — v5.0: Runtime (MCP, Hooks, Plugin, Subagents)

- [ ] **7.1** `tidos-mcp` server with tools: `get_context`, `route_persona`, `plan_gate`, `verify`, `record_outcome`, `recall`, `propose_skill`, `scout_tools`
- [ ] **7.2** `get_context(task)` — retrieval with ~8 KB budget (only relevant rules/personas/skills/playbooks/memory) instead of loading ~86 KB at boot
- [ ] **7.3** Enforcement hooks (Claude Code): `PreToolUse` blocks `Edit/Write` until a plan/grounding record exists
- [ ] **7.4** Enforcement hooks: `Stop` blocks "done" unless `verify` passed
- [ ] **7.5** Convert personas to real subagents: `tidos-architect`, `tidos-reviewer` (read-only), `tidos-tester`, `tidos-security`, `tidos-researcher`, `tidos-uiux`, `tidos-mobile`
- [ ] **7.6** Orchestrator `/tidos <task>`: plan → implement → review → verify → record
- [ ] **7.7** Second-opinion reviewer subagent using a different model via API (replaces GPTID browser automation)
- [ ] **7.8** Package as a **Claude Code plugin** (skills + subagents + hooks + MCP)
- [ ] **7.9** `AGENTS.md` generator for Codex / Cursor / OpenCode / others
- [ ] **7.10** Release v5.0.0

---

## Phase 8 — Skills Library (`SKILL.md`)

### Engineering
- [ ] **8.1** `tdd-loop`
- [ ] **8.2** `bug-rca` (reproduce → bisect → fix → regression test)
- [ ] **8.3** `refactor-safely`
- [ ] **8.4** `dependency-upgrade`
- [ ] **8.5** `perf-profile`
- [ ] **8.6** `api-design`
- [ ] **8.7** `db-migration`
- [ ] **8.8** `release` (semver + changelog + tag)

### User stacks
- [ ] **8.9** `flutter-android` (Gradle/AGP traps)
- [ ] **8.10** `firebase-rules-audit`
- [ ] **8.11** `supabase-rls`
- [ ] **8.12** `tkinter-desktop` (from TP DRIVER lessons)
- [ ] **8.13** `pyinstaller-exe`
- [ ] **8.14** `windows-powershell-pitfalls` (cp1252, quoting, `python -c`)

### Teaching
- [ ] **8.15** `tp-builder` (TP DRIVER moteur rules, auto-verification)
- [ ] **8.16** `exam-generator` with auto-verification

### Meta
- [ ] **8.17** `skill-author` (writes new skills)
- [ ] **8.18** `eval-author` (bug → golden task)
- [ ] **8.19** `memory-compactor`
- [ ] **8.20** `tool-scout` (see Phase 11)

---

## Phase 9 — v5.5: Solo Leveling (Auto-Learn)

- [ ] **9.1** XP engine: +XP first-try verify pass / accepted without edits; −XP reverts, corrections, failed gates
- [ ] **9.2** Global TIDOS level + per-domain levels
- [ ] **9.3** Ranks E→S for every skill, playbook, persona (success rate over N uses)
- [ ] **9.4** Rank-based loading priority (high-rank first, low-rank demoted/archived)
- [ ] **9.5** Reflexion lessons: after failure, write "when X, do Y" with trigger condition
- [ ] **9.6** Voyager-style distillation: pattern succeeds 3+ times → auto-draft `SKILL.md`
- [ ] **9.7** **Eval-gated promotion**: new skill/lesson kept only if eval score improves
- [ ] **9.8** Memory decay: unused / unhelpful facts lose confidence and leave context
- [ ] **9.9** Memory dedup + conflict resolution
- [ ] **9.10** "Job change": domain passes threshold → propose a specialist subagent
- [ ] **9.11** DSPy / GEPA-style prompt optimization of personas & skills against evals
- [ ] **9.12** `TIDOS STATUS` command (terminal version of Status Window)
- [ ] **9.13** Panel: 🧠 **Memory Explorer** (edit/merge/delete/pin, graph view)
- [ ] **9.14** Panel: "Shadow Army" view (subagents as units with level & specialties)

---

## Phase 10 — Auto-Develop

- [ ] **10.1** `evolution/SUGGESTIONS.md` → GitHub Issues (label, score, eval delta)
- [ ] **10.2** Self-PR bot (scheduled agent): implements top suggestion on a branch, runs CI + evals, opens PR with before/after score — **human merges, never pushes to main**
- [ ] **10.3** Mutation testing of the OS: remove a rule → eval drop? If not, propose deletion (keeps TIDOS lean)
- [ ] **10.4** Daily quest: scheduled eval run + regression report (`/schedule` or GitHub Actions)
- [ ] **10.5** Notifications (daily quests, playbooks ready for promotion, regressions)
- [ ] **10.6** Panel: 🧬 **Evolution Queue** (approve → PR, reject)

---

## Phase 11 — Tool Scout

- [ ] **11.1** Need sensing (missing capability from task/stack, e.g. "no secret scanner", "no linter")
- [ ] **11.2** Search: GitHub API, MCP registries, awesome-lists
- [ ] **11.3** Trust score: stars, recent commits, license, maintainers, OSV / OpenSSF Scorecard
- [ ] **11.4** Sandbox vetting (Docker/worktree): install, smoke test, permission check
- [ ] **11.5** Propose install + config to user — **never auto-install without approval**
- [ ] **11.6** Learn: tool XP (helped or not), blacklist bad tools
- [ ] **11.7** Integrate starter toolset: gitleaks, semgrep, ruff, mypy/pyright, pytest, ast-grep, tree-sitter, ripgrep, Playwright MCP, GitHub MCP, Context7, Serena, promptfoo/inspect-ai, LiteLLM, Ollama
- [ ] **11.8** Panel: 🛰 **Tool Scout** (trust score, install, sandbox-test, blacklist)

---

## Phase 12 — Control Center (full)

- [ ] **12.1** "Ask TIDOS" bar (natural-language questions over traces: "why did Flutter tasks fail this week?")
- [ ] **12.2** Global search across traces, playbooks, memory, evals
- [ ] **12.3** Settings editor for `config/framework.md` values (with validation)
- [ ] **12.4** Export / backup / restore of brain.db
- [ ] **12.5** Mobile-friendly layout
- [ ] **12.6** Dashboard E2E tests (Playwright)

---

## Phase 13 — v6.0: Swarm & TIDOS-native Model

- [ ] **13.1** Community skills/playbooks submitted as PRs, accepted only if they raise community eval scores
- [ ] **13.2** Signed releases + verified update channel
- [ ] **13.3** Trace → dataset pipeline (sanitized, provider terms respected)
- [ ] **13.4** LoRA fine-tune a small open model (e.g. via Unsloth) → "TIDOS-7B" that natively follows the protocol
- [ ] **13.5** Benchmark TIDOS-7B vs base model vs strong models on the dungeons
- [ ] **13.6** Release v6.0.0

---

## Open Questions

- [x] **Q1** Which models/tools are used day to day? → **Mostly Claude (Claude Code); sometimes Gemini and OpenCode models.** Collector order: 2.3/2.4 Claude Code → 2.5 Gemini CLI → 2.6 OpenCode — answered 2026-10-24
- [x] **Q2** Owner Firebase UID → `YTU4IuDy3SaGKOPt9E34iSge8Mo1` — answered 2026-10-24 *(permission to deploy Firestore rules still to confirm at task 3.2)*
- [x] **Q3** Dashboard stack → user delegated ("go with the best way you see"): **Python stdlib server + plain HTML/JS + SSE**, no FastAPI/React — answered 2026-10-24
- [ ] **Q4** Purge personal data from git history (1.20)? Requires force-push to GitHub

---

## Decisions Log

| Date | Decision | Reason |
| :--- | :--- | :--- |
| 2026-10-24 | Enforce via code/hooks/tools, not prose | Weak models ignore long instructions; enforcement is reliable |
| 2026-10-24 | All learned data lives in `~/.tidos/brain.db`, outside the repo | Updater cannot wipe it; private data never reaches GitHub |
| 2026-10-24 | `/TIDOSZIT` password stored as a **hash** in Firestore, typed only in the browser, plus Google owner-UID check | Plaintext in Firestore is readable/leakable; password must never pass through the AI chat |
| 2026-10-24 | Learn **methodology** (playbooks, grounding, verification, constraints) from strong models — not raw weights | Transferable and measurable; escalation covers hard reasoning |
| 2026-10-24 | Every learned artifact is eval-gated before promotion | Prevents self-learning drift/rot |
| 2026-10-24 | Auto-develop opens PRs; a human merges | Avoids supply-chain / prompt-injection via `main` |
| 2026-10-24 | Update gate never runs `git clean`, and skips (never forces) when system files have local edits or unpushed commits | Untracked files are always user work; protects the maintainer's in-progress changes |
| 2026-10-24 | Trace collectors built in order Claude Code → Gemini CLI → OpenCode | User mostly uses Claude, sometimes Gemini / OpenCode (Q1) |
| 2026-10-24 | Control center = Python stdlib + plain JS + SSE (not FastAPI/React) | Zero installs, no build, offline, matches TIDOS stdlib-only scripts (Q3 delegated) |
| 2026-10-24 | Control password is set/changed only in the browser; no CLI | Anything typed in a terminal can be captured in AI transcripts |
| 2026-10-24 | Kill switches live in `~/.tidos/control.json` and are enforced by scripts/hooks | Real control, not prose; survives TIDOS updates |
| 2026-10-24 | TIDOS learns from EVERY project the user works on; strong-model work counts most; TIDOS's own test runs (dungeons) are never learned from | User: "make tidos learn when users work on their project, especially with powerful models" |
| 2026-10-24 | REALIGNMENT: the goal is developing TIDOS — learn from strong-model sessions, guide weak models with the user; no model training or model benchmarking | User correction |
| 2026-10-24 | (superseded) Driver orchestrates sandboxed agents (Claude Code, OpenCode), not raw completions | OpenCode free tier only works inside its agent; agents already read/edit/run, the driver adds the loop, checks and escalation |
| 2026-10-24 | The strong model writes the checks ("defines done"), the weak model does the work | Spec -> tests is cheap for a strong model and the hardest part for a weak one |
| 2026-10-24 | Agent cannot edit `~/.claude/settings.json` or deploy to Firebase (Claude Code safety) — owner runs those two commands | Self-modification and production deploys need a human |
