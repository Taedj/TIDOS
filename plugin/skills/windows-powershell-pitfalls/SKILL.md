---
name: windows-powershell-pitfalls
description: Avoid common Windows / PowerShell 5.1 traps: quoting, encodings, paths with spaces, stderr handling. Use when running or writing scripts on Windows.
---

# Windows & PowerShell pitfalls
- **No complex `python -c` one-liners** in PowerShell (quotes, apostrophes, unicode break them): write a temp `.py`.
- **Encoding**: PowerShell 5.1 reads scripts as ANSI unless they have a BOM - keep `.ps1` ASCII-only. A cp1252
  console can crash on unicode output: run Python with `PYTHONUTF8=1` before calling it a regression.
- **Paths with spaces/brackets**: quote everything; use `-LiteralPath` (brackets are wildcards for `-Path`).
- **Native stderr**: with `$ErrorActionPreference = 'Stop'`, `cmd 2>&1` turns normal stderr (e.g. git progress)
  into a fatal error. Check `$LASTEXITCODE` instead.
- **Culture**: number parsing/formatting depends on regional settings (`12,5` vs `12.5`); use
  `[CultureInfo]::InvariantCulture`.
- **Git Bash** has no `python3`; `/tmp` maps to the user temp folder; 8.3 short paths (`ABC~1`) differ from long ones.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
