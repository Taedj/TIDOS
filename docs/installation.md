# TIDOS Installation Guide

## Prerequisites

- Git 2.30+
- Access to the TIDOS repository (canonical URL in `config/framework.md`)
- One of the supported AI coding agents

## Repository URL

The canonical TIDOS repository URL is defined in `config/framework.md`. If you move the repository to a new organization or rename it, update that single file instead of searching through dozens of documents.

## Installation Modes

### Method 1: Git Submodule (Recommended)

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
git submodule init
git submodule update
```

### Method 2: Git Clone

```bash
cd your-project
git clone https://github.com/tidjani/TIDOS.git .tidos
rm -rf .tidos/.git
```

### Method 3: Manual Download

1. Download the latest release from GitHub
2. Extract into `.tidos/` directory in your project root
3. Verify with `cat .tidos/VERSION.md`

### Method 4: Installation Script

```bash
# Linux/macOS
bash scripts/install.sh

# Windows PowerShell
.\scripts\install.ps1
```

## Verification

```bash
ls -la .tidos/VERSION.md          # Should contain version
ls -la .tidos/TIDSTART.md         # Should exist
ls -la .tidos/config/framework.md  # Should exist
```

Verify version matches expected:
```bash
cat .tidos/VERSION.md
```

## Next Steps

1. Read `.tidos/TIDSTART.md` for the startup protocol
2. Load core, engines, rules, and approach-appropriate plugins
3. Begin development with TIDOS governance active
