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
| 1 | v4.1 — Fix & Clean | Stop data loss, security holes, inconsistencies | 🟢 Done except user items (1.4 local gitleaks, 1.20 history purge, 1.27 first CI run on push) |
| 2 | Brain & Traces | Record every task outside the repo (`~/.tidos/brain.db`) | 🟢 Done except user/deferred items (2.3 install, 2.5 Gemini, 2.7 router) |
| 3 | `/TIDOSZIT` Control Center (core) | Secure dashboard: Google + Firestore password gate | 🟢 Built (13/15) - 3.2 deploy + 3.15 first login need the user |
| 4 | v4.5 — Measure (Evals / Dungeons) | Ground-truth scoring of models and TIDOS | 🟢 Built (5/8) - baselines superseded by 6.8 |
| 5 | LEARN mode | TIDOS learns from strong-model sessions (START TIDOS) | ✅ Done (9/9) |
| 6 | GUIDE mode | TIDOS detects weak models and guides them with the user | 🟢 Built (8/9) - 6.8 raid gave no result (agent hang, fixed); rerun pending |
| 7 | v5.0 — Runtime (MCP, Hooks, Plugin, Subagents) | Make TIDOS a real agent kernel | ✅ Done (10/10) |
| 8 | Skills Library | Feed TIDOS reusable `SKILL.md` skills | ✅ Done (20/20) |
| 9 | v5.5 — Solo Leveling (Auto-Learn) | XP, ranks, eval-gated promotion | 🟢 Done (11/14) - 9.7, 9.9 partial, 9.11 deferred |
| 10 | Auto-Develop | Self-PR bot, mutation testing, scheduled quests | 🟢 Done (5/6) - 10.1 partial (no eval delta per proposal yet) |
| 11 | Tool Scout | Auto-discover, vet, propose tools | 🟢 Done (6/8) - 11.4 and 11.7 partial |
| 12 | Control Center (full) | All dashboard panels | ✅ Done (6/6) |
| 13 | v6.0 — Swarm & TIDOS-native Model | Federated community + fine-tuned model | 🟡 Partial (1/6 + 5 partial/deferred) - v5.1.0 released instead of v6.0 |

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
- [ ] **1.4** *(partial: new patterns + false-positive fixes tested; gitleaks layer runs in CI (secrets job) - still not installed on this machine)* Sanitizer detection: integrate **gitleaks** (or trufflehog) as primary scanner; keep regex as fallback; add patterns for `sk-ant-`, `AKIA…`, JWT `eyJ…`, Slack `xox?-`; remove false positives on prose ("Bearer tokens", "password: never hardcode")
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
- [x] **1.21** Unify version numbers everywhere (README, TIDSTART, VERSION, engines, start banners) — single source in `config/framework.md` — done 2026-10-24 (VERSION.md is the single source (config/framework.md mirrors it, checked in CI); README, TIDSTART, ROADMAP, CONTRIBUTING and start banners carry no version; banners read VERSION.md)
- [x] **1.22** Remove or archive the duplicated legacy `.tidos/` tree; reconcile `plugins/` vs `.tidos/plugins/` (keep `figma.md`, `github.md`) — done 2026-10-24 (legacy .tidos/ tree removed from git; its 3 unique plugins (figma, github, playwright) moved to plugins/)
- [x] **1.23** Fix `README.md` (duplicate `examples/` line, false CI/CD claim) — done 2026-10-24 (README rewritten: learn/guide model, quick start, components, control center, safety/privacy, dev commands; local file:///d:/... links replaced by repo-relative links in 10 docs)
- [x] **1.24** Fix `docs/tools/claude-code.md` (wrong URL `tidjani/TIDOS`; no `systemPrompt` setting — use `CLAUDE.md` / skills / hooks / plugin) — done 2026-10-24 (docs/tools/claude-code.md: real URL (Taedj/TIDOS), CLAUDE.md snippet instead of a non-existent systemPrompt setting, hooks install + /TIDOSZIT command)
- [x] **1.25** Audit and fix all other `docs/tools/*.md` guides against each tool's real configuration — done 2026-10-24 (9 tool guides regenerated with one bootstrap snippet in each tool's real instruction file (CLAUDE.md, AGENTS.md, GEMINI.md, .cursor/rules, .windsurf/rules, .clinerules, .roo/rules); Antigravity's location marked unverified instead of guessed)
- [x] **1.26** Mark the "80/80 weak model benchmark" in `docs/THE_BIG_IDEA.md` as unverified until Phase 4 produces real numbers — done 2026-10-24 (THE_BIG_IDEA.md 5.1 unchecked and corrected: the 80/80 was self-verification on a strong model; real eval results cited)

### 1E. CI
- [x] **1.30** *(found and fixed 2026-10-24)* `scripts/factory_sync.ps1` never parsed on Windows since v4.0 (unclosed `if` block + UTF-8 `✓` read as a smart quote by PowerShell 5.1) — fixed; all `.ps1` files now parse and are ASCII-only. CI should run a PowerShell parse check (see 1.27)
- [ ] **1.27** *(written 2026-10-24: .github/workflows/ci.yml = tests on Linux + Windows, spec validator, update-gate scenarios (sh + ps1), dungeon validation (node/dart/PowerShell), .ps1 parse + ASCII check, PSScriptAnalyzer and shellcheck (errors only), gitleaks on the working tree with .gitleaks.toml allowlist. Every step that can run locally passes; the workflow itself runs for the first time when the branch is pushed)* Add `.github/workflows/ci.yml`: pytest, ruff, markdown-lint, link check, gitleaks secret scan, PowerShell lint (PSScriptAnalyzer), shellcheck
- [x] **1.28** Add persona/skill schema validator (required sections, routing signals) to CI — done 2026-10-24 (scripts/validate_specs.py: persona title + registration, factory schema for generated personas, registry links, VERSION vs config, models.json, dungeon task.json, repo-relative Markdown links; 0 errors; in CI and tests/test_specs.py)
- [x] **1.29** Release v4.1.0 (changelog, tag) — done 2026-10-24 (VERSION.md + config/framework.md 4.1.0 (status Beta), CHANGELOG + ROADMAP entries, annotated tag v4.1.0 created locally (unsigned, not pushed))

---

## Phase 2 — Brain & Traces (foundation for learning + dashboard)

- [x] **2.1** Design `~/.tidos/brain.db` SQLite schema: `sessions`, `tasks`, `steps`, `tool_calls`, `verifications`, `corrections`, `playbooks`, `facts`, `models`, `evals`, `xp_events`, `security_log` — done 2026-10-24 (`tidos_brain/db.py`, schema v1 via `PRAGMA user_version`; corrections stored as `tasks.corrected`, steps as `tool_calls`; also `live_events` for the Live Monitor; WAL mode for hooks + dashboard)
- [x] **2.2** Implement `tidos_brain` Python package (stdlib `sqlite3`, migrations, typed API) — done 2026-10-24 (CLI: `hook`, `import-claude`, `stats`, `prune`, `install-hooks`)
- [ ] **2.3** *(built and tested; install needs the user (Claude Code blocks agents from editing their own settings): python -I tidos_brain/__main__.py install-hooks. START TIDOS already imports transcripts incrementally, so learning works without it; hooks only add the live monitor)* Trace collector — **Claude Code**: `PostToolUse` / `Stop` / `UserPromptSubmit` hooks writing to brain.db
- [x] **2.4** Trace collector — Claude Code transcript importer (`~/.claude/projects/*.jsonl`) — done 2026-10-24 (real history: 11 sessions → 248 tasks in 3.3 s; skips sidechains/injected messages; dedupes split messages; counts cached tokens)
- [ ] **2.5** *(deferred: Gemini CLI is not installed here and there is no session data to build and test a parser against; user mostly uses Claude Code + OpenCode)* Trace collector — Gemini CLI session logs
- [x] **2.6** Trace collector — OpenAI Codex / OpenCode session logs — done 2026-10-24 (tidos_brain/opencode.py reads OpenCode's SQLite (session/message/part only, never account/credential tables, read-only), same task scoring as Claude Code; real data: 64 sessions / 1,086 tasks (muse-spark-free, big-pickle...); incremental (unchanged sessions skipped, 0 s); wired into START TIDOS, tidos_learn and the `import-opencode` CLI command; tests/test_opencode.py)
- [ ] **2.7** *(deferred: no API keys on this machine; agents are driven through their own CLIs (Claude Code, OpenCode) instead)* Trace collector — API router (LiteLLM proxy) for Grok / OpenRouter / Ollama requests
- [x] **2.8** Outcome scoring: verify-pass, user-accepted, retries, reverts, user corrections → `task.score` — done 2026-10-24 (v1 heuristics in `tidos_brain/scoring.py`: tests/lint/build detection, pass/fail parsing, EN+FR correction detection, tool errors; first run on real history: 56 success / 25 failure / 167 unknown)
- [x] **2.9** Privacy: sanitizer runs on every trace before storage; secrets never stored — done 2026-10-24 (scan of the real import: **0 leaks**; sanitizer extended to redact this machine's user name in every spelling — spaces, dashes, Claude's `C--Users-…` encoding, 8.3 short name; home-folder sessions stored as project `~`)
- [x] **2.10** Retention & size limits (rotate/compact old traces) — done 2026-10-24 (`prune --live-days 14 --session-days N` + VACUUM; tested)
- [x] **2.11** Tests for brain package and collectors — done 2026-10-24 (`tests/test_brain.py`; full suite 116 passed, 23 subtests)

---

## Phase 3 — `/TIDOSZIT` Control Center (core)

### 3A. Security gate
- [x] **3.1** Firestore document `admin/tidoszit` = `{ hash, salt, algo, iterations, updatedAt }` (never the plaintext password) — done 2026-10-24 (format implemented + tested; the document itself is created by the first-run setup in the browser)
- [ ] **3.2** *(rules written; deploy needs the user (Claude Code blocks agent production deploys): firebase deploy --only firestore:rules --project tidos-framework --config firebase/firebase.json)* Firestore security rules: `admin/*` readable/writable **only** by the owner UID; deploy to `tidos-framework`
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
- [ ] **3.15** *(needs the user: hooks installed (2.3), rules deployed (3.2), one real Google login)* End-to-end test: `/TIDOSZIT` → login → see live trace from a real Claude Code session

---

## Phase 4 — v4.5: Measure (Evals = "Dungeons")

- [x] **4.1** Eval task format (task prompt, repo fixture, verify command, expected outcome) — done 2026-10-24 (`evals/dungeons/<suite>/<name>/` = `task.json` + `fixture/` + `hidden/` (tests copied in only AFTER the agent finishes, so they cannot be read or gamed) + `solution/`)
- [x] **4.2** Write 30–50 golden tasks across user stacks — done 2026-10-24 (30 tasks E..S: python 17, teaching 4, javascript 3, sql 2, powershell 2, dart 2; all validated fail-untouched / pass-with-solution)
- [x] **4.3** Eval runner (sandboxed worktree/Docker, runs any model through the router, records results in brain.db) — done 2026-10-24 (`tidos_evals/`: isolated workdirs in `~/.tidos/eval-runs/`, agents `claude:<model>` (restricted tools, budget cap) and `opencode:<provider/model>` (per-run sandbox config, `--dir` + pinned PWD), results in `brain.evals` (schema v2) + per-run logs; `validate` proves every task fails untouched and passes with its reference solution (17/17 valid))
- [ ] **4.4** *(superseded by the 2026-10-24 realignment (goal = develop TIDOS, not benchmark models): Claude Haiku 32/32 recorded; strong-model baselines not needed)* Baseline: strong models (Claude, Gemini, Grok, GPT) **without** TIDOS
- [ ] **4.5** *(superseded: free GLM ran at ceiling; weak-model measurement moves to 6.8 (free model with vs without the TIDOS GUIDE brief))* Baseline: weak/local models (Ollama 7B/8B) **without** TIDOS
- [ ] **4.6** *(superseded by 6.8: v4 prose protocol gave no gain on Haiku (31/32 vs 32/32, +55% cost) - the reason GUIDE mode is short and task-specific)* Baseline: same models **with** current TIDOS v4.1 — real answer to the "Big Idea" claim
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
- [x] **5.6** Distillation runs at session end in LEARN mode (the strong model summarizes its own session — cheap, high quality), plus `tidos learn` to process older sessions — done 2026-10-24 (tidos_learn/summarize.py: at START TIDOS (no hooks needed) up to 2 unsummarized strong-model sessions are digested (prompts, files, checks, corrections; no file contents) and sent in the background to claude -p --model haiku (budget cap 0.05 USD); its 1-3 advice lines become project notes; switch auto_summarize; real run on a ZTAP Opus session produced 3 concrete notes; also tidos_learn summarize --session/--pending)
- [x] **5.7** User & project knowledge: preferences, recurring corrections, project facts (stack, test command, deploy steps) learned per project — done 2026-10-24 (tidos_learn/prefs.py: directive sentences (EN+FR) that RECUR (>=2, similar wording) and are specific (>=3 content words, so review-only rules like 'Do NOT modify code' never become general rules) -> ~/.tidos/memory/LEARNED_PREFERENCES.md per project + all projects; GUIDE brief shows up to 4 as standing rules (near-duplicates merged); real data: SMARTRAD trading-safety rules learned)
- [x] **5.8** Playbook quality: confidence from outcomes (verified success, no correction), merge duplicates, decay unused ones — done 2026-10-24 (confidence decays with the age of the newest evidence (none for 30 days, at most halved), newest_evidence in front matter; GUIDE briefs record which playbooks they served (~/.tidos/playbook_state.json); disabled playbooks are never served and stay disabled across regeneration; merge = idempotent regeneration)
- [x] **5.9** Panel: 📜 Playbook Library in /TIDOSZIT (view, edit, approve, delete) — done 2026-10-24 (Playbooks tab in /TIDOSZIT: every playbook + notes with project, type, E-S rank, confidence, evidence, times served, on/off switch, viewer; path-traversal-safe API + tests; verified with Playwright on real data (desktop + mobile, 0 errors))

---

## Phase 6 — GUIDE mode: TIDOS guides weak/free models with the user

- [x] **6.1** Compact guided brief (< 4 KB, not the 86 KB v4 boot): user profile, project facts, weak-model protocol, top playbooks for this project — done 2026-10-24 (GUIDE brief hard-capped at 4 KB: rules, project facts (stack, check commands, deploy/git notes), matching playbooks from `~/.tidos/playbooks`)
- [x] **6.2** Weak-model protocol (from what the evals showed): one small step at a time, relative paths only, read before edit, run the project's checks after every change, never claim "done" without check output, ask the user when unsure — done 2026-10-24 (7 rules in `tidos_session/brief.py` (small steps, read before edit, relative paths, checks first, verify after every change, never "done" without output, ask on risky actions, stop after 3 identical errors and suggest a strong model))
- [x] **6.3** Just-in-time guidance: on each user prompt, TIDOS picks the matching playbook and injects only that (Claude Code `UserPromptSubmit` hook; OpenCode/Gemini via MCP tool `tidos_guide(task)`) — done 2026-10-24 (tidos_session guide REQUEST: classifies the request (opening verb first, then keywords; raw questions vs bugs) and returns, within 1.6 KB of whole lines, only this project's playbook for that task type (else the general one), its pitfalls and the strong-model notes; Claude Code: UserPromptSubmit hook injects it automatically in GUIDE mode; other tools: the GUIDE brief tells the model to run it for every new request)
- [x] **6.4** Checks-first for risky tasks: TIDOS asks the model to write/locate the checks before editing (driver lesson: "define done" first) — done 2026-10-24 (checks-first step per task type (bugfix: reproduce with a failing check; feature: write expected behavior as checks; deploy: explicit OK for the exact command; refactor: checks before and after; review/question: do not modify code))
- [x] **6.5** Stuck detection: repeated failures / same error loop → TIDOS tells the user and suggests switching to a strong model for this step (or, with consent, asks a strong model for a hint) — done 2026-10-24 (Claude Code PostToolUse hook in GUIDE mode: the 3rd identical failing check in a row -> exit 2 + stderr telling the model to stop, explain and suggest a stronger model; Bash checks judged by output; brief rule 7 for other tools)
- [x] **6.6** Delivery per tool: Claude Code (hooks + CLAUDE.md block), OpenCode (AGENTS.md + instructions + plugin), Gemini CLI (GEMINI.md), others via AGENTS.md — done 2026-10-24 (the brief is delivered through START TIDOS output in every tool; tidos_session snippet --tool X prints the paste-ready instructions for each tool's own file (CLAUDE.md, AGENTS.md, GEMINI.md, .cursor/.windsurf/.roo rules, .clinerules); docs/tools/ guides)
- [x] **6.7** Every guided session is traced too, so TIDOS learns which guidance helped weak models — done 2026-10-24 (OpenCode + Claude Code sessions are traced (2.6); every START TIDOS is logged (~/.tidos/guide_log.jsonl); tidos_session effect compares weak-model tasks after a GUIDE start vs without (check pass rate, corrections, tool errors). Baseline before any guidance: big-pickle 62%, muse-spark 85% checks passed)
- [ ] **6.8** *(partial: the A-S raid (big-pickle plain vs GUIDE) produced no result - OpenCode hung and the timeout could not kill npm-shim grandchildren; fixed (process-tree kill + test). Rerun: python -I tidos_evals/__main__.py run --agent opencode:opencode/big-pickle --tidos compare --min-difficulty A)* Measure TIDOS guidance with dungeons: free model inside its own agent WITH the TIDOS guide vs WITHOUT (quality check of TIDOS, not a model benchmark)
- [x] **6.9** Panel: mode, model tier and guidance used per session in the Live Monitor — done 2026-10-24 (Live Monitor: TIDOS Session card (mode, model, tier, tool, project, start) + 'Does GUIDE mode help?' table (guided vs unguided tasks and check pass rate per weak/medium model) from /api/session; Playwright check desktop + mobile, 0 errors)

> Built 2026-10-24 before this realignment and kept as tools: `tidos_driver/` (external orchestrator — its lessons feed 6.2/6.4/6.5),
> `tidos_evals/` dungeons (used by 6.8). Earlier model baselines: Claude Haiku 32/32 without vs 31/32 with the v4 prose protocol
> (+55% cost) → the long v4 boot text does not help; GUIDE mode must be short and task-specific.

---

## Phase 7 — v5.0: Runtime (MCP, Hooks, Plugin, Subagents)

- [x] **7.1** `tidos-mcp` server with tools: `get_context`, `route_persona`, `plan_gate`, `verify`, `record_outcome`, `recall`, `propose_skill`, `scout_tools` — done 2026-10-24 (tidos_mcp/: stdlib MCP server (stdio JSON-RPC, protocol 2024-11-05..2025-06-18) with tidos_start, tidos_guide, tidos_verify (real exit codes; only check subcommands allowed: never python -c / node -e / shell), tidos_recall, tidos_note, tidos_propose; verified end-to-end with real Claude Code (Haiku called tidos_guide via --mcp-config, 0.004 USD) and OpenCode (server connected); tests/test_mcp.py)
- [x] **7.2** `get_context(task)` — retrieval with ~8 KB budget (only relevant rules/personas/skills/playbooks/memory) instead of loading ~86 KB at boot — done 2026-10-24 (context is served per need instead of the 86 KB boot: tidos_start returns the brief (GUIDE <= 4 KB), tidos_guide returns <= 1.6 KB for one request, tidos_recall searches what was learned)
- [x] **7.3** Enforcement hooks (Claude Code): `PreToolUse` blocks `Edit/Write` until a plan/grounding record exists — done 2026-10-24 (GUIDE mode (Claude Code PreToolUse hook on Edit|Write|MultiEdit|NotebookEdit): an edit is blocked (exit 2 + reason) until the model has read or searched something since the user's request; LEARN mode never gated; tests)
- [x] **7.4** Enforcement hooks: `Stop` blocks "done" unless `verify` passed — done 2026-10-24 (GUIDE mode Stop hook: if code changed and no check passed after the last edit, finishing is blocked with: run the checks or say clearly it is UNVERIFIED; stop_hook_active guard prevents loops; failing checks do not count; tests)
- [x] **7.5** Convert personas to real subagents: `tidos-architect`, `tidos-reviewer` (read-only), `tidos-tester`, `tidos-security`, `tidos-researcher`, `tidos-uiux`, `tidos-mobile` — done 2026-10-24 (.claude/agents/: tidos-architect (plan, read-only), tidos-reviewer (diff review, read-only), tidos-tester (failing check first, may edit tests only), tidos-security, tidos-researcher (web), tidos-uiux, tidos-mobile; verified: real Claude Code ran tidos-reviewer (2 turns, 0.014 USD) and its findings led to a real fix (flutter 'N issues found' and other checker failures were not recognized))
- [x] **7.6** Orchestrator `/tidos <task>`: plan → implement → review → verify → record — done 2026-10-24 (.claude/commands/tidos.md: /tidos <request> = guide (define done) -> architect plan -> implement -> tester verify -> reviewer -> learn note -> report incl. anything UNVERIFIED)
- [x] **7.7** Second-opinion reviewer subagent using a different model via API (replaces GPTID browser automation) — done 2026-10-24 (tidos_session review --with claude:<model>|opencode:<provider/model>: sanitized git diff to a different model via its official CLI, reviewer has no edit/shell/web access; warns when the reviewer is the same model family as the session; replaces GPTID; real run with Haiku produced 4 valid findings, 3 fixed (0 issues found, case-insensitive FAIL, unanchored exit code))
- [x] **7.8** Package as a **Claude Code plugin** (skills + subagents + hooks + MCP) — done 2026-10-24 (plugin/ = Claude Code plugin (7 subagents, /tidos + /TIDOSZIT, hooks for all 6 events, MCP server) with a launcher that finds the TIDOS checkout (TIDOS_REPO or ~/.tidos/repo_path written by START TIDOS) because installed plugins live in a cache; .claude-plugin/marketplace.json for /plugin marketplace add Taedj/TIDOS; built by scripts/build_plugin.py (CI checks sync); claude plugin validate: plugin + marketplace pass with no warnings; launcher hook + MCP verified)
- [x] **7.9** `AGENTS.md` generator for Codex / Cursor / OpenCode / others — done 2026-10-24 (tidos_session agents-md [--write]: inserts or replaces a marked TIDOS block in the project's AGENTS.md (other content kept, idempotent): START TIDOS, MCP workflow, detected check commands; never contains private playbooks, rules or notes; tests)
- [x] **7.10** Release v5.0.0 — done 2026-10-24 (VERSION + config 5.0.0 (beta), CHANGELOG + ROADMAP, plugin rebuilt and validated, annotated tag v5.0.0 created locally (not pushed))

---

## Phase 8 — Skills Library (`SKILL.md`)

### Engineering
- [x] **8.1** `tdd-loop` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.2** `bug-rca` (reproduce → bisect → fix → regression test) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.3** `refactor-safely` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.4** `dependency-upgrade` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.5** `perf-profile` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.6** `api-design` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.7** `db-migration` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.8** `release` (semver + changelog + tag) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))

### User stacks
- [x] **8.9** `flutter-android` (Gradle/AGP traps) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.10** `firebase-rules-audit` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.11** `supabase-rls` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.12** `tkinter-desktop` (from TP DRIVER lessons) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.13** `pyinstaller-exe` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.14** `windows-powershell-pitfalls` (cp1252, quoting, `python -c`) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))

### Teaching
- [x] **8.15** `tp-builder` (TP DRIVER moteur rules, auto-verification) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.16** `exam-generator` with auto-verification — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))

### Meta
- [x] **8.17** `skill-author` (writes new skills) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.18** `eval-author` (bug → golden task) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.19** `memory-compactor` — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))
- [x] **8.20** `tool-scout` (see Phase 11) — done 2026-10-24 (.claude/skills/<name>/SKILL.md, shipped in the plugin; validated by claude plugin validate + scripts/validate_specs.py; public generic know-how only (project specifics stay in private playbooks))

---

## Phase 9 — v5.5: Solo Leveling (Auto-Learn)

- [x] **9.1** XP engine: +XP first-try verify pass / accepted without edits; −XP reverts, corrections, failed gates — done 2026-10-24 (tidos_learn/xp.py: XP from evidence per task (success +20, unknown +5, failure -10, check passed +5, first check passed +5, corrected -10) written to brain.xp_events at every distill; dashboard and terminal use the same engine)
- [x] **9.2** Global TIDOS level + per-domain levels — done 2026-10-24 (global level + per-domain (project, sub-repo attributed) levels and ranks; real data: TIDOS LV 26 B, SMARTRAD LV 19 C, ZTAP LV 10 C)
- [x] **9.3** Ranks E→S for every skill, playbook, persona (success rate over N uses) — done 2026-10-24 (playbooks ranked E-S from confidence + evidence; subagents ranked by missions in the Shadow Army; personas are not usage-tracked (they are specs for strong models))
- [x] **9.4** Rank-based loading priority (high-rank first, low-rank demoted/archived) — done 2026-10-24 (briefs and per-request guidance pick playbooks by project match + confidence (rank) and skip disabled ones; low-rank playbooks lose to stronger ones and decay with age)
- [x] **9.5** Reflexion lessons: after failure, write "when X, do Y" with trigger condition — done 2026-10-24 (failures become pitfalls (checks that failed before passing, user corrections with the correcting message, informative failed attempts) and strong-model summaries add 'trap avoided' notes)
- [x] **9.6** Voyager-style distillation: pattern succeeds 3+ times → auto-draft `SKILL.md` — done 2026-10-24 (playbooks with >= 10 verified successes and rank B+ are drafted as SKILL.md in ~/.tidos/drafts/skills (13 drafted from real data); activated only when the user moves them)
- [ ] **9.7** *(partial: promotion of drafts is a human review step; the eval gate exists as a tool (tidos_evals --tidos guide/compare) but is not yet automatic)* **Eval-gated promotion**: new skill/lesson kept only if eval score improves
- [x] **9.8** Memory decay: unused / unhelpful facts lose confidence and leave context — done 2026-10-24 (playbook confidence decays with evidence age (none for 30 days, at most halved); unused playbooks visible via served counts)
- [ ] **9.9** *(partial: learned rules are clustered/deduplicated (prefs.py), near-duplicate rules merged in briefs, memory-compactor skill; no automatic rewrite of memory files)* Memory dedup + conflict resolution
- [x] **9.10** "Job change": domain passes threshold → propose a specialist subagent — done 2026-10-24 (job change: a domain reaching level 15 gets a draft specialist subagent built from its playbooks + the user's standing rules (SMARTRAD drafted at LV 19))
- [ ] **9.11** *(deferred: needs repeated eval runs per prompt variant (cost/time); the dungeon harness (--repeat, compare) is the base for it)* DSPy / GEPA-style prompt optimization of personas & skills against evals
- [x] **9.12** `TIDOS STATUS` command (terminal version of Status Window) — done 2026-10-24 (tidos_learn status: terminal status window (level, rank, XP bar, 5 stats, domains, daily quests, unlocked drafts))
- [x] **9.13** Panel: 🧠 **Memory Explorer** (edit/merge/delete/pin, graph view) — done 2026-10-24 (Memory tab in /TIDOSZIT: private memory files, learned rules and drafts, read-only viewer, traversal-safe API (tests))
- [x] **9.14** Panel: "Shadow Army" view (subagents as units with level & specialties) — done 2026-10-24 (Shadow Army on the Status window: active subagents + drafted specialists with missions and E-S rank; the importer now records which subagent each delegation went to)

---

## Phase 10 — Auto-Develop

- [ ] **10.1** *(partial: evolution queue (~/.tidos/proposals.jsonl, priorities, statuses) + local GitHub issue drafts with the exact gh command (publishing stays the user's decision); eval delta per proposal not yet attached)* `evolution/SUGGESTIONS.md` → GitHub Issues (label, score, eval delta)
- [x] **10.2** Self-PR bot (scheduled agent): implements top suggestion on a branch, runs CI + evals, opens PR with before/after score — **human merges, never pushes to main** — done 2026-10-24 (scripts/self_improve.py: implements one ACCEPTED proposal in a temporary git worktree on branch auto/<id>-<slug>, gates = tests + spec validator + plugin sync, commits only if all pass, never pushes/merges; verified for real (haiku, 0.02 USD, branch auto/1-... with code + 2 tests))
- [x] **10.3** Mutation testing of the OS: remove a rule → eval drop? If not, propose deletion (keeps TIDOS lean) — done 2026-10-24 (tidos_evals run --ablate N: GUIDE mode with weak rule N removed, compared with full GUIDE on the same tasks (>= 10); no drop -> deletion proposal filed in the evolution queue (tests; verified with the reference agent; real-model ablations are the user's cost decision))
- [x] **10.4** Daily quest: scheduled eval run + regression report (`/schedule` or GitHub Actions) — done 2026-10-24 (scripts/daily_quest.py: tests, specs, plugin sync, dungeon validation, learning refresh, status -> ~/.tidos/reports/<date>.md, exit 1 on regression (first real run: all clear); schedule with schtasks/cron (docstring))
- [x] **10.5** Notifications (daily quests, playbooks ready for promotion, regressions) — done 2026-10-24 ([SYSTEM] notifications on the Status window: new proposals, implemented branches to review, daily quest regressions, unlocked drafts, missing report (tests))
- [x] **10.6** Panel: 🧬 **Evolution Queue** (approve → PR, reject) — done 2026-10-24 (Evolution tab unlocked: queue with Accept/Reject (logged in the security log), daily quest result, unlocked draft counts)

---

## Phase 11 — Tool Scout

- [x] **11.1** Need sensing (missing capability from task/stack, e.g. "no secret scanner", "no linter") — done 2026-10-24 (tidos_scout needs: missing capabilities from the project's stack + files (e.g. ZTAP lacks a secret scanner, dependency scanner, python linter/type checker); installed tools, MCP servers (names only) and blacklisted tools excluded)
- [x] **11.2** Search: GitHub API, MCP registries, awesome-lists — done 2026-10-24 (tidos_scout search: GitHub repository search (only the query words leave the machine) ranked by trust; curated starter catalog in config/tools.json (16 tools incl. MCP servers))
- [x] **11.3** Trust score: stars, recent commits, license, maintainers, OSV / OpenSSF Scorecard — done 2026-10-24 (trust 0-100: stars, last push, license (permissive/copyleft), archived = 0, OpenSSF Scorecard; capped at 85 without Scorecard; cached 7 days; offline keeps the cached value; system-curl fallback when Python's CA bundle fails (verification never disabled))
- [ ] **11.4** *(partial: vet runs an INSTALLED tool's catalog version command in an empty temp dir and flags stray writes; no container/network isolation (Docker not used) and nothing is downloaded to vet)* Sandbox vetting (Docker/worktree): install, smoke test, permission check
- [x] **11.5** Propose install + config to user — **never auto-install without approval** — done 2026-10-24 (propose/approve print the exact install command for the user; TIDOS never runs install (CLI + dashboard))
- [x] **11.6** Learn: tool XP (helped or not), blacklist bad tools — done 2026-10-24 (tool XP from real sessions (runs/passes of each tool's commands in the brain, e.g. pytest 11/13); blacklist removes a tool from needs and briefs)
- [ ] **11.7** *(partial: starter toolset catalogued with install commands and detection; installed tools with a check (gitleaks, ruff, osv-scanner, shellcheck) are added to GUIDE briefs as extra checks; nothing installed on this machine (user decision))* Integrate starter toolset: gitleaks, semgrep, ruff, mypy/pyright, pytest, ast-grep, tree-sitter, ripgrep, Playwright MCP, GitHub MCP, Context7, Serena, promptfoo/inspect-ai, LiteLLM, Ollama
- [x] **11.8** Panel: 🛰 **Tool Scout** (trust score, install, sandbox-test, blacklist) — done 2026-10-24 (Tool Scout tab unlocked: installed, trust (with reasons on hover), usage, status; Trust/Vet/Approve/Ban actions, logged in the security log (tests))

---

## Phase 12 — Control Center (full)

- [x] **12.1** "Ask TIDOS" bar (natural-language questions over traces: "why did Flutter tasks fail this week?") — done 2026-10-24 (Ask TIDOS bar: question -> digest of the last 30 days (per project/type/stack/tier outcomes, recent failures, matching items) -> haiku with ALL tools and MCP disabled, budget 0.05 USD; switch ask_llm (off = local facts); the question is never logged. Real answer verified on the user's data)
- [x] **12.2** Global search across traces, playbooks, memory, evals — done 2026-10-24 (global search (all words) across tasks, playbooks, memory + drafts, evals, proposals; results jump to the right tab)
- [x] **12.3** Settings editor for `config/framework.md` values (with validation) — done 2026-10-24 (settings editor (Security tab) for 10 whitelisted config/framework.md values with type/range/choice validation; rewrites one line in place keeping comments/line endings; relay_host and other risky values stay manual)
- [x] **12.4** Export / backup / restore of brain.db — done 2026-10-24 (tidos_brain backup / backup --list / restore NAME --yes (integrity + schema check, current brain saved as pre-restore first, never overwrites a backup, newest 10 kept by mtime); dashboard: Back up now + list; restore terminal-only)
- [x] **12.5** Mobile-friendly layout — done 2026-10-24 (every tab checked at 390 px: no horizontal scroll (Playwright E2E + visual QA); ask bar wraps on phones)
- [x] **12.6** Dashboard E2E tests (Playwright) — done 2026-10-24 (tests/test_dashboard_e2e.py (Playwright/Chromium, opt-in TIDOS_E2E=1, run by the daily quest): login wall, all tabs without console errors, search -> memory, Ask, settings write, backup, mobile overflow - 4/4 pass)

---

## Phase 13 — v6.0: Swarm & TIDOS-native Model

- [ ] **13.1** *(partial: contribution gate in CI (scripts/check_contribution.py: privacy firewall, no private TIDOS drafts or learned data, frontmatter, size; tests); 'only if eval scores rise' is a manual dungeon run before/after (CI has no model budget/secrets))* Community skills/playbooks submitted as PRs, accepted only if they raise community eval scores
- [ ] **13.2** *(partial: the update gate already enforces signed tags with TIDOS_REQUIRE_SIGNED=1; signing needs the owner's GPG/SSH key (none configured here), so v5.1.0 is tagged unsigned)* Signed releases + verified update channel
- [x] **13.3** Trace → dataset pipeline (sanitized, provider terms respected) — done 2026-10-24 (tidos_learn dataset: verified strong-model work -> JSONL (request, task type, stacks, steps, checks, outcome) + data card; no model-written text; privacy firewall + path stripping (audit on real data: 124 records, 0 paths/usernames); tests)
- [ ] **13.4** *(deferred: needs a GPU, hours of training and a provider-terms review before training on session-derived data; the dataset (13.3) is ready for it)* LoRA fine-tune a small open model (e.g. via Unsloth) → "TIDOS-7B" that natively follows the protocol
- [ ] **13.5** *(deferred: depends on 13.4; the dungeon harness (compare/ablate/repeat) is ready to benchmark it)* Benchmark TIDOS-7B vs base model vs strong models on the dungeons
- [ ] **13.6** *(not released as v6.0 (no TIDOS-native model yet); phases 9-12 shipped as v5.1.0 'Level Up' (local tag))* Release v6.0.0

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
