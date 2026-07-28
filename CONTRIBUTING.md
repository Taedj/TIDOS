# Contributing to TIDOS Framework (v3.0)

Thank you for your interest in contributing to **TIDOS (Tidjani Development Operating System)**! TIDOS is a centralized, version-controlled AI Development Operating System designed to provide consistent, principal-grade AI engineering governance across codebases.

---

## 1. Operating System Freeze & Contribution Rules

1. **System Core Immutability**: Core directories (`core/`, `engines/`, `personas/`, `rules/`, `commands/`, `checklists/`, `templates/`, `plugins/`, `prompts/`) are protected system files.
2. **Evolutionary Suggestions**: New feature proposals, rule enhancements, or bug fixes must be submitted as non-invasive entries in `evolution/SUGGESTIONS.md` before core modification PRs are merged.
3. **Pull Request Protocol**:
   - Every PR must target the `main` branch.
   - All PRs must include updated tests/verification checks.
   - Breaking architectural changes require a MAJOR SemVer version proposal.

---

## 2. Development Setup

```bash
# Clone official TIDOS repository
git clone https://github.com/tidjani/TIDOS.git
cd TIDOS

# Run verification checks
git status
```

---

## 3. Submitting New Plugins or Templates

- **New Technology Plugins**: Place in `plugins/<technology>.md` following the mandatory 8-part plugin schema.
- **New Templates**: Place in `templates/<name>.md` ensuring zero project-specific hardcoded data.
