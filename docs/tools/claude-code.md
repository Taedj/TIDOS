# Using TIDOS with Claude Code

## 1. Get TIDOS

```bash
cd your-project
git clone https://github.com/Taedj/TIDOS.git TIDOS     # or: git submodule add https://github.com/Taedj/TIDOS.git TIDOS
```

## 2. Tell Claude Code how to start TIDOS

- Put the snippet in the project's `CLAUDE.md` (or `~/.claude/CLAUDE.md` for every project).
- Live recording into the brain (optional, recommended): run once in a terminal `python -I <TIDOS>/tidos_brain/__main__.py install-hooks` — it backs up `~/.claude/settings.json`, keeps your existing hooks, and `--uninstall` removes it. Restart Claude Code afterwards. Without hooks, START TIDOS still imports your sessions from Claude Code's transcripts.
- Control center command: copy `<TIDOS>/.claude/commands/TIDOSZIT.md` to `~/.claude/commands/` to get `/TIDOSZIT` in every project.
- Model detection: automatic (read from the session transcript).

Snippet (Windows):

```markdown
## TIDOS
When the user says **START TIDOS**:
1. Run `.\TIDOS\start_tidos.ps1 -Tool claude-code -Model <your model id>` from the project root (TIDOS checkout at `TIDOS/`).
   Pass your exact model id if you know it; otherwise leave `-Model`/`--model` out and TIDOS detects it.
2. Read the brief it prints and follow it for the whole session (LEARN mode on strong models,
   GUIDE mode on weak/free models).
3. If it reports an available TIDOS update, tell the user what it contains; install it only if they approve
   (re-run with `-ApplyUpdate` / `--apply-update`).
Never ask for, repeat or store passwords or tokens in the chat.
```

On Linux/macOS use `./TIDOS/scripts/start_tidos.sh --tool=claude-code --model=<your model id>` instead.

## 3. Use it

Say **START TIDOS** at the beginning of a session. Open the control center with `/TIDOSZIT` (Claude Code) or `TIDOS/scripts/tidoszit.ps1`.
