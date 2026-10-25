---
description: Open the TIDOS Control Center (login in the browser) and list every TIDOS / command
---

Open the TIDOS Control Center.

1. Find the TIDOS checkout: use `$TIDOS_HOME` if it is set, otherwise the folder that contains
   `tidos_dashboard/__main__.py` (the current workspace, `.tidos/`, or `TIDOS/`).
2. Run its launcher **once**:
   - Windows: `powershell -NoProfile -ExecutionPolicy Bypass -File "<TIDOS>/scripts/tidoszit.ps1"`
   - Linux/macOS/Git Bash: `bash "<TIDOS>/scripts/tidoszit.sh"`
3. Run `python -I "<TIDOS>/tidos_session/__main__.py" commands` and show the user the list of TIDOS
   commands it prints (every `/` command TIDOS adds to this tool).
4. Reply in one or two lines: the control center is open at http://localhost:8767/ and the user must
   sign in **in the browser** with their Google owner account, then enter the control password there.

Rules:
- NEVER ask for, accept, repeat or store the control password in this chat or any terminal command.
  If the user types it here, tell them to change it from the Security panel.
- Do not open the dashboard pages yourself or try to log in.
- To stop it later: the same launcher with `-Stop` (PowerShell) or `--stop` (bash).
