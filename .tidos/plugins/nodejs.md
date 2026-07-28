# TIDOS Plugin: Node.js & Server Systems

## 1. Detection Rules
- **Signature Files**: `package.json` (without frontend framework bindings)
- **File Extensions**: `.js`, `.ts`, `.mjs`, `.cjs`

## 2. Initialization Steps
- Verify Node.js runtime version (`node -v`).
- Run package audit (`npm audit` / `pnpm audit`).

## 3. Documentation to Generate
- `NODE_BACKEND_SPEC.md`: Document service architecture, middleware stack, and error handling.

## 4. Best Practices
- Structure services using Clean Architecture (Controller -> Service -> Repository).
- Use async/await throughout; handle promise rejections with centralized middleware.

## 5. Coding Standards
- Log all uncaught exceptions (`uncaughtException`, `unhandledRejection`) before graceful process exit.
- Isolate configuration loading via typed `dotenv` schemas.

## 6. Review & Quality Rules
- Validate zero blocking synchronous filesystem calls (`fs.readFileSync`) in server event loops.
- Verify security middleware (`helmet`, `cors`, rate limiting).

## 7. Research Topics
- Node.js native test runner, TypeScript 5.x features, Fastify vs Express performance benchmarks.
