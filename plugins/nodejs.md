# TIDOS Plugin: Node.js Backend Services (v3.0)

## 1. Detection Rules
- **Signature Files**: `package.json` with `express`, `fastify`, `hono`, or `@nestjs/core`
- **File Extensions**: `.js`, `.ts`, `.mjs`

## 2. Initialization Steps
- Verify Node.js LTS runtime (`node --version`).
- Validate TypeScript compilation config (`tsconfig.json`).

## 3. Documentation to Generate
- `NODE_ARCHITECTURE.md`: Document service layer, middleware chain, and error propagation strategy.

## 4. Best Practices
- Structure handlers as thin controllers delegating to typed service classes.
- Use dependency injection for testable service composition.

## 5. Coding Standards
- Require TypeScript strict mode (`"strict": true` in `tsconfig.json`).
- Use Zod or Joi schemas for runtime request validation at API boundaries.

## 6. Review & Quality Rules
- Validate zero synchronous blocking I/O calls in request handlers.
- Ensure graceful shutdown handlers (`SIGTERM`, `SIGINT`) are registered.

## 7. Research Topics
- Bun runtime benchmarks vs Node, tRPC type-safe APIs, Node.js --experimental-permission model.
