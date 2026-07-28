# Using TIDOS with Windsurf

## Setup

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Integration

Windsurf's Cascade agent can reference TIDOS files directly:

1. Open `.tidos/TIDSTART.md` at session start
2. Follow the 9-step startup sequence
3. Load core, engines, rules, and plugins
4. Recover context from `.tidos/memory/`

## Best Practice

Pin the TIDSTART.md tab for quick reference during the session.
