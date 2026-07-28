# Using TIDOS with OpenCode

## Setup

Add TIDOS as a submodule in your project. The canonical repository URL is defined in `config/framework.md`.

```bash
# See config/framework.md for the authoritative URL
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Startup Sequence

When starting a new session:

1. Read `.tidos/config/framework.md` for repository metadata
2. Reference `TIDSTART.md` to execute the 9-step protocol
3. Load core, engines, rules, personas, and plugins from `.tidos/`
4. Recover project context from `.tidos/memory/`
5. TIDOS provides structured command support via `.tidos/commands/session_commands.md`
