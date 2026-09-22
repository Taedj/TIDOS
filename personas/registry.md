# TIDOS Persona Registry & Auto-Routing Table (v1.0)

> **Purpose**: Lets TIDOS smartly auto-select the right persona for any request in any mounted project.
> **Governance**: TIDOS Core (`core/kernel.md`) takes precedence. Explicit user keyword always overrides the router.
> New personas MUST add a row here plus a `## Routing Signals` block in their own spec file.

---

## 1. Routing Algorithm (runs in Workflow Stage 2, complements Stage 4)

```text
1. EXPLICIT OVERRIDE: request contains a bare persona keyword (TIDOSTRADE / TIDOSUIUX)
   → activate that persona immediately. Skip scoring.
2. SCORE: for each persona, count intent-signal hits in the request (Sec 2),
   +1 if Bootstrap stack detection matches its stack weights,
   +1 if target project context matches its project weights.
3. ACTIVATE: single highest score >= 2 → auto-activate + announce:
   `TIDOS persona active: <NAME> — <reason>.`
4. ASK: tie for highest score, or highest score == 1 → ask user which persona
   (suggest-only fallback), then activate the chosen one.
5. DEFAULT: every score is 0 → no specialist-persona activation; continue with
   `personas/roles.md` specialists via Stage 4 Expert Consultation.
```

---

## 2. Persona Signal Map

### TIDOSTRADE — Binary Options Trading Intelligence (`personas/tidostrade.md`)

- **Trigger keyword**: `TIDOSTRADE`
- **Intent signals**: backtest, strategy, strategies, payout, candle, candlestick, expiry, martingale, win rate, expectancy, expected value, indicator, signal convergence, regime, calibration, overfitting, drawdown, stake, smartrad, trading, binary option
- **Stack weights (+1)**: Python backtesting/notebook stack (`pyproject.toml`, `*.ipynb`, `pandas`/`numpy`); trading-data pipelines
- **Project weights (+1)**: target workspace is SMARTRAD (or trading-named project)

### TIDOSUIUX — Universal UI/UX & Product Design (`personas/tidosuiux.md`)

- **Trigger keyword**: `TIDOSUIUX`
- **Intent signals**: ui, ux, design, redesign, accessibility, screen, layout, responsive, adaptive, widget, theme, typography, navigation flow, usability, user journey, wireframe, mockup, figma, contrast, information architecture, design system
- **Stack weights (+1)**: Flutter (`pubspec.yaml`), React/Next.js (`package.json` + `*.tsx`), any `ThemeData`/design-token setup
- **Project weights (+1)**: none (domain-agnostic by design — scores on intent + stack only)

### GPTID — ChatGPT Interface & Reasoning Relay (`personas/tidosgptid.md`)

- **Trigger keyword**: `GPTID`
- **Intent signals**: gptid, chatgpt relay, chatgpt review, browser relay, chatgpt free, second opinion, external review, ask chatgpt, chatgpt audit, chatgpt debug
- **Stack weights (+1)**: none (transport persona — scores on intent only, works in any project)
- **Project weights (+1)**: none (domain-agnostic by design)

---

## 3. Threshold & Tie Rules

- **Activation threshold**: `score >= 2`.
- **Tie**: two personas share the highest score → ASK (list both + reasons, user picks).
- **Weak signal**: single highest score == 1 → ASK. **No signal**: all scores 0 → `roles.md` default, no ASK.
- **Cross-domain requests** (e.g., "redesign the SMARTRAD dashboard"): both personas may score — report both scores, activate the higher; on tie, ASK and offer collaboration order (domain persona first for requirements, TIDOSUIUX for interface).
- **Announcement is mandatory** on every auto-activation (reason = top matched signals).

---

## 4. Maintenance Rule

Every new persona spec MUST include a `## Routing Signals` block (trigger keyword + intent signals + stack/project weights) and a matching row in Section 2 above. Removing a persona MUST remove its row. Registry edits are additive and backward compatible — manual keywords keep working regardless of registry state.

## 5. Persona Factory (auto-generated personas)

Rows may also be added by the **Persona Factory** (`engines/persona_factory_engine.md`) when a stack-gap or recurring-domain signal (>= 2 sources) has no active coverage — granted OS Freeze exception (2026-09-13). Factory conventions:

- **New-file only**: the factory creates `personas/tidos<domain>.md`; it never edits or deletes existing personas or rows.
- **One row + one evolution entry** per generated persona, committed + pushed to `origin/main` via `scripts/factory_sync.ps1/.sh`.
- **Trigger keyword** is always the bare persona name (`TIDOS<DOMAIN>`, e.g. `TIDOSDEVX`); manual keywords override the router.
- Auto-synced personas are advisory specialist personas under the same governance as hand-made ones (TIDOS remains final authority).
- Diagnostic command: `TIDOS PERSONA FACTORY` (scan + generate + sync), `STOP FACTORY` (suspend for the boot).

(End of file — Persona Registry v1.0 + Factory v1.0)
