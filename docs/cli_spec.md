# TIDOS CLI Specification (Future)

This document describes the architectural specification for a future TIDOS command-line interface. **This is a design document only — no CLI is implemented.**

## Overview

The TIDOS CLI provides a unified interface for managing the TIDOS Operating System across projects. It handles initialization, configuration, diagnostics, and workflow automation.

## Command Reference

### `tidos init`

Initialize TIDOS in the current project.

**Behavior:**
1. Detect project type and technology stack
2. Ask for connection mode (submodule / multi-root / local)
3. Create `.tidos/` directory structure
4. Generate initial memory files from detected stack
5. Output initialization summary

**Flags:**
- `--mode submodule|local|prompt` - Force connection mode
- `--yes` - Skip confirmation prompts
- `--plugin <name>` - Pre-select plugins

---

### `tidos start`

Execute the TIDOS startup sequence and generate a Startup Report.

**Behavior:**
1. Read `TIDSTART.md` protocol
2. Load core, identity, and bootstrap
3. Mount engines, rules, personas, and plugins
4. Analyze target project directory
5. Recover project context and memory
6. Generate and display Startup Report
7. Wait for user instructions

**Flags:**
- `--report` - Save report to file
- `--quick` - Skip detailed analysis, load cached state
- `--force` - Rebuild all cached context

---

### `tidos doctor`

Run a system health check on the TIDOS installation.

**Behavior:**
1. Verify `.tidos/` directory structure integrity
2. Check for missing required files
3. Validate protected directory invariant
4. Check VERSION.md against latest remote tag
5. Report any issues with resolution recommendations

**Exit Codes:**
- `0` - All checks passed
- `1` - Warnings found
- `2` - Errors found

---

### `tidos review`

Generate a code review report against TIDOS quality gates.

**Behavior:**
1. Read current project state
2. Apply TIDOS rules and architecture standards
3. Run quality engine checks (all 8 dimensions)
4. Generate structured review report
5. Output violations, warnings, and recommendations

**Flags:**
- `--gate <1-8>` - Run specific quality gate only
- `--format json|markdown` - Output format
- `--output <file>` - Save report to file

---

### `tidos plan`

Generate an execution plan for a task or feature.

**Behavior:**
1. Accept task description or PRD reference
2. Load relevant plugins for the detected stack
3. Apply architecture rules and templates
4. Generate structured plan with:
   - Task breakdown
   - File manifests
   - Test requirements
   - Quality gates to pass
5. Output execution plan

**Flags:**
- `--template <name>` - Use specific template
- `--adr` - Generate ADR alongside plan

---

### `tidos learn`

Record a lesson or pattern in the memory system.

**Behavior:**
1. Prompt for lesson details (what, why, context)
2. Categorize as lesson, pattern, or best practice
3. Update appropriate memory file
4. Validate against existing patterns (avoid duplicates)
5. Confirm write to `memory/`

**Flags:**
- `--type lesson|pattern|practice` - Categorize entry
- `--project <name>` - Associate with project

---

### `tidos research`

Run a 4-factor research analysis on a technology or approach.

**Behavior:**
1. Accept research topic or question
2. Execute research engine protocol:
   - Benefit analysis
   - Risk assessment
   - Compatibility check
   - Value proposition
3. Generate structured research report
4. Include recommendations

**Flags:**
- `--deep` - Extended analysis with benchmarks
- `--output <file>` - Save research report

---

### `tidos upgrade`

Upgrade TIDOS to the latest version.

**Behavior:**
1. Check current version from `VERSION.md`
2. Fetch latest version from remote repository
3. Display changelog between versions
4. Check for breaking changes
5. Prompt for confirmation
6. Execute upgrade based on connection mode
7. Verify post-upgrade integrity

**Flags:**
- `--version <semver>` - Target specific version
- `--yes` - Skip confirmation
- `--dry-run` - Show what would change without applying

## Architecture

The CLI would be implemented as a standalone executable with the following modules:

```
tidos/
  cli/           -> Command routing and argument parsing
  commands/      -> Command implementations
  core/          -> Core OS loading and validation
  detectors/     -> Project and stack detection
  generators/    -> Report and plan generation
  sync/          -> Memory and context synchronization
```

## Non-Goals

- No package manager functionality
- No build system integration
- No direct modification of protected system files
