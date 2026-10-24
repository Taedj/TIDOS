# TIDOS — Tidjani Development Operating System

TIDOS sits on top of the AI coding agent you already use (Claude Code, OpenCode, Gemini CLI, Cursor, Codex…).
It **learns** how work is done in your projects while you use a strong model, and it **guides** weak or free
models with that knowledge so they work better with you.

Version: see [`VERSION.md`](VERSION.md) · Plan & progress: [`docs/ENHANCEMENT_PLAN.md`](docs/ENHANCEMENT_PLAN.md)

---

## How it works

```
START TIDOS ─► detect tool + model ─► tier (config/models.json, ~/.tidos/models.json)
                     │
     strong model ───┴─── weak / free model
     LEARN mode            GUIDE mode
     work normally;        short brief (≤ 4 KB): rules for weak models, project facts,
     sessions recorded     how to check work, playbooks learned from strong models
            │                       │
            └──► ~/.tidos/  (private, never in a repository)
                 brain.db      every task: prompt, files, commands, checks, outcome, your corrections
                 playbooks/    how tasks are solved in each project (+ notes written by strong models)
                 memory/       your profile, preferences, lessons
```

## Quick start

1. Clone TIDOS next to (or inside) your project.
2. In your AI agent, say **`START TIDOS`**. The agent runs:
   - Windows: `.\start_tidos.ps1 -Tool <claude-code|opencode|...> -Model <model id>`
   - Linux/macOS: `./scripts/start_tidos.sh --tool=<tool> --model=<model id>`
   Model unknown? Leave it out: TIDOS reads it from the tool (Claude Code transcript, OpenCode state).
3. The agent follows the brief that START TIDOS prints (LEARN or GUIDE mode).

Updates: START TIDOS **reports** new releases and installs them only when you approve (`-ApplyUpdate`).

## What is inside

| Folder | What it does |
|---|---|
| `tidos_session/` | START TIDOS: model detection, tier, LEARN/GUIDE brief, private memory migration |
| `tidos_brain/` | Local trace store (`~/.tidos/brain.db`), Claude Code importer + hooks, kill switches |
| `tidos_learn/` | Turns recorded sessions into per-project and general playbooks |
| `tidos_dashboard/` | `/TIDOSZIT` control center (owner-only, localhost): status, live monitor, dungeons, security |
| `tidos_evals/` + `evals/` | "Dungeons": 30 verified coding tasks to check that TIDOS guidance really helps |
| `tidos_driver/` | Experimental external loop (checks first → implement → verify → escalate) |
| `scripts/` | START TIDOS, update gate, privacy firewall (`sanitizer.py`), persona sync, launchers |
| `core/`, `engines/`, `rules/`, `personas/`, `plugins/`, `checklists/`, `templates/` | Specs for strong models (LEARN mode) |
| `memory/` | Templates only — your real memory lives in `~/.tidos/memory/` |

Tool-specific setup: [`docs/tools/`](docs/tools/).

## Control center

`/TIDOSZIT` (or `scripts/tidoszit.ps1` / `.sh`) opens a local dashboard at `http://localhost:8767/`.
Login = your Google owner account **and** a control password typed in the browser (only its PBKDF2 hash is stored,
in Firestore, owner-only rules in `firebase/firestore.rules`). Kill switches there are enforced by the scripts.

## Safety and privacy

- Everything learned stays in `~/.tidos/` on your machine. Secrets, user paths, e-mails and IPs are redacted before
  storage; contributions go through the privacy firewall (`scripts/sanitizer.py`, gitleaks when installed).
- The update gate never touches a project that merely contains TIDOS files, never rewrites a fork's remote, never
  discards local work, and installs nothing without approval.
- Generated personas are proposed as pull requests; nothing reaches `main` without a human merge.
- Optional features with risk are off by default (GPTID browser relay, Google sign-in gate).

## Development

```bash
python -m pytest -q tests browser_relay/tests          # unit + security tests
python -I tidos_evals/__main__.py validate             # every dungeon fails untouched, passes with its solution
bash tests/update_gate_scenarios.sh sh                 # update-gate safety scenarios (ps1 on Windows)
```

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). License: [MIT](LICENSE).
