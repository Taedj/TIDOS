# TIDOS Plugin: Figma & Design System Integration

## 1. Detection Rules
- **Signature Files / Tokens**: `.figma/`, `figma.config.json`, design token files (`tokens.json`, `tailwind.config.js`)
- **Keywords**: `figma_tokens`, `design_system`

## 2. Initialization Steps
- Verify Figma API access token environment variable (`FIGMA_ACCESS_TOKEN`).
- Validate design token sync pipeline.

## 3. Documentation to Generate
- `DESIGN_SYSTEM_TOKENS.md`: Document color palettes, typography scale, spacing tokens, and component mappings.

## 4. Best Practices
- Map Figma styles directly to CSS variables or framework theme tokens (Flutter ThemeData / React Tailwind).
- Maintain 1-to-1 naming parity between Figma component names and codebase UI widgets.

## 5. Coding Standards
- Never hardcode hex color strings or arbitrary pixel values in component code; consume design tokens.
- Export responsive layout auto-layout parameters into flexible flexbox/grid containers.

## 6. Review & Quality Rules
- Validate UI component visual fidelity against target Figma mockups.
- Check WCAG 2.1 AA contrast ratios on imported Figma color tokens.

## 7. Research Topics
- Figma Variables API, Automated Token Sync via GitHub Actions, Code Connect component bindings.
