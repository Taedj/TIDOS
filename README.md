# TIDOS (Tidjani Development Operating System) v3.0
## Centralized AI Development Operating System Platform

**TIDOS** is a standalone, centralized AI Development Operating System hosted in a dedicated Git repository. Instead of copying framework files into every target project, AI coding agents load TIDOS directly from the official central repository or consume it via portable connection protocols.

---

## 1. Top-Level Repository Structure

```text
TIDOS/
├── README.md                  # Central platform overview & quick start
├── LICENSE                    # MIT License
├── CODE_OF_CONDUCT.md         # Community standards
├── CHANGELOG.md               # Version release log
├── VERSION.md                 # Active version tag (3.0.0)
├── ROADMAP.md                 # Platform roadmap & maturity model
├── CONTRIBUTING.md            # Contribution guidelines & OS Freeze rules
├── TIDSTART.md                # Central session entry & boot protocol
│
├── config/                    # Centralized configuration (repository URL, version)
├── docs/                      # Installation, Tool Integration Guides & CLI Spec
├── core/                      # Protected OS Core, Identity & Bootstrap
├── engines/                   # Specialized Operating Engines (Workflow, Quality, Memory, etc.)
├── personas/                  # Virtual AI Engineering Company (30+ roles)
├── rules/                     # Architecture, Security & Coding Standards
├── commands/                  # Session command definitions & protocols
├── checklists/                # Quality Gate & DoD verification checklists
├── templates/                 # 13 Reusable Markdown Document Templates
├── plugins/                   # 18 Technology Specialization Plugins & Plugin Engine
├── prompts/                   # System prompt scaffolds
├── memory/                    # Evolving User Profile, Preferences, Patterns & Learnings
├── evolution/                 # OS Suggestions, Approved Upgrades & Version History
├── examples/                  # 9 Integration Blueprints (Flutter, React, Supabase, AI, etc.)
├── scripts/                   # Framework helper scripts (install.sh, install.ps1)
├── examples/                  # 10 Integration Blueprints (Flutter, React, Supabase, AI, Starter, etc.)
└── .github/                   # CI/CD Workflows
```

---

## 2. Multi-Agent Connection Modes

Because different AI coding agents have different capabilities, TIDOS v3.0 supports four flexible consumption modes. The canonical repository URL is defined in `config/framework.md` — update that single file if the repository moves.

```
+-----------------------------------------------------------------------+
| Mode 1: Git Submodule / Central Reference                             |
|         git submodule add $(REPO_URL) .tidos                          |
+-----------------------------------------------------------------------+
| Mode 2: Multi-Root Workspace / Symlink                                |
|         Add TIDOS repo folder alongside project in IDE workspace       |
+-----------------------------------------------------------------------+
| Mode 3: System Prompt / System Instructions                           |
|         Inject TIDSTART.md & Kernel URL in AI agent settings          |
+-----------------------------------------------------------------------+
| Mode 4: Standalone Local Copy (Fallback)                              |
|         Copy TIDOS root folder directly into target project           |
+-----------------------------------------------------------------------+
```

Detailed tool-specific integration guides for **OpenCode**, **Antigravity IDE**, **Claude Code**, **Cursor**, **Windsurf**, **Roo Code**, **Cline**, **Gemini CLI**, and **OpenAI Codex** are located in [docs/](file:///d:/work/Dev/TIDOS/docs).

---

## 3. Protected Operating System & Evolution Isolation

- **Protected System Core**: Directories `core/`, `engines/`, `personas/`, `rules/`, `commands/`, `checklists/`, `templates/`, `plugins/`, and `prompts/` are **read-only system files**.
- **Evolution Layer**: Non-invasive framework enhancement ideas are written to `evolution/SUGGESTIONS.md` and applied only upon explicit user upgrade commands.
- **User Memory**: Personal developer preferences and validated engineering patterns accumulate in `memory/`.

---

## 4. Quick Start for AI Agents

1. Load or reference the official TIDOS repository.
2. Execute the central startup sequence in [TIDSTART.md](file:///d:/work/Dev/TIDOS/TIDSTART.md).
3. Synchronize core rules, architecture standards, and user profile before responding to user prompts.
