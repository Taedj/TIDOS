# Patterns

## Architectural Patterns

### Clean Architecture Layers
```
domain/    -> Entities, Use Cases, Repository Interfaces
data/      -> Repository Implementations, DTOs, Data Sources
presentation/ -> Widgets/Components, ViewModels/Controllers
```

### Feature-First Structure
```
features/<feature_name>/
  domain/
  data/
  presentation/
```

## Code Patterns

### Repository Pattern
```dart
abstract class Repository {
  Future<Result<T>> get<T>(String id);
  Future<Result<void>> save<T>(T entity);
}
```

### BLoC/Cubit Pattern (Flutter)
```dart
class FeatureCubit extends Cubit<FeatureState> {
  final FeatureRepository repository;
}
```

## Integration Patterns

### Service Injection
- Constructor injection for all dependencies
- Abstract interfaces for all services
- Factory providers for platform-specific implementations

## Readiness Patterns (verified 2026-09-22, GPTID relay)

### Single semantic-first detector
```
SEMANTIC signals (textarea, contenteditable, role=textbox)
  → registry fallback chain (never primary)
  → usability = visible + enabled + editable, reject disabled/aria-disabled
```
One function (`find_usable_composer`) serves startup classification, monitor probes, and diagnostics — never two definitions of ready.

### Total-budget probing (no multiplication)
```python
deadline = now + budget_ms            # caps the WHOLE operation
per_candidate_slice = min(1000, remaining)
```
`_classify` (10s) and `quick_ready` (5s) share semantics; only cadence/budget differ.

### Adapter-truth state reconciliation
```
dead page  => ERROR   (never retain READY)
LOADING    => downgrade cached READY to BROWSER_READY
READY      => only on live page + usable composer
```
One `sync_relay_state` transition function; relay state derives from adapter truth. Terminal reasons carry a `DEAD:` marker so monitors can downgrade instead of ignoring failures.
