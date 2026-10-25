# Contributing to TIDOS

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

---

## 4. Skills, Subagents and Guidance Changes (quality gate)

Changes to `.claude/skills/`, `.claude/agents/`, `personas/` or the guidance code (`tidos_session/`, `tidos_learn/`)
are accepted only when they pass two gates:

1. **CI (automatic, every pull request)**: `scripts/check_contribution.py` rejects anything the privacy firewall
   would redact, unreviewed TIDOS drafts, private learned data, bad frontmatter or oversized files.
2. **Dungeon score (maintainer, before merging)**: the change must not lower the pass rate of a weak model
   guided by TIDOS. Measure it with a free model (no API cost):

   ```bash
   git fetch origin pull/123/head:pr-123
   python scripts/measure_proposal.py --branch pr-123 --agent opencode:opencode/big-pickle --min-difficulty B
   ```

   The same agent runs the GUIDE dungeons with TIDOS before and after the change (the eval runner and the
   dungeons are held constant). `Verdict: OK to merge (no drop)` is required; a drop means the change is
   reworked or declined.
