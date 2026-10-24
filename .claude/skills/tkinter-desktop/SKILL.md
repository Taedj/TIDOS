---
name: tkinter-desktop
description: Tkinter desktop apps: widget lifecycle, layout, threading and packaging-safe paths. Use when building or fixing Tkinter UIs.
---

# Tkinter desktop
- **Lifecycle**: when you move (reparent) a widget into a new container, update EVERY reference used by
  destroy/reset guards - otherwise reset code destroys the new container. Grep for the old attribute name.
- **Layout**: never mix `pack` and `grid` in the same parent. Use frames per region.
- **Threads**: Tk is single-threaded; long work in a worker thread, UI updates via `root.after(...)`.
- **Empty/loading/error states** for every list or table view.
- **Batch actions** without a backend batch API: sequential calls with progress (`i/N`) and per-item error
  collection; do not change the backend contract.
- **Paths**: resolve data files relative to the executable when frozen (`sys._MEIPASS` / `sys.executable`).
- Test UI logic by separating it from widgets (pure functions/classes) so it runs headless.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
