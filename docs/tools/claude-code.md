# Using TIDOS with Claude Code

## Setup

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Configuration

Add to `~/.claude/settings.json` or project `.claude/settings.json`:

```json
{
  "systemPrompt": "Load TIDOS from .tidos/TIDSTART.md before responding"
}
```

## Usage

Claude Code supports the `.tidos/` convention. The agent will:
1. Read `.tidos/TIDSTART.md` for startup protocol
2. Load core specifications
3. Mount plugins matching detected stack
4. Read `memory/` for user preferences
