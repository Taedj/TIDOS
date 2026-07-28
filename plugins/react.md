# TIDOS Plugin: React & Frontend Applications (v3.0)

## 1. Detection Rules
- **Signature Files**: `package.json` containing `react`, `react-dom`
- **File Extensions**: `.jsx`, `.tsx`

## 2. Initialization Steps
- Verify Node.js package manager (`npm`, `pnpm`, `yarn`, `bun`).
- Validate ESLint & Prettier configuration files (`.eslintrc`, `.prettierrc`).

## 3. Documentation to Generate
- `REACT_GUIDANCE.md`: Document component hierarchy, state management (Zustand/Redux), and hook rules.

## 4. Best Practices
- Keep components small, functional, and single-purpose.
- Decouple server data fetching from UI using React Query (TanStack Query) or SWR.

## 5. Coding Standards
- Strictly adhere to Rules of Hooks (no conditional hook invocations).
- Use `useCallback` and `useMemo` deliberately for expensive computations, not prematurely.

## 6. Review & Quality Rules
- Validate zero prop drilling beyond 2 component levels (use Context/Zustand).
- Verify type completeness in TypeScript interfaces for all component props.

## 7. Research Topics
- React 19 Compiler (Forget), Server Actions, React Server Components (RSC).
