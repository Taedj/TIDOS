# TIDOS v1.x to v2.0 Migration Guide

## Overview

TIDOS v2.0 introduces a centralized architecture. Projects using the old `.tidos/` local folder structure must migrate to reference the central TIDOS repository.

## Breaking Changes

| Area | v1.x (Local) | v2.0 (Central) |
|------|-------------|----------------|
| Location | `.tidos/` inside each project | Standalone Git repository |
| Versioning | None or manual | Semantic Versioning in `VERSION.md` |
| Updates | Manual copy | `git pull` or `git submodule update` |
| Memory | `.tidos/evolution/` | `memory/` and `evolution/` |
| Plugins | `.tidos/plugins/` | `plugins/` in central repo |
| Templates | `.tidos/templates/` | `templates/` in central repo |

## Migration Steps

### Step 1: Backup Existing Projects

```bash
# For each project using TIDOS v1.x
cp -r .tidos .tidos.backup
```

### Step 2: Choose Connection Mode

- **Recommended**: Git submodule (enables version tracking and updates)
- **Alternative**: Multi-root workspace (for IDE environments)
- **Fallback**: Local copy (for offline or air-gapped environments)

### Step 3: Submodule Installation

```bash
# Remove old local .tidos
rm -rf .tidos

# Add central TIDOS as submodule
git submodule add https://github.com/tidjani/TIDOS.git .tidos
git submodule init
git submodule update
```

### Step 4: Migrate Memory

Copy your personalized memory and evolution data:

```bash
# Create memory directory if needed
mkdir -p .tidos/memory .tidos/evolution

# Copy existing user data
cp .tidos.backup/evolution/USER_PREFERENCES.md .tidos/memory/PREFERENCES.md 2>/dev/null || true
cp .tidos.backup/evolution/PROJECT_PROFILE.md .tidos/memory/USER_PROFILE.md 2>/dev/null || true
cp .tidos.backup/evolution/PROJECT_HISTORY.md .tidos/memory/PROJECT_HISTORY.md 2>/dev/null || true
cp .tidos.backup/evolution/BEST_PRACTICES.md .tidos/memory/BEST_PRACTICES.md 2>/dev/null || true
cp .tidos.backup/evolution/SUGGESTIONS.md .tidos/evolution/SUGGESTIONS.md 2>/dev/null || true
```

### Step 5: Update .gitignore

Ensure `.tidos/` is NOT in `.gitignore` (since submodules are tracked):

```bash
# Remove .tidos from .gitignore if present
git add .tidos
git commit -m "migrate: TIDOS v1.x → v2.0 centralized architecture"
```

### Step 6: Verify Migration

```bash
cat .tidos/VERSION.md
# Expected: 2.0.0
ls .tidos/core/kernel.md
ls .tidos/TIDSTART.md
```

## Rollback Plan

If migration fails:

```bash
git submodule deinit .tidos
rm -rf .tidos
mv .tidos.backup .tidos
git checkout -- .gitmodules
```

## Post-Migration

1. Update AI agent instructions to reference `.tidos/TIDSTART.md`
2. Review `docs/tools/` for agent-specific configuration
3. Run startup sequence to verify system integrity
4. Update any custom scripts to use new paths
