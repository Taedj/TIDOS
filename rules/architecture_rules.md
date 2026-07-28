# TIDOS Clean Architecture Rules (v3.0)

TIDOS mandates a strict 4-layer Clean Architecture model with unidirectional inward dependency rules across all target projects:

```
+-----------------------------------------------------------------------+
| 1. PRESENTATION LAYER (UI, Views, Widgets, Controllers, ViewModels)    |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 2. DOMAIN LAYER (Entities, Use Cases, Value Objects, Interactors)     |
+-----------------------------------------------------------------------+
                                  ^
                                  |
+-----------------------------------------------------------------------+
| 3. DATA LAYER (Repositories, Data Sources, DTO Models, Mappers)       |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 4. CORE / INFRASTRUCTURE LAYER (Network, Storage, Drivers, Config)    |
+-----------------------------------------------------------------------+
```

---

## Key Invariants
1. **Presentation Layer**: Renders UI, binds state. Must never import Data Sources or network drivers directly.
2. **Domain Layer**: Pure business entities and abstract repository interfaces. Zero dependencies on UI frameworks or external SDKs.
3. **Data Layer**: Implements Domain repository interfaces, manages caching, converts DTOs to Domain Entities.
4. **Feature-First Layout**: Structure codebases by feature (`features/<feature_name>/{data,domain,presentation}`) rather than monolithic layer folders.
