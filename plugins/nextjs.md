# TIDOS Plugin: Next.js Full-Stack Framework (v3.0)

## 1. Detection Rules
- **Signature Files**: `next.config.js`, `next.config.mjs`, `next.config.ts`
- **Dependencies**: `next` in `package.json`

## 2. Initialization Steps
- Verify Node.js runtime and package manager (`npm`, `pnpm`, `yarn`, `bun`).
- Check `app/` vs `pages/` router directory structure.

## 3. Documentation to Generate
- `NEXTJS_ARCHITECTURE.md`: Document routing strategy, data fetching layers, and middleware.

## 4. Best Practices
- Prefer App Router (`app/`) with React Server Components (RSC) for new projects.
- Use Server Actions for form mutations instead of dedicated API routes.
- Implement route-level `loading.tsx` and `error.tsx` boundary components.

## 5. Coding Standards
- Separate server-only logic from client components using `'use client'` directive.
- Define metadata exports (`generateMetadata`) for SEO on every page.

## 6. Review & Quality Rules
- Validate zero client-side `fetch()` calls that should use Server Components.
- Verify middleware runs only on intended route matchers.

## 7. Research Topics
- Next.js Turbopack production readiness, Partial Prerendering (PPR), Server Actions streaming.
