# TIDOS v2.0 Release Notes

## Version

**2.0.0** — Centralized GitHub Operating System

**Release Date**: 2026-07-28

## What's New

### Centralized Architecture
- Refactored from local `.tidos/` copies to a standalone Git repository
- Single source of truth for all projects
- Semantic Versioning for tracking changes
- Multiple consumption modes: submodule, multi-root, system prompt injection, local copy

### New Directory Structure
- `core/` - Core execution, identity, and bootstrap
- `engines/` - 6 specialized operating engines
- `personas/` - 30+ virtual AI engineering roles
- `rules/` - Architecture, security, and coding standards
- `commands/` - Session command protocols
- `checklists/` - Quality Gate verification
- `templates/` - 13 reusable document templates
- `plugins/` - 18 technology specialization plugins
- `prompts/` - System prompt scaffolds
- `memory/` - Evolving user intelligence layer
- `evolution/` - Non-invasive improvement proposals
- `docs/` - Comprehensive documentation
- `examples/` - 9 integration blueprints

### Multi-Agent Support
Official integration guides for:
- OpenCode
- Antigravity IDE
- Claude Code
- Cursor
- Windsurf
- Roo Code
- Cline
- Gemini CLI
- OpenAI Codex

### Documentation
- Installation guide (4 modes)
- Upgrade guide
- Migration guide (v1.x → v2.0)
- CLI specification
- Enterprise architecture report
- Repository tree
- Dependency diagram
- Per-tool integration guides

## Breaking Changes

- **v1.x `kernel.md` references**: Update all agent instructions to use new `.tidos/TIDSTART.md` protocol
- **Memory location**: Moved from `.tidos/evolution/` to `.tidos/memory/`
- **Protected directories**: Explicit invariant enforced for 9 system directories

## Upgrade Path

See `docs/migration_guide.md` for detailed migration instructions.

## Future Roadmap

- **v2.1.0**: MCP Server implementation, GitHub Actions sync bot
- **v2.2.0**: CLI implementation, plugin marketplace
- **v3.0.0**: Multi-repository orchestration, distributed memory

## Contributors

- Tidjani & TIDOS Framework Contributors
