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
