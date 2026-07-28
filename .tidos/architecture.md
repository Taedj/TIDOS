# TIDOS Universal Architecture Specification (v1.0)

The **TIDOS Architecture Engine** (`architecture.md`) defines the universal software design, structural topology, and domain layer separation standards for all TIDOS-governed projects. Positioned at **Level 3** in the TIDOS Subsystem Boot Hierarchy, this specification ensures codebases remain modular, scalable, maintainable, and secure.

---

## 1. Core Architectural Framework

### Clean Architecture & Layer Separation
TIDOS mandates a strict 4-layer Clean Architecture model with unidirectional inward dependency rules:

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

#### Layer Responsibilities & Rules
1. **Presentation Layer**: Renders UI, receives user input, binds local state. Must never import Data Sources or network drivers directly.
2. **Domain Layer**: Contains core business rules, pure entities, and abstract repository interfaces. Must have **zero dependencies** on UI frameworks, HTTP clients, or external SDKs.
3. **Data Layer**: Implements Domain repository interfaces, manages caching strategies, converts DTOs to Domain Entities, and interfaces with external APIs.
4. **Core / Infrastructure Layer**: Provides low-level drivers, environment config, logger instances, and system utilities.

---

## 2. Modular & Feature-Based Organization

Codebases must be structured by **Feature** rather than by technical layer type at the root level.

### Standard Feature Directory Layout
```
lib/ or src/
├── core/                        # Shared infrastructure & utilities
│   ├── config/                  # App constants & env schemas
│   ├── error/                   # Failure classes & exception handlers
│   ├── network/                 # HTTP/gRPC clients & interceptors
│   ├── theme/                   # Design system tokens & styles
│   └── utils/                   # Pure helper functions
│
├── features/                    # Feature modules
│   ├── auth/                    # Authentication feature module
│   │   ├── data/                # DTOs, data sources, repository impls
│   │   ├── domain/              # Entities, use cases, repository contracts
│   │   └── presentation/        # Screens, components, state management
│   │
│   ├── profile/                 # User profile feature module
│   │   ├── data/
│   │   ├── domain/
│   │   └── presentation/
│   │
│   └── dashboard/               # Dashboard feature module
│
└── main.dart (or index.ts / main.py / main.go)
```

---

## 3. Universal Design Standards

### 3.1 Naming Conventions
- **Files & Directories**: `snake_case` (e.g., `user_repository_impl.dart`, `auth_controller.ts`).
- **Classes & Enums**: `PascalCase` (e.g., `UserProfileScreen`, `NetworkException`).
- **Variables & Functions**: `camelCase` (e.g., `fetchUserData()`, `isSubscribed`).
- **Constants**: `SCREAMING_SNAKE_CASE` or `lowerCamelCase` with `k` prefix per language idioms (e.g., `MAX_RETRY_COUNT`, `kDefaultTimeout`).

### 3.2 Dependency Management (SOLID Principles)
- **Dependency Inversion**: High-level modules must depend on abstractions (interfaces), never on low-level concrete implementations.
- **Single Responsibility**: Each class/file must have exactly one reason to change.
- **Explicit Injection**: Pass dependencies via constructors; avoid hidden singleton calls inside business logic.

### 3.3 Error Handling & Exception Protocols
- **Domain Failure Union Types**: Represent errors explicitly using Result/Either types or typed domain failures rather than raw string exceptions.
- **Boundary Exception Trapping**: Catch low-level network/DB exceptions in the Data Layer and map them to domain-specific failures before exposing them to the Domain/UI layers.
- **Non-Silent Exception Protocol**: Never swallow exceptions with empty `catch` blocks. Always log or propagate context-rich failure details.

### 3.4 Structured Logging & Observability
- Log entries must be structured with severity levels (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`).
- Never log sensitive user credentials, access tokens, PII (Personally Identifiable Information), or encryption keys.

### 3.5 Configuration & Environment Management
- Environment variables must be loaded from `.env` files via strongly-typed config schemas (e.g., `AppConfig.env`).
- Never hardcode API base URLs, secret keys, or environment flags in application source code.

### 3.6 Security by Design
- **Zero-Trust Input Sanitization**: Treat all incoming user inputs, route params, and third-party payloads as untrusted.
- **Secret Isolation**: Store secrets in environment management systems or key vaults. Keep secrets out of client-side binaries.
- **Least Privilege Access**: Restrict storage, DB, and API permissions strictly to required execution boundaries.

### 3.7 Performance & Caching Design
- **Lazy Loading**: Initialize heavy singletons, modules, and routes on-demand rather than during application cold-start.
- **Two-Tier Caching Strategy**: Utilize fast memory cache (RAM) backed by persistent disk cache (SQLite / Hive / IndexedDB) with explicit TTL (Time-To-Live) expiration.
- **Async Non-Blocking Operations**: Run expensive CPU tasks off the main thread/event loop using isolates, web workers, or background thread pools.

---

## 4. Technology-Specific Architecture Guidelines

### 4.1 Flutter & Dart
- **State Management**: Enforce strict separation of UI from logic using Riverpod or BLoC. UI widgets must remain purely declarative.
- **Widget Tree Optimization**: Use `const` constructors aggressively. Extract sub-trees into independent `StatelessWidget` classes to restrict rebuild bounds.
- **Platform Channels**: Encapsulate native Swift/Kotlin/C++ interactions behind abstract Dart interfaces.

### 4.2 Firebase & Cloud Infrastructure
- **Serverless Architecture**: Keep Cloud Functions single-purpose, stateless, and idempotent.
- **Security Rules**: Enforce explicit ownership and authentication checks in `firestore.rules` and `storage.rules`. Never deploy wildcard `allow read, write: if true;` rules.

### 4.3 Firestore Database Architecture
- **Schema Strategy**: Design collections to favor read performance. Denormalize small, frequently accessed lookup data to prevent expensive nested reads.
- **Subcollection vs Top-Level**: Use subcollections for hierarchical data owned exclusively by a parent entity; use top-level collections for data queried across entities.
- **Query Bounds**: Every query must include explicit `limit()` constraints. Use composite indexes for multi-field filtering.

### 4.4 Supabase Backend Architecture
- **PostgreSQL Relational Design**: Maintain 3NF normalization for core database tables.
- **Row Level Security (RLS)**: Enforce RLS on **every** table. Validate `auth.uid()` against table owner foreign keys in RLS policies.
- **Realtime Optimization**: Scope Realtime subscriptions to explicit table rows or filter channels to minimize socket memory usage.

### 4.5 Android Native (Kotlin)
- **Jetpack Architecture**: Structure applications using MVVM/MVI with `ViewModel`, `StateFlow`/`SharedFlow`, and Jetpack Compose.
- **Coroutines & Threading**: Dispatch disk/network operations on `Dispatchers.IO`, heavy computation on `Dispatchers.Default`, and UI state updates on `Dispatchers.Main`.
- **Database & Storage**: Use Room ORM with typed DAOs and explicit SQL migration strategies.

### 4.6 Desktop (Cross-Platform / Electron / Tauri / Flutter Desktop)
- **Window State Preservation**: Persist window coordinates, size, and layout state across application restarts.
- **IPC Isolation**: Restrict Inter-Process Communication (IPC) channels to explicit whitelist bridge protocols.
- **Local Storage Security**: Store sensitive local user data in OS-level secure storage (Windows Credential Manager, macOS Keychain, Linux Secret Service).

### 4.7 Web Architecture (Next.js / Vite / React)
- **Rendering Strategy**: Choose explicit rendering boundaries: Server-Side Rendering (SSR) for dynamic SEO, Static Site Generation (SSG) for static content, and Client-Side Rendering (CSR) for interactive dashboards.
- **Bundle Optimization**: Implement route-based code splitting, dynamic imports, and image/font optimization.
- **State Isolation**: Use local state for component UI, Context/Zustand for feature state, and React Query/SWR for server cache synchronization.
