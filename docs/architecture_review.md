# TIDOS v3.0 Enterprise Architecture Report

## 1. Executive Summary

TIDOS v3.0 is a centralized, version-controlled AI Development Operating System hosted in a dedicated Git repository. It has evolved from local `.tidos/` folders into a standalone Git repository with config-driven multi-project support, installation scripts, project templates, and a documented release strategy. The architecture follows a protected core + evolution layer pattern, ensuring system stability while enabling continuous improvement.

## 2. Architectural Qualities

### Scalability
- **Repository Scale**: Single Git repository with modular directory structure supports unlimited files
- **Multi-Project**: Any number of projects can reference the single TIDOS repository via submodule, clone, or install scripts
- **Multi-Agent**: All 9 major AI coding agents are supported via documented integration guides
- **Plugin Growth**: 18 existing plugins; new plugins added without modifying core
- **Config-Driven**: `config/framework.md` centralizes repository metadata for single-point updates

### Maintainability
- **Protected Core**: 9 system directories (`core/`, `engines/`, `personas/`, `rules/`, `commands/`, `checklists/`, `templates/`, `plugins/`, `prompts/`) are read-only
- **Evolution Layer**: Suggestions isolated in `evolution/SUGGESTIONS.md` for controlled changes
- **Memory Isolation**: User intelligence in `memory/` evolves independently of system files
- **Clear Ownership**: Every directory has a README explaining purpose and contents
- **Installation Scripts**: One-command setup for Linux/macOS and Windows

### Modularity
- **Core**: Execution engine, identity, and bootstrap (3 files)
- **Engines**: 6 specialized engines (workflow, quality, memory, learning, research, plugin)
- **Rules**: Architecture, security, and coding standards
- **Plugins**: 18 technology-specific plugins
- **Personas**: 30+ virtual AI roles
- **Templates**: 13 document templates
- **Prompts**: Agent-specific system prompt scaffolds
- **Config**: Centralized configuration for repository metadata

### Backward Compatibility
- **v1.x → v2.0**: Breaking change (local → centralized), migration guide provided
- **v2.0 → v3.0**: Non-breaking (kernel → core rename, config added, new scripts/templates)
- **v3.0 → future**: Protected core ensures forward compatibility; evolution layer prevents breaking changes without explicit version bumps
- **Versioning**: Semantic Versioning maintained in `VERSION.md`

## 3. Cross-Reference Verification

| Directory | Referenced By | References |
|-----------|--------------|------------|
| `config/` | `README.md`, `TIDSTART.md`, `docs/tools/*` | — |
| `core/` | `TIDSTART.md`, `docs/architecture_review.md` | Rules, Engines, `config/framework.md` |
| `engines/` | `TIDSTART.md`, `core/kernel.md` | Rules, Plugins |
| `personas/` | `TIDSTART.md` | Rules |
| `rules/` | `TIDSTART.md`, `engines/quality_engine.md` | — |
| `commands/` | `TIDSTART.md` | — |
| `checklists/` | `engines/quality_engine.md` | — |
| `templates/` | `engines/workflow_engine.md` | — |
| `plugins/` | `TIDSTART.md`, `engines/plugin_engine.md` | — |
| `prompts/` | `TIDSTART.md` | — |
| `memory/` | `TIDSTART.md`, `engines/memory_engine.md` | — |
| `evolution/` | `CONTRIBUTING.md`, `core/kernel.md` | `config/framework.md` |
| `examples/` | `docs/installation.md` | Plugins |
| `docs/` | `README.md` | All directories |
| `scripts/` | `README.md` | `config/framework.md` |

## 4. Naming Consistency

- All directory names are lowercase, plural nouns
- All specification files use `snake_case.md`
- Plugin files follow `<technology>.md` convention
- Template files follow `<purpose>.md` convention
- Memory files use `UPPER_CASE.md` for active documents
- Config file uses `framework.md` for framework-level settings
- Script files use language-standard extensions (`.sh`, `.ps1`)

## 5. Security Analysis

- **Protected Directories**: AI agents cannot modify system files (`core/`, `engines/`, `personas/`, `rules/`, `commands/`, `checklists/`, `templates/`, `plugins/`, `prompts/`)
- **Memory Privacy**: Explicit policy against storing sensitive personal information in `memory/`
- **No Secrets**: No API keys, tokens, or credentials in repository
- **MIT License**: Permissive open-source licensing with clear attribution
- **Code of Conduct**: Contributor Covenant for community safety

## 6. Recommended Improvements

1. **Implement CI Pipeline**: Add `.github/workflows/` with repository integrity checks
2. **MCP Server**: Add MCP protocol support for tool-based OS context hydration
3. **Automated Sync Bot**: GitHub Action for cross-repository memory consolidation
4. **Plugin Marketplace**: Define plugin registry format for community contributions
5. **Unit Tests**: Add validation tests for directory structure and cross-references
6. **Prompt Content**: Populate `prompts/` with agent-specific system prompt templates
7. **Version Templates**: Create release workflow templates in `.github/`
