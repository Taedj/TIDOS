---
name: tool-scout
description: Find, vet and propose a tool for a missing capability (linter, scanner, test runner, MCP server): search, check trust signals, try it in a sandbox, propose install - never install silently. Use when a project lacks a check or capability.
---

# Tool scout
1. **Need**: state the missing capability and why (e.g. "no secret scanner", "no Dart test coverage").
2. **Search** official sources first (project docs, GitHub, package registries, MCP registries).
3. **Trust signals**: maintained (recent releases/commits), license, stars/downloads, number of maintainers,
   open security advisories (OSV), install method (official releases, no curl|bash from unknown hosts).
4. **Sandbox try**: temp folder or container; run it on a copy; check what it writes/reads/sends.
5. **Propose** to the user: what, why, trust summary, exact install command, how TIDOS will use it.
   Never install, enable or configure a tool without the user's explicit OK.

With TIDOS installed, the scout CLI does steps 1-3 and 5 for you (it never installs anything):
`python -I <TIDOS>/tidos_scout/__main__.py needs --project . --trust` (missing capabilities + trust 0-100),
`... search "capability words"`, `... vet NAME` (installed tools only), `... propose NAME` (prints the command).

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
