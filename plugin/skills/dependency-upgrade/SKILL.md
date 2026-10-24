---
name: dependency-upgrade
description: Upgrade a library, SDK or toolchain safely: read the changelog, upgrade one thing, fix breaking changes, verify. Use for Flutter/Dart, npm, pip, Gradle/AGP upgrades.
---

# Dependency upgrade
1. **Inventory**: current version (lockfile/manifest), target version, and why.
2. **Read the official changelog / migration guide** between the two versions; list breaking changes that touch
   this project (search the code for each removed or renamed API).
3. **Upgrade one dependency (or one coherent group)** at a time. Update the lockfile with the tool
   (`flutter pub upgrade <pkg>`, `npm install <pkg>@<v>`, `pip install -U`), never by hand.
4. **Fix compile/analyze errors**, then run tests and a build of the real artifact (apk/aab, web, exe).
5. **Check transitive conflicts** and minimum platform/SDK changes (Android minSdk, Java/Gradle, Node, Python).
6. Commit per upgrade with the changelog link. Never upgrade everything at once in one blind step.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
