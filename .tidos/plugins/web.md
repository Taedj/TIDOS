# TIDOS Plugin: Web Applications (Vanilla HTML5 / CSS3 / Web Standards)

## 1. Detection Rules
- **Signature Files**: `index.html`, `styles.css`, `public/index.html`
- **File Extensions**: `.html`, `.css`, `.js`

## 2. Initialization Steps
- Verify HTML5 semantic document structure.
- Check CSS reset / global design system token initialization.

## 3. Documentation to Generate
- `WEB_STANDARDS.md`: Document CSS token architecture, accessibility targets, and performance SLAs.

## 4. Best Practices
- Use semantic HTML elements (`<header>`, `<nav>`, `<main>`, `<article>`, `<footer>`).
- Enforce modern CSS variables for design system tokens (colors, fonts, spacing).

## 5. Coding Standards
- Require WCAG 2.1 AA color contrast and semantic ARIA attributes.
- Avoid inline styles; use clean external style sheets.

## 6. Review & Quality Rules
- Validate Lighthouse Performance and Accessibility scores (>90).
- Verify responsive layout across mobile, tablet, and desktop viewports.

## 7. Research Topics
- Native CSS Container Queries, Web Components, Service Worker caching strategies.
