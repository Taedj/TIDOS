# TIDOS Upgrade Guide

## Checking Current Version

```bash
cat .tidos/VERSION.md
```

## Upgrade Procedure

### Submodule Mode

```bash
cd .tidos
git fetch origin
git checkout v3.0.0
cd ..
git add .tidos
git commit -m "chore: upgrade TIDOS to v3.0.0"
```

### Local Copy Mode

```bash
rm -rf .tidos
git clone https://github.com/tidjani/TIDOS.git .tidos
rm -rf .tidos/.git
```

### Multi-Root Mode

```bash
cd TIDOS
git pull origin main
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
