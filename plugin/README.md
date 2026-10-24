# TIDOS plugin for Claude Code

TIDOS learns how your projects are built while you work with strong models, and guides weak or free models with
that knowledge.

## What it adds

- **Hooks** — record sessions into the private TIDOS brain (`~/.tidos/`); in GUIDE mode (weak models) they inject
  per-request guidance, block edits before the model has read the code, block "done" without a passing check, and
  stop the model after the same check fails 3 times.
- **MCP server `tidos`** — `tidos_start`, `tidos_guide`, `tidos_verify`, `tidos_recall`, `tidos_note`, `tidos_propose`.
- **Subagents** — `tidos-architect`, `tidos-reviewer`, `tidos-tester`, `tidos-security`, `tidos-researcher`,
  `tidos-uiux`, `tidos-mobile`.
- **Commands** — `/tidos <request>` (plan → implement → verify → review → learn) and `/TIDOSZIT` (control center).

## Install

The plugin runs code from your TIDOS checkout, so clone TIDOS first and run **START TIDOS** once (it records where
TIDOS lives in `~/.tidos/repo_path`; or set `TIDOS_REPO`). Then, in Claude Code:

```
/plugin marketplace add Taedj/TIDOS
/plugin install tidos@tidos
```

Requirements: Python 3.10+ on `PATH` as `python`. Everything TIDOS learns stays on your machine.
