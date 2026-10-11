# TIDOS Universal Model Equalizer Checklist (v4.0)

> **Purpose**: Cognitive scaffolding framework that forces System-2 reasoning, empirical ground-truth verification, and mechanical validation onto any underlying LLM. Designed specifically to eliminate hallucinations, context drift, premature conclusions, and tool failures when running on small (7B/8B), quantized, or lightweight models.

---

## 1. The 6-Stage System-2 Cognitive Railway

Every task executed by an AI agent under TIDOS must strictly pass each stage in sequential order. A model is **forbidden** from mutating workspace files until Stages 1, 2, and 3 are satisfied and recorded.

```text
[Stage 1: INGEST]  ──►  [Stage 2: GROUND]  ──►  [Stage 3: PLAN & BOUND]
                                                           │
[Stage 6: SIGN-OFF] ◄── [Stage 5: VERIFY]  ◄──  [Stage 4: ATOMIC EDIT]
```

---

### Stage 1: Ingestion & Intent Parse Gate
*Prevent rushing into premature execution without understanding constraints.*

- [ ] **Request Deconstruction**: User prompt dissected into:
  1. *Core Objective* (single declarative sentence).
  2. *Explicit Constraints* (tools, frameworks, versions, style rules).
  3. *Implicit Edge Cases* (unhandled errors, nullability, concurrency, offline state).
- [ ] **Zero-Fluff Invariant**: No conversational filler (`"Sure!", "I'd be happy to help"`). Output starts directly with structured analysis.
- [ ] **Ambiguity Check**: If critical specifications are missing, halt and ask for clarification rather than hallucinating assumptions.

---

### Stage 2: Empirical Grounding Gate (Zero-Assumption Rule)
*Eliminate hallucinated file paths, imaginary methods, and outdated library APIs.*

- [ ] **Empirical File Inspection**: Mandatory reading of relevant source files via `view_file` or `grep_search` before designing any solution.
- [ ] **Fact Citation**: Current behavior grounded by quoting exact file paths and line ranges (`file:///path/to/file#L10-L30`).
- [ ] **Dependency & Version Verification**: Read project manifests (`package.json`, `pubspec.yaml`, `requirements.txt`, `build.gradle`, etc.) to confirm exact installed library versions.
- [ ] **No Memory Guessing**: Never rely on pre-trained internal weights for third-party API signatures — verify active code or live documentation first.

---

### Stage 3: Atomic Planning & Negative Boundary Definition
*Prevent weak models from wandering off-topic or attempting monolithic rewrites.*

- [ ] **Atomic Step Decomposition**: Task broken down into micro-steps affecting < 30 lines each.
- [ ] **Explicit Negative Boundaries (NEVER DO)**: Explicitly declare what the implementation must **NOT** touch:
  - *Must not alter unrelated functions or APIs.*
  - *Must not add unnecessary dependencies.*
  - *Must not bypass architectural layers (e.g. Presentation calling Data directly).*
- [ ] **Hypothesis & Risk Table**:
  | Step | Target File | Intended Mutation | Potential Side Effect | Verification Method |
  | :--- | :--- | :--- | :--- | :--- |
  | 1 | `path/to/file` | Brief change description | Risk to other callers | Unit test / Compiler |

---

### Stage 4: Atomic Execution Gate
*Ensure surgical, non-destructive file edits.*

- [ ] **Surgical Targeting**: Use targeted diff/chunk replacements (`replace_file_content`) over whole-file rewrites.
- [ ] **Comment & Docstring Integrity**: Preserve existing comments, docstrings, and type annotations unrelated to the change.
- [ ] **Clean Architecture Compliance**: Changes respect project layering (`Domain` remains pure; `Presentation` and `Data` remain decoupled).
- [ ] **Style & Convention Match**: Variable naming, indentation, and formatting match surrounding code exactly.

---

### Stage 5: Mechanical Verification Gate (Deterministic Truth)
*Never trust a model's self-assessment — let the machine verify.*

- [ ] **Tool-Driven Execution**: Run actual terminal commands (compilers, linters, static analyzers, test runners).
- [ ] **Empirical Exit Code Audit**: Verify exit code is strictly `0`. Never declare success without seeing terminal pass output.
- [ ] **Micro-Correction on Failure**: If a compiler or test fails:
  1. Capture raw terminal output.
  2. Isolate the exact failing line and error code.
  3. Apply targeted single-line fix.
  4. Re-run verification command until 100% pass.
  5. Never guess or try random code rewrites.

---

### Stage 6: Quality Sign-Off & Knowledge Capture
*Prevent regressions and preserve institutional intelligence.*

- [ ] **Regression Check**: Verify existing tests in the suite continue to pass.
- [ ] **Clean Git Diff**: Run `git status` / `git diff` to confirm zero unintended files, scratch scripts, or debug logs remain.
- [ ] **Knowledge Distillation**:
  - Mistake made during execution? -> Append post-mortem to `memory/LESSONS.md`.
  - Reusable pattern discovered? -> Promote to `memory/PATTERNS.md` (2+ reuse rule).

---

## 2. Weak-Model Anti-Drift Rules (Hard Invariants)

When running on local/small models (Llama 3 8B, Mistral, quantized models, basic flash models), the agent must adhere to these 4 absolute rules:

1. **Rule of Single Focus**: Only perform ONE file edit per response turn. Never attempt multi-file batch edits in a single turn without intermediate verification.
2. **Rule of Verbatim Citation**: When stating an existing function behavior, quote the exact lines from `view_file`. Paraphrasing leads to hallucinated state.
3. **Rule of Negative Restraint**: Every generated prompt or code block must be preceded by an explicit negative constraint: *"Do not rewrite the entire file; modify only lines X to Y"*.
4. **Rule of Terminal Authority**: The model's belief that code "looks correct" has zero evidentiary weight. Only compiler/test terminal output confirms correctness.
