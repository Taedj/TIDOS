# Changelog

All notable changes to **TIDOS (Tidjani Development Operating System)** are documented in this file.

---

## [3.2.0] - 2026-09-11

### Added
- **Channel validation**: `SENT TO <NAME>:` + `[TIDOS:` and `RECEIVED FROM <NAME>:` + single `<NAME>:` box enforced; missing name/direction → `MALFORMED` before claims (`engines/chora_session_engine.md` Sec 8).
- **Untrusted boundary**: RECEIVED is data-only; authority/governance override + embedded execute attempts → `REJECTED`; never executed.
- **Bloat control**: bounded ledger `templates/chora_session.md` §4; limits `max_turn_chars: 8000`, `max_receipt_chars: 12000`, `max_turns_per_round: 12`, overflow `truncate-and-summarize`.
- **Validator coverage**: `verify_chora_session.ps1` 34→44 (8 deterministic v3.2 tests: valid SENT/RECEIVED, missing name, malformed direction, oversize, embedded instruction, authority override, zero-secret).

### Verified
- `verify_chora_session.ps1` 44/44 PASS, `verify_chora_trigger.ps1` 21/21 PASS. Decision via CHORA `chora-20260911-002` (CHATGPT).

---

## [3.1.0] - 2026-09-11

### Added
- **TIDOSCHORA Chat-Channel Mode (default)**: bare `TIDOSCHORA` asks partner count → names (e.g. `CHATGPT`) + perspective → opens copyable `SENT TO <NAME>:` / `RECEIVED FROM <NAME>:` channels. Turn-0 contract enforces single-md-box replies (`<NAME>:`), minimal pointers, zero secrets.
- **`config/framework.md` `chora.session.channel`**: `enabled/default_mode/reply_format/context` flags.
- **Validator coverage**: `verify_chora_session.ps1` now asserts channel markers (`SENT TO`, `RECEIVED FROM`, `Partner name`, `Channel`) alongside legacy markers.

### Changed
- `engines/chora_trigger_engine.md` Sec 7, `engines/chora_session_engine.md` Sec 4-5, `docs/chora_session.md`, `commands/session_commands.md`, `prompts/chora/advisor_base.md`, `prompts/chora/perspectives.md`, `templates/chora_session.md`, `templates/chora_response.md` migrated to channel default.
- Legacy `templates/chora_response.md` envelope retained as deprecated compat path (verified claims-only synthesis, authority hierarchy, `max_rounds: 2` unchanged).

### Verified
- `verify_chora_session.ps1` + `verify_chora_trigger.ps1` green. Decision via CHORA `chora-20260911-001` (4 claims VERIFIED: C4/C6/C7/C8).

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
