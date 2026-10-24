---
name: pyinstaller-exe
description: Package a Python app as a Windows .exe with PyInstaller: data files, hidden imports, paths, antivirus and testing the built exe. Use for desktop app releases.
---

# PyInstaller exe
1. Build from a clean venv with pinned requirements; `pyinstaller --noconfirm app.spec` (keep the .spec in git).
2. **Data files**: add via `datas=[(...)]`; at runtime resolve with `getattr(sys, "_MEIPASS", base_dir)`.
3. **Hidden imports** for plugins/dynamic imports (`hiddenimports=[...]`); read the build warnings.
4. `--windowed` for GUI apps; keep a console build for debugging.
5. **Test the built exe** on a clean machine/user: start, main flows, file paths with spaces and accents.
6. Antivirus false positives: avoid `--onefile` UPX compression when flagged; sign the exe if possible.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
