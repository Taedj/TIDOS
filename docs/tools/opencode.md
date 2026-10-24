# Using TIDOS with OpenCode

## 1. Get TIDOS

```bash
cd your-project
git clone https://github.com/Taedj/TIDOS.git TIDOS     # or: git submodule add https://github.com/Taedj/TIDOS.git TIDOS
```

## 2. Tell OpenCode how to start TIDOS

- Put the snippet in `AGENTS.md` at the project root, or in `~/.config/opencode/AGENTS.md` for every project.
- Model detection: automatic (OpenCode's last used model in `~/.local/state/opencode/model.json`).
- Free models are rated **weak** by default, so TIDOS runs in GUIDE mode and hands them the playbooks learned from your strong-model sessions. Re-rate a model in `~/.tidos/models.json`.

Snippet (Windows):

```markdown
## TIDOS
When the user says **START TIDOS**:
1. Run `.\TIDOS\start_tidos.ps1 -Tool opencode -Model <your model id>` from the project root (TIDOS checkout at `TIDOS/`).
   Pass your exact model id if you know it; otherwise leave `-Model`/`--model` out and TIDOS detects it.
2. Read the brief it prints and follow it for the whole session (LEARN mode on strong models,
   GUIDE mode on weak/free models).
3. If it reports an available TIDOS update, tell the user what it contains; install it only if they approve
   (re-run with `-ApplyUpdate` / `--apply-update`).
Never ask for, repeat or store passwords or tokens in the chat.
```

On Linux/macOS use `./TIDOS/scripts/start_tidos.sh --tool=opencode --model=<your model id>` instead.

## 3. Use it

Say **START TIDOS** at the beginning of a session. Open the control center with `/TIDOSZIT` (Claude Code) or `TIDOS/scripts/tidoszit.ps1`.
