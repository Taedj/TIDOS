# TIDOS Plugin: Flutter & Dart

## 1. Detection Rules
- **Signature File**: `pubspec.yaml`
- **Dependency Key**: `flutter:` under `dependencies:` or `dev_dependencies:`
- **File Extensions**: `.dart`

## 2. Initialization Steps
- Verify Flutter SDK installation (`flutter --version`).
- Run `flutter pub get` if `pubspec.lock` is missing or out of sync.
- Hydrate Flutter Riverpod / BLoC state management rules.

## 3. Documentation to Generate
- `FLUTTER_ARCHITECTURE.md`: Document state management choice, widget tree conventions, and platform channels.

## 4. Best Practices
- Separate UI widgets from state management using Riverpod or BLoC.
- Use `const` constructors aggressively across widget sub-trees.
- Avoid passing raw BuildContext across async gaps (`if (!context.mounted) return;`).

## 5. Coding Standards
- Enforce `flutter_lints` / `very_good_analysis` lint rules.
- Prefer `StatelessWidget` extracted sub-trees over long single `build()` methods.

## 6. Review & Quality Rules
- Check zero `setState()` calls in global app state.
- Validate `const` widget tree coverage.

## 7. Research Topics
- Flutter Web Wasm compilation, Impeller graphics engine benchmarks, Riverpod 3.0 updates.
