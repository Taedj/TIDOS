# Using TIDOS with Gemini CLI

## 1. Get TIDOS

```bash
cd your-project
git clone https://github.com/Taedj/TIDOS.git TIDOS     # or: git submodule add https://github.com/Taedj/TIDOS.git TIDOS
```

## 2. Tell Gemini CLI how to start TIDOS

- Put the snippet in `GEMINI.md` at the project root, or `~/.gemini/GEMINI.md` for every project.
- Pass `-Model` explicitly (e.g. `gemini-2.5-pro`); automatic detection for Gemini CLI is not implemented yet.
- Gemini Pro models are rated frontier (LEARN mode), Flash models medium, Flash-Lite weak (GUIDE mode).

Snippet (Windows):

```markdown
## TIDOS
When the user says **START TIDOS**:
1. Run `.\TIDOS\start_tidos.ps1 -Tool gemini-cli -Model <your model id>` from the project root (TIDOS checkout at `TIDOS/`).
   Pass your exact model id if you know it; otherwise leave `-Model`/`--model` out and TIDOS detects it.
2. Read the brief it prints and follow it for the whole session (LEARN mode on strong models,
   GUIDE mode on weak/free models).
3. If it reports an available TIDOS update, tell the user what it contains; install it only if they approve
   (re-run with `-ApplyUpdate` / `--apply-update`).
Never ask for, repeat or store passwords or tokens in the chat.
```

On Linux/macOS use `./TIDOS/scripts/start_tidos.sh --tool=gemini-cli --model=<your model id>` instead.

## 3. Use it

Say **START TIDOS** at the beginning of a session. Open the control center with `/TIDOSZIT` (Claude Code) or `TIDOS/scripts/tidoszit.ps1`.
