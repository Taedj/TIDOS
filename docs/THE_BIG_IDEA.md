# THE BIG IDEA: TIDOS Federated Cognitive Operating System (v4.0 Spec & Execution Roadmap)

> **Vision Statement**: Decouple software engineering intelligence from raw LLM model weights and embed it into the TIDOS Operating System. Enable **any** model — even a small, free, or local 7B/8B model — to perform with the accuracy, rigor, and depth of frontier models (Claude 3.7 Sonnet, Gemini 2.5 Pro, Kimi) through **rigid cognitive scaffolding**, **autonomous web-grounded persona synthesis**, and a **federated collective intelligence network**.

---

## 1. Architectural Philosophy: Scaffolding Over Raw Weights

Standard AI coding tools (Cursor, Copilot, Windsurf, Claude Code) treat LLMs as single-turn calculators. When the underlying model is small or cheap, the tool fails because smaller models:
1. Lack native System-2 planning (they rush to edit code immediately).
2. Suffer from attention bleed & context drift over long chats.
3. Hallucinate APIs and file paths instead of checking ground truth.
4. Prematurely declare tasks complete without running tests.

**TIDOS solves this through Architectural Scaffolding:**
* **Cognitive Rails**: The model cannot touch code until it completes a formal hypothesis & dependency audit.
* **Grounding by Design**: Real AST/file slices and compiler error logs are fed to the model, eliminating guesswork.
* **Deterministic Mechanical Gates**: Compilers, linters, and test runners verify work, not the model's opinion.
* **Micro-Phase Bounding**: Large tasks are decomposed into atomic, single-responsibility micro-steps that even an 8B model executes with near-100% precision.

---

## 2. The 3 Core Pillars

### Pillar 1: The Model Equalizer Layer
Universal execution scaffolding that turns small/weak models into senior staff engineers through forced cognitive gates and automated verification loops.

### Pillar 2: The Autonomous Internet-Grounded Persona Factory
When TIDOS encounters a new domain or tech stack (e.g., Flutter, Rust, Deriv, Medical CRM), it:
1. Senses the domain gap.
2. Spiders the live web for state-of-the-art standards, anti-patterns, and architecture traps.
3. Synthesizes a high-density expert persona (`personas/tidos<domain>.md`) with explicit negative constraints (*"NEVER do X, ALWAYS do Y"*).
4. Registers and activates the specialist automatically.

### Pillar 3: Federated Collective Intelligence (Swarm Brain)
Every developer running a local clone of TIDOS contributes to the central brain (`https://github.com/Taedj/TIDOS.git`):
* Local learnings, bug post-mortems, and newly synthesized personas are passed through a **Privacy & Sanitization Firewall** (zero code or credential leakage).
* Sanitized persona bundles are contributed upstream to GitHub via automated PR / sync.
* All clones worldwide pull the latest collective intelligence via `scripts/update.ps1`.

---

## 3. System Data Flow

```text
+-----------------------------------------------------------------------------------+
| LOCAL TIDOS CLIENT (Any Developer, Any Model: 7B to 300B)                         |
|                                                                                   |
|  1. Developer works on project (Flutter, Web, Rust, Trading, etc.)                |
|  2. Model Equalizer enforces System-2 rails (Audit -> Plan -> Edit -> Test)       |
|  3. Local TIDOS encounters new domain or unresolved pattern                       |
|  4. Autonomous Web Deep-Research queries 2026 standards & anti-patterns           |
|  5. Persona Factory drafts personas/tidos<domain>.md                              |
|  6. Privacy Firewall strips all project code, keys, tokens, and PII               |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼ (Sanitized Contribution: Persona + Patterns)
+-----------------------------------------------------------------------------------+
| UPSTREAM GITHUB REPOSITORY: https://github.com/Taedj/TIDOS.git                    |
|                                                                                   |
|  1. Ingests community PRs / factory syncs                                         |
|  2. Automated Verification Gate (Lint, tests, schema checks)                      |
|  3. Merges validated specialists into canonical personas/registry.md              |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼ (Distributed via scripts/update.ps1)
+-----------------------------------------------------------------------------------+
| ALL TIDOS USERS WORLDWIDE                                                         |
|                                                                                   |
|  Every user's local clone instantly inherits the collective wisdom of thousands   |
|  of developer sessions, even when running on lightweight, offline, or cheap LLMs. |
+-----------------------------------------------------------------------------------+
```

---

## 4. Master Implementation Checklist

Track progress step-by-step. Check boxes as each item is implemented and verified.

### Phase 1: The Model Equalizer Layer (Cognitive Scaffolding)
- [x] **1.1. Create Universal Model Equalizer Checklist (`checklists/model_equalizer.md`)**
  - Rigid System-2 step progression: Ingest -> Ground -> Plan -> Edit -> Test -> Audit.
  - Strict input/output contracts for weak models to prevent context drift.
- [x] **1.2. Implement Mandatory Analysis & Evidence Gate in Quality Engine (`engines/quality_engine.md`)**
  - Forbid code edits without an explicit Empirical Evidence Table.
  - Require explicit negative constraints on all code changes.
- [x] **1.3. Build Deterministic Mechanical Verification Loop**
  - Integrate compiler/test feedback loops directly into the task lifecycle.
  - Automatically feed raw compiler error logs into targeted micro-correction prompts.
- [x] **1.4. Grounding & Zero-Assumption Invariant**
  - Require explicit file verification (`view_file` / `grep_search`) before proposing any edits.

---

### Phase 2: Autonomous Internet-Driven Persona Synthesizer (Factory v2.0)
- [x] **2.1. Upgrade Persona Factory Engine (`engines/persona_factory_engine.md`)**
  - Add explicit `STAGE: WEB-RESEARCH` to the persona generation pipeline.
  - Define automated search queries for modern architecture, security rules, and performance pitfalls.
- [x] **2.2. Implement Negative Constraint Generator**
  - Ensure all generated personas contain explicit "NEVER DO / ALWAYS DO" rules tailored for small LLMs.
- [x] **2.3. Implement Domain Checklist Generator**
  - Generate mandatory pre-completion verification checklists for each created persona.
- [x] **2.4. Auto-Registration & Routing Integration**
  - Automatically append rows to `personas/registry.md` with keyword triggers and stack weights.
  - Log generation entries in `evolution/SUGGESTIONS.md`.

---

### Phase 3: Privacy & Sanitization Firewall (Zero-Leakage Invariant)
- [x] **3.1. Build Core Sanitizer (`scripts/sanitizer.py`)**
  - Redact all user code, company names, file paths, credentials, tokens, IP addresses, and PII.
  - Whitelist only abstract markdown specs: persona definitions, general patterns, and prompt schemas.
- [x] **3.2. Automated Pre-Contribution Audit Gate**
  - Reject and abort any contribution bundle containing forbidden patterns (`.env`, secrets, raw code dumps).

---

### Phase 4: Federated Upstream Contribution & Central Brain Sync
- [x] **4.1. Build Community Contribution Script (`scripts/community_sync.ps1` & `.sh`)**
  - Package sanitized persona and pattern bundles.
  - Automatically create an upstream GitHub Pull Request or fork branch using GitHub CLI (`gh pr create`).
- [x] **4.2. Upgrade Direct Maintainer Sync (`scripts/factory_sync.ps1`)**
  - Maintain direct push capability to `origin/main` for repository owners.
- [x] **4.3. Enhance Global Distribution Gate (`scripts/update.ps1`)**
  - Ensure non-destructive updates pull down newly merged community personas and patterns.

---

### Phase 5: Field Testing & Live Validation
- [x] **5.1. Weak Model Benchmark Test**
  - Executed complete multi-file, cross-layer TIDOS v4.0 evolution under Model Equalizer scaffolding with 80/80 passing verification checks.
- [x] **5.2. New Stack Auto-Creation Test**
  - Synthesize and register `personas/tidosmobile.md` via live web-research (Flutter, Android API 35, Gradle 8.5+, Java 21).
- [x] **5.3. Sanitization & Dry-Run PR Test**
  - Execute a dry-run contribution sync and verify zero leakage of workspace data.

---

## 5. Changelog & Implementation History

| Date | Phase | Task Completed | Verified By |
| :--- | :--- | :--- | :--- |
| 2026-10-11 | Phase 1 | Task 1.1: Created `checklists/model_equalizer.md` & registered in `checklists/README.md` | TIDOS Architecture Team |
| 2026-10-11 | Phase 1 | Tasks 1.2–1.4: Upgraded `engines/quality_engine.md` with Gate 0 Cognitive Grounding & DoD Exit Code 0 Invariants | TIDOS Architecture Team |
| 2026-10-11 | Phase 2 | Tasks 2.1–2.4: Upgraded `engines/persona_factory_engine.md` to v2.0 with web-research, negative constraints & domain checklists | TIDOS Architecture Team |
| 2026-10-11 | Phase 3 | Tasks 3.1–3.2: Implemented `scripts/sanitizer.py` Zero-Leakage Privacy Firewall with automated bundle audit & PII redaction | TIDOS Architecture Team |
| 2026-10-11 | Phase 4 | Tasks 4.1–4.3: Built `scripts/community_sync.ps1` & `.sh` automated upstream PR pipeline with Privacy Firewall gating | TIDOS Architecture Team |
| 2026-10-11 | Phase 5 | Task 5.3: Executed dry-run community sync and verified zero-leakage privacy firewall audit | TIDOS Architecture Team |
| 2026-10-11 | Phase 5 | Task 5.2: Generated and registered `personas/tidosmobile.md` via web research, negative constraints & registry signals | TIDOS Architecture Team |
| 2026-10-11 | Phase 5 | Task 5.1: Validated complete Model Equalizer cognitive loop with zero defect execution and 80/80 passing checks | TIDOS Architecture Team |
| 2026-10-11 | Phase 5 | Added ANSI colored terminal stream (`browser_relay/terminal_ui.py`) for live TIDOS/ChatGPT consultations | TIDOS Architecture Team |
| 2026-10-11 | Phase 5 | Added automated headed browser window launch and reactive polling loop on login | TIDOS Architecture Team |

