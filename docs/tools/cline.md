# Using TIDOS with Cline

## Setup

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Custom Instructions

Add to Cline's custom instructions in IDE settings:

```
This project uses TIDOS (Tidjani Development Operating System).
Read .tidos/TIDSTART.md before responding to any request.
The .tidos/ directory contains core, rules, and user memory.
Never modify files in .tidos/core/, .tidos/engines/, .tidos/rules/, .tidos/plugins/, etc.
```

## Startup Flow

Cline reads `.tidos/` files on session start and applies the full TIDOS startup sequence.
