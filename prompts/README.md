# TIDOS System Prompts (`prompts/`)

The `prompts/` directory contains standardized system prompt scaffolds used for AI agent initialization and context injection across different coding assistants.

## Protection Rule

```
INVARIANT: All files in prompts/ are PROTECTED system files and read-only.
```

## Contents

System prompt templates for each supported AI coding agent, providing consistent TIDOS context regardless of the tool being used.

## CHORA Advisor Prompt Pack (`prompts/chora/`)

- [advisor_base.md](file:///d:/work/Dev/TIDOS/prompts/chora/advisor_base.md): Locked per-advisor scaffold (role, falsification mandate, scope, constraints, evidence pointers, risks, decision, response schema, secrets ban).
- [perspectives.md](file:///d:/work/Dev/TIDOS/prompts/chora/perspectives.md): Seven complementary lenses (Architecture, Security, Performance, Algorithm/Math, Quantitative/Risk, QA/Validation, Adversarial) with trigger-reason mapping.
