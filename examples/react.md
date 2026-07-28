# TIDOS + React Integration Example

## Project Type
React single-page application with modern hooks and state management.

## TIDOS Connection

```bash
cd react_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/react.md` - React SPA specification
- `plugins/web.md` - HTML5/CSS3 standards
- `plugins/docker.md` - Docker containerization (if used)

## Architecture Enforced

- Feature-first directory structure
- Custom hooks for reusable logic
- Context API or Zustand for state management
- React Router for navigation
- Vitest + React Testing Library for tests

## Startup Sequence

Load TIDOS -> Mount react.md plugin -> Analyze `src/` structure -> Generate startup report
