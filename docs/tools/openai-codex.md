# Using TIDOS with OpenAI Codex

## Setup

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Configuration

Add to Codex system instructions:

```
You have access to .tidos/ which contains the TIDOS AI Development Operating System.
Before responding, read .tidos/TIDSTART.md and follow the startup sequence.
Apply core rules, architecture standards, and user memory.
Never modify .tidos/core/, .tidos/engines/, or other protected directories.
```

## Considerations

OpenAI Codex benefits from explicit system instructions to load TIDOS context. The `.tidos/` directory should be in the accessible file scope.
