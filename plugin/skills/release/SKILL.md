---
name: release
description: Cut a release: version bump, changelog, checks, build, tag. Deploy and store uploads only with the user's explicit OK. Use for 'bump version', 'create aab/apk', 'release', 'deploy'.
---

# Release
1. **Clean state**: `git status` clean, on the right branch, checks green.
2. **Version bump** in the single source of truth (pubspec.yaml `x.y.z+build`, package.json, VERSION file);
   semantic versioning; build number always increases.
3. **Changelog / release notes** from the commits since the last tag, written for users.
4. **Build the artifact** (`flutter build appbundle`, `flutter build web`, exe) and confirm it exists and starts.
5. **Ask before publishing**: show the exact deploy/upload command and wait for an explicit OK
   (`firebase deploy --only hosting`, Play Console upload, store listing).
6. **Tag** the release (`git tag -a vX.Y.Z`), note what was deployed where.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
