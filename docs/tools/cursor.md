# Using TIDOS with Cursor

## Setup

Option A - Submodule:
```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

Option B - Multi-Root:
- Add TIDOS directory to Cursor workspace

## Configuration

Add `.tidos` to Cursor's allowed directories. Configure system prompt in Cursor settings to include TIDSTART.md reference.

## Startup

Cursor's AI agent will:
1. Load TIDSTART.md context from `.tidos/`
2. Mount core, engines, and rules
3. Apply matching plugins based on project analysis
4. Recover user memory from `.tidos/memory/`
