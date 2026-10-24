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
| 1 | v4.1 — Fix & Clean | Stop data loss, security holes, inconsistencies | 🔄 In progress (8/29) |
| 2 | Brain & Traces | Record every task outside the repo (`~/.tidos/brain.db`) | ⬜ Not started |
| 3 | `/TIDOSZIT` Control Center (core) | Secure dashboard: Google + Firestore password gate | ⬜ Not started |
| 4 | v4.5 — Measure (Evals / Dungeons) | Ground-truth scoring of models and TIDOS | ⬜ Not started |
| 5 | Learn from Strong Models (Distillation) | Turn strong-model traces into playbooks | ⬜ Not started |
| 6 | Weak-Model Driver | TIDOS drives weak models to strong-model results | ⬜ Not started |
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
- [ ] **0.7** User answers open questions (see [Open Questions](#open-questions)) — Q1, Q2 answered 2026-10-24; Q3, Q4 pending

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
- [ ] **1.10** Update gate: pin to **signed release tags** instead of `main`; show a diff and require user approval before applying
- [ ] **1.11** `scripts/factory_sync.ps1` / `.sh` — stop auto-pushing to `main`; open a PR instead
- [ ] **1.12** `scripts/google_auth_server.py` — add `state` nonce to `/callback`, verify the ID token server-side, reject unexpected origins
- [ ] **1.13** Store the refresh token securely (OS keyring via `keyring`, or at least restricted file permissions)
- [ ] **1.14** `scripts/auth_verify.ps1` / `.sh` — remove `-Password` CLI argument (shell history leak); prompt securely instead
- [ ] **1.15** Make the Google auth gate **opt-in** (required only for features that need identity: community sync, `/TIDOSZIT`)
- [ ] **1.16** `browser_relay/` (GPTID) — mark as experimental/off by default; document ToS risk; prepare API-based replacement (see 6.x)
- [ ] **1.17** `personas/tidostrade.md` — add risk disclaimer and "paper-trading only / never execute real trades" constraint

### 1C. Privacy
- [ ] **1.18** Remove personal project data from the public repo (`memory/LESSONS.md`, `memory/PROJECT_HISTORY.md`, `memory/USER_PROFILE.md`, etc.); ship only empty templates
- [ ] **1.19** Move user memory to `~/.tidos/memory/` (outside repo); add `memory/*` user files to `.gitignore`
- [ ] **1.20** Purge personal data from git history (optional, `git filter-repo`) — needs user approval

### 1D. Consistency & cleanup
- [ ] **1.21** Unify version numbers everywhere (README, TIDSTART, VERSION, engines, start banners) — single source in `config/framework.md`
- [ ] **1.22** Remove or archive the duplicated legacy `.tidos/` tree; reconcile `plugins/` vs `.tidos/plugins/` (keep `figma.md`, `github.md`)
- [ ] **1.23** Fix `README.md` (duplicate `examples/` line, false CI/CD claim)
- [ ] **1.24** Fix `docs/tools/claude-code.md` (wrong URL `tidjani/TIDOS`; no `systemPrompt` setting — use `CLAUDE.md` / skills / hooks / plugin)
- [ ] **1.25** Audit and fix all other `docs/tools/*.md` guides against each tool's real configuration
- [ ] **1.26** Mark the "80/80 weak model benchmark" in `docs/THE_BIG_IDEA.md` as unverified until Phase 4 produces real numbers

### 1E. CI
- [ ] **1.27** Add `.github/workflows/ci.yml`: pytest, ruff, markdown-lint, link check, gitleaks secret scan, PowerShell lint (PSScriptAnalyzer), shellcheck
- [ ] **1.28** Add persona/skill schema validator (required sections, routing signals) to CI
- [ ] **1.29** Release v4.1.0 (changelog, tag)

---

## Phase 2 — Brain & Traces (foundation for learning + dashboard)

- [ ] **2.1** Design `~/.tidos/brain.db` SQLite schema: `sessions`, `tasks`, `steps`, `tool_calls`, `verifications`, `corrections`, `playbooks`, `facts`, `models`, `evals`, `xp_events`, `security_log`
- [ ] **2.2** Implement `tidos_brain` Python package (stdlib `sqlite3`, migrations, typed API)
- [ ] **2.3** Trace collector — **Claude Code**: `PostToolUse` / `Stop` / `UserPromptSubmit` hooks writing to brain.db
- [ ] **2.4** Trace collector — Claude Code transcript importer (`~/.claude/projects/*.jsonl`)
- [ ] **2.5** Trace collector — Gemini CLI session logs
- [ ] **2.6** Trace collector — OpenAI Codex / OpenCode session logs
- [ ] **2.7** Trace collector — API router (LiteLLM proxy) for Grok / OpenRouter / Ollama requests
- [ ] **2.8** Outcome scoring: verify-pass, user-accepted, retries, reverts, user corrections → `task.score`
- [ ] **2.9** Privacy: sanitizer runs on every trace before storage; secrets never stored
- [ ] **2.10** Retention & size limits (rotate/compact old traces)
- [ ] **2.11** Tests for brain package and collectors

---

## Phase 3 — `/TIDOSZIT` Control Center (core)

### 3A. Security gate
- [ ] **3.1** Firestore document `admin/tidoszit` = `{ hash, salt, algo, iterations, updatedAt }` (never the plaintext password)
- [ ] **3.2** Firestore security rules: `admin/*` readable/writable **only** by the owner UID; deploy to `tidos-framework`
- [ ] **3.3** `scripts/tidoszit_setpass.py` — set/change password locally (PBKDF2-SHA256 or argon2), writes only the hash
- [ ] **3.4** Login step 1: Google sign-in, must match owner UID
- [ ] **3.5** Login step 2: password typed **in the browser** (never through the AI chat/terminal) and verified against the Firestore hash
- [ ] **3.6** Session cookie (HttpOnly, SameSite=Strict, 30-min expiry), bound to `127.0.0.1` only
- [ ] **3.7** Brute-force protection: 5 failures → 15-min lockout; every attempt logged in `security_log`
- [ ] **3.8** Security tests (wrong UID, wrong password, lockout, expired session, CSRF)

### 3B. Command & app
- [ ] **3.9** `/TIDOSZIT` slash command for Claude Code (`.claude/commands` or skill) + `scripts/tidoszit.ps1` / `.sh` for other tools
- [ ] **3.10** Backend: FastAPI + SQLite (reads brain.db), WebSocket live stream
- [ ] **3.11** Frontend: React + Tailwind, dark "System Window" theme (Solo Leveling style), built and served locally
- [ ] **3.12** Panel: 🜲 **Status Window** (level, XP bar, rank, today's quests, recent level-ups)
- [ ] **3.13** Panel: 📡 **Live Monitor** (running sessions, current step, active model, gates, live log; pause/kill)
- [ ] **3.14** Panel: 🛡 **Security** + kill switches (auto-update, persona factory, auto-sync, GPTID)
- [ ] **3.15** End-to-end test: `/TIDOSZIT` → login → see live trace from a real Claude Code session

---

## Phase 4 — v4.5: Measure (Evals = "Dungeons")

- [ ] **4.1** Eval task format (task prompt, repo fixture, verify command, expected outcome)
- [ ] **4.2** Write 30–50 golden tasks across user stacks: Python, Flutter/Android, Firebase/Firestore, Tkinter desktop, PowerShell, TP DRIVER/teaching builders
- [ ] **4.3** Eval runner (sandboxed worktree/Docker, runs any model through the router, records results in brain.db)
- [ ] **4.4** Baseline: strong models (Claude, Gemini, Grok, GPT) **without** TIDOS
- [ ] **4.5** Baseline: weak/local models (Ollama 7B/8B) **without** TIDOS
- [ ] **4.6** Baseline: same models **with** current TIDOS v4.1 — real answer to the "Big Idea" claim
- [ ] **4.7** "Turn a fixed bug into a golden task" helper (every real bug grows the dungeon)
- [ ] **4.8** Panel: 🏰 **Dungeons** (suites, pass/fail history, regressions, "Run" button)

---

## Phase 5 — Learn from Strong Models (Distillation)

- [ ] **5.1** Task classifier (task type × stack: bug-fix/flutter, feature/python, refactor, migration, TP-builder…)
- [ ] **5.2** Filter: only successful, high-score strong-model traces are learning material
- [ ] **5.3** Distiller: strong model summarizes N similar traces into a **Playbook** (steps, grounding pattern, verification habit, negative constraints, worked example)
- [ ] **5.4** Playbook format (`playbooks/<type>/<stack>.md` + metadata in brain.db: source models, uses, success rate, rank)
- [ ] **5.5** Negative-constraint extractor (from strong-model mistakes and user corrections)
- [ ] **5.6** Worked-example selector (best 1–2 traces per playbook as few-shot)
- [ ] **5.7** **Eval gate**: a playbook is promoted only if it raises the weak-model score on golden tasks
- [ ] **5.8** Per-model methodology profile (how Claude vs Gemini vs Grok plan/verify; which is best per domain)
- [ ] **5.9** Panel: 📜 **Playbook Library** (rank E→S, approve/edit/demote/delete, "test against eval")
- [ ] **5.10** Check each provider's terms before any fine-tuning use of outputs (playbooks/prompts for own use are fine)

---

## Phase 6 — Weak-Model Driver

- [ ] **6.1** Model router via LiteLLM (cloud: Claude, Gemini, Grok, OpenRouter; local: Ollama / llama.cpp)
- [ ] **6.2** Model profiles `models/{small,medium,frontier}.yaml` (context budget, micro-step size, output format, verify depth)
- [ ] **6.3** Driver loop: classify → fetch playbook → decompose into micro-steps → strict JSON/diff output per step
- [ ] **6.4** Grounding: TIDOS reads files itself; repo map (tree-sitter), ast-grep, LSP (Serena MCP) — weak model gets only relevant slices
- [ ] **6.5** Mechanical verify after every step (tests/lint/compile) + repair loop with exact error + playbook fix pattern (max N tries)
- [ ] **6.6** **Teacher-on-call** escalation: strong model fixes only the stuck step; the fix becomes a new trace
- [ ] **6.7** Cost-aware routing: cheap model first, escalate on gate failure; budget limits
- [ ] **6.8** Measure: weak + TIDOS driver vs weak alone vs strong (Phase 4 suites)
- [ ] **6.9** Panel: ⚔ **Model Arena** (leaderboard model × domain, teacher-vs-student chart, routing rules editor)
- [ ] **6.10** Panel: 💰 **Cost & Tokens**

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
- [ ] **Q3** Approve dashboard stack: FastAPI + SQLite + React/Tailwind (default)
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
