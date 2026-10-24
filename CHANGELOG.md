# Changelog

All notable changes to **TIDOS (Tidjani Development Operating System)** are documented in this file.

---

## [5.0.0] - 2026-10-24

TIDOS becomes a runtime: it learns automatically from strong-model work and **enforces** guidance for weak models
(hooks, MCP tools) instead of only describing it.

### Added
- **MCP server** (`tidos_mcp/`): `tidos_start`, `tidos_guide`, `tidos_verify` (only real check subcommands),
  `tidos_recall`, `tidos_note`, `tidos_propose` — for Claude Code, OpenCode, Cursor and any MCP client.
- **Claude Code plugin** (`plugin/`, marketplace in `.claude-plugin/`): 7 subagents (architect, reviewer, tester,
  security, researcher, uiux, mobile), `/tidos` orchestrator, `/TIDOSZIT`, hooks for all events, MCP server.
- **GUIDE mode, per request**: `tidos_session guide` / hook injection returns only the matching playbook, a
  checks-first step and the project's notes (≤ 1.6 KB).
- **Enforcement in GUIDE mode** (Claude Code hooks): read before edit, no "done" without a passing check, stop after
  the same check fails 3 times.
- **Automatic learning**: background strong-model session summaries (`auto_summarize`), learned standing rules from
  recurring user directives, playbook decay, usage tracking, disable switch, Playbook Library tab.
- **OpenCode collector**: free-model sessions are traced too; `tidos_session effect` compares guided vs unguided work.
- **Second opinion** from a different model (`tidos_session review`), replacing the GPTID browser relay.
- **AGENTS.md generator** (`tidos_session agents-md`).

### Fixed
- Checker failures without the word "failed" (flutter "N issues found", jest `FAIL`, `npm ERR!`, tsc, TAP) were
  counted as passes — found by the TIDOS reviewer subagent.
- Task classification: spec wording ("pre-release", "compared", "plan") no longer misroutes requests; opening verbs
  and questions are understood.
- Sessions started in a parent folder are credited to the sub-repository they worked in.

---

## [4.1.0] - 2026-10-24

TIDOS now **learns** from strong-model sessions and **guides** weak/free models, and the v4.0 safety problems are fixed.

### Added
- **START TIDOS modes** (`tidos_session/`): detects tool + model (Claude Code transcript, OpenCode state), tier via
  `config/models.json` (+ `~/.tidos/models.json`); LEARN mode on frontier models, GUIDE mode (≤ 4 KB brief with weak-model
  rules, project facts, check commands, learned playbooks) on medium/weak models.
- **Brain** (`tidos_brain/`): private trace store `~/.tidos/brain.db`, Claude Code importer + hooks, privacy redaction,
  kill switches enforced by scripts (`~/.tidos/control.json`).
- **Learning** (`tidos_learn/`): per-project and general playbooks distilled from successful strong-model tasks
  (where code lives, checks that confirm work, pitfalls incl. user corrections); `note` command for strong models.
- **/TIDOSZIT control center** (`tidos_dashboard/`): owner-only (Google + control password hash in Firestore),
  Status window, Live monitor, Dungeons, Security/kill switches.
- **Dungeons** (`evals/`, `tidos_evals/`): 30 verified tasks (fail untouched, pass with solution) to check TIDOS guidance.
- **CI** (`.github/workflows/ci.yml`), spec validator, `.gitleaks.toml`, `.gitattributes`.

### Changed
- **Update gate**: follows release tags by default, reports updates and installs only with approval (`-ApplyUpdate`),
  optional signed-tag requirement, never downgrades.
- **Persona factory sync** opens pull requests instead of pushing to `main`.
- **Google sign-in gate** is opt-in (`auth_gate` switch); login callback is nonce-protected and verified server-side;
  session file restricted to the OS user; no password arguments.
- **User memory** moved to `~/.tidos/memory/`; the repository keeps templates only.
- README, TIDSTART and tool guides rewritten for the real behavior; one version source (`VERSION.md`).

### Fixed
- Sanitizer crashed on every input (bad regex escape), missed real key formats, flagged prose, ignored the directory whitelist.
- Update gate could reset a user's project or a fork, and deleted generated personas (`git clean`).
- `factory_sync.ps1` never parsed on Windows; bash `factory_sync` never ran the firewall nor detected personas;
  bash scripts called `python3`, absent from Git Bash on Windows.

### Security
- Removed `memory/ULTIDOS_persona.md` (jailbreak-style prompt with a plain-text password) from the repository.
  It remains in git history until the history is rewritten (plan task 1.20).
- GPTID browser relay marked experimental and off by default (ToS risk).

---

## [4.0.0] - 2026-10-11

### Added
- **The Big Idea Cognitive Architecture**: Complete architecture decoupling cognitive excellence from raw model weights, enabling smaller/local 7B-8B models to match frontier performance (Claude 3.7 / Gemini 2.5 Pro).
- **Model Equalizer System-2 Layer**: Mandatory 6-stage railway (`Ingest -> Ground -> Plan -> Atomic Edit -> Verify -> Sign-off`) preventing premature completion, context bleed, and hallucinations.
- **Autonomous Internet-Grounded Persona Synthesizer**: Upgraded Persona Factory (`engines/persona_factory_engine.md` v2.0) with real-time web research, negative constraints, and domain checklists.
- **`TIDOSMOBILE` Persona**: First autonomously synthesized specialist persona targeting modern mobile development (Flutter 3.x, Android 15/API 35, Gradle 8.5+, Java 21).
- **Privacy Firewall (`scripts/sanitizer.py`)**: Zero-Leakage audit engine detecting and redacting secrets, API keys, credentials, local paths, and user PII.
- **Federated Community Swarm Sync**: Automated upstream sync pipelines (`scripts/community_sync.ps1`, `scripts/community_sync.sh`) allowing distributed TIDOS clones to contribute sanitized patterns back to `Taedj/TIDOS`.
- **Colored Terminal Chat & Consultation Stream (`browser_relay/terminal_ui.py`)**: Rich live console UI featuring Neon Cyan for TIDOS and Emerald Green for ChatGPT with Virtual Terminal Processing support.
- **Headless Background Relay**: Browser relay defaults to headless execution without popping visible browser windows during routine CLI tasks.

---

## [3.2.0] - 2026-09-11

### Added
- **Channel validation**: Clean copyable blocks and structured message flow.
- **Untrusted boundary**: External responses are data-only and strictly validated before application.
- **Bloat control**: Bounded limits for turns, context size, and summaries.

---

## [3.1.0] - 2026-09-11

### Added
- **Partner Consultation Mode**: Named external consultant flow with copyable blocks and single-box responses.

---

## [3.0.0] - 2026-07-28

### Added
- **Renamed `kernel/` to `core/`**: Aligned directory name with semantic purpose.
- **`config/` directory**: Centralized configuration with `framework.md` as single source of truth for repository URL.
- **`CODE_OF_CONDUCT.md`**: Contributor Covenant code of conduct.
- **Installation Scripts**: `scripts/install.sh` (Linux/macOS) and `scripts/install.ps1` (Windows) for one-command TIDOS setup.
- **Starter Template**: `examples/starter-template.md` for rapid project initialization.
- **Release Strategy Documentation**: SemVer workflow with GitHub Releases guidance.

### Changed
- All `kernel/` references updated to `core/` across the entire codebase.
- All version references updated to v3.0.0 in documentation, headers, and metadata.
- Documentation updated to reference `config/framework.md` instead of hardcoded URLs.
- Protected system directories invariant updated to include `core/`.

---

## [2.0.0] - 2026-07-28

### Added
- **Centralized GitHub Repository Architecture**: Refactored TIDOS from local project copies into a standalone, centralized Git platform repository.
- **Top-Level Modular Folder Hierarchy**:
  - `core/`: Core runtime execution spec, identity baseline, and bootstrap discovery protocol.
  - `engines/`: Specialized operating engines (`workflow_engine`, `quality_engine`, `memory_engine`, `learning_engine`, `research_engine`, `plugin_engine`).
  - `personas/`: Virtual AI Engineering Company (30+ domain specialist roles).
  - `rules/`: Clean architecture, security, and clean coding standards.
  - `commands/`: Session commands and invocation protocols.
  - `checklists/`: Quality Gate checklists and Definition of Done verification schemas.
  - `templates/`: 13 reusable document templates (`prd.md`, `architecture.md`, `roadmap.md`, etc.).
  - `plugins/`: 18 technology specialization plugins (`flutter.md`, `firebase.md`, `supabase.md`, etc.).
  - `prompts/`: Standardized system prompt scaffolds.
  - `memory/`: Evolving user profile, project history, preferences, patterns, learnings, and best practices.
  - `evolution/`: OS improvement suggestions, approved upgrades, and version history.
  - `examples/`: 9 complete sample integration blueprints (Flutter, Firebase, Firestore, Supabase, React, Next.js, Node.js, Desktop, AI).
  - `docs/`: Comprehensive installation guides, upgrade protocols, AI tool integration guides, and future CLI specification.
- **Multi-Agent Consumption Protocols**: Explicit integration guides for 9 major AI IDEs and CLI platforms (OpenCode, Antigravity IDE, Claude Code, Cursor, Windsurf, Roo Code, Cline, Gemini CLI, OpenAI Codex) supporting Git submodules, multi-root workspace linking, system prompt injection, and local copy fallbacks.
- **Future CLI Specification (`docs/cli_spec.md`)**: Full architectural specification for `tidos init`, `tidos start`, `tidos doctor`, `tidos review`, `tidos plan`, `tidos learn`, `tidos research`, and `tidos upgrade`.

---

## [1.1.0] - 2026-07-28
- Introduced Enterprise Evolution System, OS Freeze Invariant, and `.tidos/evolution/` dynamic layer.

---

## [1.0.0] - 2026-07-28
- Initial release: Core 10 specifications, 13 templates, 18 technology plugins.
