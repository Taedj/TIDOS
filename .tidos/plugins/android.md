# TIDOS Plugin: Android Native (Kotlin / Java)

## 1. Detection Rules
- **Signature Files**: `android/app/build.gradle`, `build.gradle.kts`, `AndroidManifest.xml`
- **File Extensions**: `.kt`, `.java`

## 2. Initialization Steps
- Verify Android SDK and Gradle wrapper configuration (`./gradlew --version`).
- Check target and minimum SDK versions in `build.gradle`.

## 3. Documentation to Generate
- `ANDROID_ARCHITECTURE.md`: Document Jetpack components, Coroutine scope rules, and Room DB schemas.

## 4. Best Practices
- Follow MVVM/MVI Jetpack architecture with `ViewModel` and `StateFlow`.
- Execute disk/network I/O strictly on `Dispatchers.IO`.

## 5. Coding Standards
- Require explicit Kotlin type declarations and null-safety guards.
- Use Jetpack Compose for declarative UI styling.

## 6. Review & Quality Rules
- Validate zero blocking `Thread.sleep()` or main-thread database calls.
- Verify ProGuard / R8 obfuscation rules for release builds.

## 7. Research Topics
- Kotlin Multiplatform (KMP), Compose Multiplatform, Android 15 API changes.
