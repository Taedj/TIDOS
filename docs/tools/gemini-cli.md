# Using TIDOS with Gemini CLI

## Setup

```bash
cd your-project
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Configuration

Gemini CLI uses a project-level configuration file. Add TIDOS context to your prompt preamble:

```
System context: TIDOS AI Development Operating System is at .tidos/
Read .tidos/TIDSTART.md for startup sequence.
Load kernel from .tidos/core/
Apply rules from .tidos/rules/
Mount plugins from .tidos/plugins/
```

## Usage

Gemini CLI processes the `.tidos/` files as context before responding to user prompts.
