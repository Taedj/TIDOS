# TIDOS + Next.js Integration Example

## Project Type
Full-stack Next.js application with App Router and Server Components.

## TIDOS Connection

```bash
cd nextjs_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/nextjs.md` - Next.js specification
- `plugins/react.md` - React foundation
- `plugins/nodejs.md` - API routes
- `plugins/supabase.md` or `plugins/firebase.md` - Backend (if used)

## Key Rules Applied

- App Router conventions (layout.tsx, page.tsx, loading.tsx, error.tsx)
- Server Component by default, Client Component only when needed
- Route Handler patterns for API routes
- Middleware for authentication and redirects
- Image optimization with `next/image`

## Startup Report

```
Detected Stack: Next.js 14+ (App Router)
Active Plugins: nextjs.md, react.md, nodejs.md
```
