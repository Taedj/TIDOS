# Using TIDOS with Antigravity IDE

## Setup

Add TIDOS as a multi-root workspace folder alongside your project.

## Integration

1. Open Antigravity IDE workspace settings
2. Add the TIDOS repository directory as a workspace folder
3. Reference `.tidos/TIDSTART.md` in agent system instructions
4. Agent automatically loads core, rules, and plugins on session start

## Multi-Root Benefits

- TIDOS stays out of project source tree
- Updates via `git pull` in TIDOS folder
- No submodule overhead
