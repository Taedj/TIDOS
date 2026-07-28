# Changelog

All notable changes to **TIDOS (Tidjani Development Operating System)** are documented in this file.

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
