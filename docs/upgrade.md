# TIDOS Upgrade Guide

## Checking Current Version

```bash
cat .tidos/VERSION.md
```

## Upgrade Procedure

### Automatic Force-Update on `START TIDOS` (Recommended)

Whenever you prompt `START TIDOS` (or run `.\start_tidos.ps1` / `./start_tidos.sh`), TIDOS automatically executes Step 0 (Update Gate):
- Automatically connects to `https://github.com/Taedj/TIDOS.git`.
- Fetches `origin/main` and force-syncs all OS core files, engines, personas, and scripts.
- Even if an old clone exists, or the submodule is detached, or `.git` was previously removed, TIDOS force updates to the latest GitHub push.
- Preserves local user preferences and custom institutional memory in `memory/` and `evolution/`.

### Manual Upgrade Script

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/update.ps1

# Linux / macOS
bash scripts/update.sh
```

### Submodule Mode

```bash
cd .tidos
git fetch origin
git checkout main
git reset --hard origin/main
cd ..
git add .tidos
git commit -m "chore: force-update TIDOS to latest main"
```

## Version Compatibility

| From | To | Breaking Changes | Migration Notes |
|------|----|-----------------|-----------------|
| 1.x | 2.0.0 | Yes | Complete architecture refactor to centralized model. See `docs/migration_guide.md` |
| 2.0.0 | 3.0.0 | Minor | `kernel/` renamed to `core/`. Config directory added. Installation scripts added. |
| 3.0.0 | future | No | Backward-compatible enhancements via evolution layer |

## Release Workflow

1. Update `VERSION.md` with new SemVer tag
2. Update `CHANGELOG.md` with release notes
3. Tag the release: `git tag v3.0.0`
4. Push: `git push origin main --tags`
5. Create GitHub Release with changelog entry
