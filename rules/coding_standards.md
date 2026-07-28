# TIDOS Clean Coding Standards (v3.0)

TIDOS enforces strict, language-idiomatic clean code standards:

---

## 1. Universal Naming Conventions
- **Files & Directories**: `snake_case` (e.g., `user_repository_impl.dart`, `auth_controller.ts`).
- **Classes & Enums**: `PascalCase` (e.g., `UserProfileScreen`, `NetworkException`).
- **Variables & Functions**: `camelCase` (e.g., `fetchUserData()`, `isSubscribed`).
- **Constants**: `SCREAMING_SNAKE_CASE` or `lowerCamelCase` with `k` prefix (e.g., `MAX_RETRY_COUNT`, `kDefaultTimeout`).

---

## 2. Code Quality & Maintainability Rules
- **SOLID Principles**: Single responsibility per class/file; code depends on abstractions, not implementations.
- **Zero Dead Code**: Unused variables, unreachable code, and debug statements (`print()`, `console.log()`) must be completely removed.
- **Typed Error Handling**: Domain failures are represented as typed failure objects or result unions, never raw unhandled exceptions.
- **Non-Silent Trapping**: Never swallow exceptions with empty `catch` blocks.
- **Lint Compliance**: Zero compiler errors or static analyzer lint warnings in modified files.
