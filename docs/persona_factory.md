# TIDOS Persona Factory — Operator Guide

The **Persona Factory** (`engines/persona_factory_engine.md`) is a self-learning persona-generation engine: it observes which stacks and domains users work on, and when it sees a pattern with no active persona, it **automatically** generates a new specialist persona, registers it, and pushes it to the central brain on GitHub (`origin/main`).

---

## Why it exists

Hand-crafted personas (like TIDOSTRADE, TIDOSUIUX) cover the stacks TIDOS was originally built for. As TIDOS users open projects in new domains (healthcare, blockchain, game-dev, IoT, machine-learning pipelines…), a dedicated persona gives better, more domain-appropriate guidance than a generic developer. The factory eliminates the manual step: it creates those personas for you.

## How it works (summary)

1. **Detection**: during `START TIDOS` and request analysis, the engine compares the detected stack and request vocabulary against existing persona routing signals.
2. **Trigger fires** when a stack or domain vocabulary has appeared across at least 2 distinct sessions and no active persona covers it.
3. **Generation**: a new `personas/tidos<name>.md` is written directly (OS Freeze exception, new files only), one routing row added to `personas/registry.md`, one evolution entry logged.
4. **Auto-sync**: `scripts/factory_sync.ps1/.sh` commits the persona + registry + evolution trio and pushes to `origin/main`. Every user's TIDOS picks it up next boot via the Update Gate.
5. **Learning loop**: repeated work in a domain builds the counter; deep domain vocabulary (3+ occurrences in `memory/PATTERNS.md`) strengthens the trigger.

## Operator commands

| Command | Effect |
|---|---|
| `TIDOS PERSONA FACTORY` | Run the detection + generation pipeline now (one-shot). Reports generated/skipped. |
| `STOP FACTORY` | Suspend generation for the rest of the current boot. |
| (automatic) | During normal `START TIDOS`, the factory evaluates passively and generates when triggered. |

## Configuration (config/framework.md)

```yaml
persona_factory:
  enabled: true
  os_freeze_exception: approved      # granted 2026-09-13
  triggers:
    stack_gap: true                  # uncovered stack seen >= 2 sessions
    domain_recurrence: true          # domain vocab across >= 2 requests, no coverage
  depth_threshold: 2                 # sessions/sources before generation
  auto_sync: true                    # commit + push to origin/main automatically
```

## Safety rules

- **New files only**: never edits or deletes an existing persona or registry row.
- **One factory run per boot** (dedupe).
- **`factory_sync` stages exactly 3 paths**: `personas/tidos<name>.md`, `personas/registry.md`, `evolution/SUGGESTIONS.md`. If any other file is dirty (unrelated), the script aborts (1) and reports what to stash/commit first.
- **Never force-push** (`factory_sync_force: false`).
- **TIDOS remains final authority** — auto-generated personas are advisors, not autonomous authorities, same as hand-crafted ones.
- **OS Freeze exception**: applies only to `personas/` (new-file), `personas/registry.md` (append-only), `evolution/SUGGESTIONS.md` (append-only). No other protected directory is written.

## Stopping or limiting the factory

- One-off suspend: `STOP FACTORY` (restores next boot).
- Permanent disable: set `persona_factory.enabled: false` in `config/framework.md`.
- Disable only stack triggers: set `stack_gap: false`.
- Increase depth threshold: raise `depth_threshold` to require more sessions before generation.

## FAQ

**Will it create too many personas?**
No — it needs the same domain/stack to appear across at least 2 distinct sessions before generating, so random project mentions won't spawn personas. You can tune this with `depth_threshold`.

**Can I rename a generated persona?**
Yes — rename the file, update the registry row manually, and commit. The factory won't touch it once it exists.

**What if it generates a persona for a domain I don't care about?**
Delete the generated `personas/tidos<name>.md` file and remove its registry row. Commit. The factory won't regenerate it unless the signal accumulates again across new sessions.

**Does the factory push automatically?**
Yes — when triggered, the `factory_sync` script commits the persona + registry + evolution trio and pushes to `origin/main`. If you'd rather review first, run `TIDOS PERSONA FACTORY -DryRun` to see what would be staged, then push manually with `git push`.

---

*Engine version 1.0 — 2026-09-13. OS Freeze exception granted by user.*