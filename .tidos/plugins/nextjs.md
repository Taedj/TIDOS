# TIDOS Plugin: Next.js Full Stack Framework

## 1. Detection Rules
- **Signature Files**: `next.config.js`, `next.config.mjs`, `next.config.ts`
- **Dependencies**: `next` in `package.json`

## 2. Initialization Steps
- Verify App Router directory structure (`app/`) or Pages Router (`pages/`).
- Check environment variable config (`.env.local`).

## 3. Documentation to Generate
- `NEXTJS_ARCHITECTURE.md`: Document rendering strategies (SSR/SSG/ISR), Route Handlers, and Server Actions.

## 4. Best Practices
- Default to React Server Components (RSC) in App Router; add `'use client'` only when interaction/state is required.
- Implement API endpoints via App Router Route Handlers (`app/api/.../route.ts`).

## 5. Coding Standards
- Use `next/image` for image optimization and `next/font` for web font loading.
- Validate incoming request body in Route Handlers using Zod schemas.

## 6. Review & Quality Rules
- Validate zero sensitive server environment keys exposed in client bundles (`NEXT_PUBLIC_` prefix checks).
- Check build output (`npm run build`) for static vs dynamic route compilation.

## 7. Research Topics
- Next.js Partial Prerendering (PPR), Middleware edge optimization, Server Actions security.
