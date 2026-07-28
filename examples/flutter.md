# TIDOS + Flutter Integration Example

## Project Type
Cross-platform mobile application using Flutter & Dart.

## TIDOS Connection

```bash
cd flutter_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/flutter.md` - Flutter & Dart specification
- `plugins/firebase.md` - Firebase services (if used)
- `plugins/firestore.md` - Firestore database (if used)

## Startup Sequence

1. Load TIDOS core and identity
2. Mount `flutter.md` plugin for framework-specific rules
3. Mount `plugins/docker.md` if containerized
4. Boot with `TIDSTART.md` protocol
5. Analyze Flutter project structure
6. Generate startup report

## Example Configuration

```yaml
# Tidos plugin: flutter
framework: flutter
state_management: bloc
architecture: clean
testing: flutter_test + bloc_test
```
