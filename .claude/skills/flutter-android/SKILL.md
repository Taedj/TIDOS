---
name: flutter-android
description: Flutter + Android work: analyzer-clean changes, Gradle/AGP/SDK version traps, release builds (apk/aab), signing and permissions. Use for Flutter apps targeting Android.
---

# Flutter + Android
- **Always** `flutter analyze` after edits; `flutter test` when tests exist. Fix analyzer errors before anything else.
- **Versions**: check `pubspec.yaml`, `android/settings.gradle(.kts)` (AGP, Kotlin), `gradle-wrapper.properties`,
  `compileSdk/targetSdk/minSdk`, Java version together - they must be compatible. Upgrade them as a set.
- **Builds**: `flutter build apk --release` / `flutter build appbundle`; bump `version: x.y.z+N` (N must increase
  for Play). Signing config comes from `key.properties` - never print or commit keystore passwords.
- **Permissions**: declare in AndroidManifest.xml AND request at runtime (camera, storage, notifications).
- **UI**: test small screens and text scaling for overflow; dispose controllers; no work in `build()`.
- **State**: after async gaps check `mounted` before using `context`.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
