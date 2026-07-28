# TIDOS Core Directory (`core/`)

The `core/` directory contains the protected runtime specification, identity baseline, and bootstrap discovery protocol of the Tidjani Development Operating System (v3.0).

## Directory Components

- [kernel.md](kernel.md): Central execution engine, state transitions, Protected OS Invariant, and Core Panic fault containment.
- [identity.md](identity.md): System stance, mission, vision, engineering philosophy, and Senior Principal Engineer behavioral profile.
- [bootstrap.md](bootstrap.md): Read-only target repository inspection, automated stack signature detection, and context recovery.

## Protection Rule

```
INVARIANT: All files in core/ are PROTECTED and read-only.
           They must NEVER be modified automatically by AI agents.
```
