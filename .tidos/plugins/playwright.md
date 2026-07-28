# TIDOS Plugin: Playwright E2E & Browser Automation Testing

## 1. Detection Rules
- **Signature Files**: `playwright.config.ts`, `playwright.config.js`
- **Dependencies**: `@playwright/test`

## 2. Initialization Steps
- Verify Playwright browser binaries installation (`npx playwright install`).
- Check test runner configuration file (`playwright.config.ts`).

## 3. Documentation to Generate
- `E2E_TESTING_GUIDE.md`: Document test suites, page object models (POM), and visual regression targets.

## 4. Best Practices
- Implement Page Object Models (POM) to encapsulate UI page interactions.
- Use auto-waiting Playwright locators (`getByRole`, `getByText`) instead of hardcoded `waitForTimeout()`.

## 5. Coding Standards
- Ensure tests run in parallel and remain completely independent and isolated.
- Capture trace files, screenshots, and video recordings on test failures for fast debugging.

## 6. Review & Quality Rules
- Validate zero fragile CSS/XPath locators susceptible to minor UI layout refactoring.
- Check cross-browser matrix coverage (Chromium, Firefox, WebKit).

## 7. Research Topics
- Playwright Component Testing, Visual Comparison testing (pixelmatch), Network mock interceptors.
