# TIDSTART — TIDOS v3.0 Central Session Entry Protocol

Welcome to **TIDOS (Tidjani Development Operating System)** v3.0 Centralized AI Operating System Platform.

---

## 1. Central Startup & Synchronization Workflow

When beginning work on any software project, the AI Agent must execute the following 9-step synchronization sequence before responding to user directives:

```mermaid
graph TD
    S1["1. Load Central TIDOS Repository"] --> S2["2. Read TIDSTART.md Protocol"]
    S2 --> S3["3. Load Core, Identity & Bootstrap"]
    S3 --> S4["4. Load Engines, Rules, Personas & Plugins"]
    S4 --> S5["5. Analyze Current Target Project"]
    S5 --> S6["6. Recover Project Context & ADRs"]
    S6 --> S7["7. Recover User Methodology & Preferences"]
    S7 --> S8["8. Generate TIDOS Startup Report"]
    S8 --> S9["9. Await User Prompt Instructions"]
```

### Step 0: Update Gate (mandatory, runs before the checklist)

Before step 1, force-sync TIDOS with GitHub: run `scripts/update.ps1` (Windows) or `scripts/update.sh` (Linux/macOS) against the TIDOS checkout (`.tidos/`, multi-root folder, or central repo). The gate fetch-compares `HEAD` against the remote and `reset --hard` to it when behind, then boot proceeds on the synced version. Safety rules: ABORT (never wipe) on uncommitted `memory/`/`evolution/` changes or unpushed commits — commit/push first, then re-run; NEVER block boot when GitHub is unreachable or no `.git` exists — warn and continue on the local version. Record the before→after version in the Startup Report.

### Step 0.5: Authentication Gate (mandatory, Firebase-enabled instances)

TIDOS requires the user to be authenticated before any work proceeds (project `tidos-framework`, see `docs/firebase_auth.md`).

1. Run `scripts/auth_verify.ps1 -Session` (Windows) or `scripts/auth_verify.sh -Session` (Linux/macOS).
   - **Exit 0** → session validated (remember-me). Announce `Authenticated: <email>` in the Startup Report and proceed.
   - **Exit 1** → user is NOT authenticated. **BLOCK BOOT** and ask the user to sign in: `Login` (email + password) or `Register` (create account; verification email sent). Run the corresponding helper with the user's credentials, then re-run `-Session`. Loop until exit 0 or the user reports offline/unconfigured.
   - **Exit 2 or network error** (FIREBASE_API_KEY missing / Firebase unreachable) → warn "Authentication unavailable (configured check failed)" and CONTINUE on the local version — auth never hard-blocks boot when the backend is unreachable or unconfigured.
2. The user may end the session at any time with `TIDOS AUTH logout` (clears the saved refresh token in `~/.tidos`, outside the repo).
3. Record auth status in the Startup Report: `Authenticated: <email>` or `Authentication: unauthenticated/offline`.

### Mandatory Subsystem Checklist
- [ ] **1. OS Core**: Read [core/kernel.md](file:///d:/work/Dev/TIDOS/core/kernel.md) (Protected OS Freeze invariant).
- [ ] **2. Identity**: Read [core/identity.md](file:///d:/work/Dev/TIDOS/core/identity.md) (Senior Principal Engineer stance).
- [ ] **3. Bootstrap**: Read [core/bootstrap.md](file:///d:/work/Dev/TIDOS/core/bootstrap.md) (Non-destructive inspection).
- [ ] **4. Operating Engines**: Mount [engines/workflow_engine.md](file:///d:/work/Dev/TIDOS/engines/workflow_engine.md), [engines/quality_engine.md](file:///d:/work/Dev/TIDOS/engines/quality_engine.md), [engines/memory_engine.md](file:///d:/work/Dev/TIDOS/engines/memory_engine.md), [engines/learning_engine.md](file:///d:/work/Dev/TIDOS/engines/learning_engine.md), [engines/research_engine.md](file:///d:/work/Dev/TIDOS/engines/research_engine.md), and [engines/plugin_engine.md](file:///d:/work/Dev/TIDOS/engines/plugin_engine.md).
- [ ] **5. Architecture & Security Rules**: Read [rules/architecture_rules.md](file:///d:/work/Dev/TIDOS/rules/architecture_rules.md), [rules/security_rules.md](file:///d:/work/Dev/TIDOS/rules/security_rules.md), and [rules/coding_standards.md](file:///d:/work/Dev/TIDOS/rules/coding_standards.md).
- [ ] **6. Personas**: Load Virtual AI Company roles from [personas/roles.md](file:///d:/work/Dev/TIDOS/personas/roles.md).
- [ ] **7. Technology Plugins**: Load matching plugins from [plugins/](file:///d:/work/Dev/TIDOS/plugins).
- [ ] **8. Memory & User Profile**: Hydrate [memory/USER_PROFILE.md](file:///d:/work/Dev/TIDOS/memory/USER_PROFILE.md), [memory/PREFERENCES.md](file:///d:/work/Dev/TIDOS/memory/PREFERENCES.md), [memory/PATTERNS.md](file:///d:/work/Dev/TIDOS/memory/PATTERNS.md), and [memory/LESSONS.md](file:///d:/work/Dev/TIDOS/memory/LESSONS.md).
- [ ] **9. Target Project Analysis**: Perform read-only scan of target project root, recover context, and output Startup Report.

---

## 2. Protected System Directories Invariant

```
INVARIANT: System directories (core/, engines/, personas/, rules/, commands/, 
           checklists/, templates/, plugins/, prompts/) are PROTECTED and read-only.
           The AI must NEVER modify these system files automatically.
           Evolution proposals are written strictly to evolution/SUGGESTIONS.md.
           See config/framework.md for the canonical repository URL.
```

---

## 3. Standard Startup Report Format

```markdown
# TIDOS v3.0 Startup Report

- **Target Workspace**: `[Path to target project]`
- **TIDOS Connection Mode**: `[Submodule / Multi-Root / System Prompt / Local]`
- **Detected Stack**: `[e.g., Flutter / Supabase / Node.js]`
- **Active Plugins Mounted**: `[flutter.md, supabase.md, github.md]`
- **User Profile Status**: Synchronized (`USER_PROFILE.md` & `PREFERENCES.md` active)
- **Project Context Status**: Hydro-recovered (`PROJECT_HISTORY.md` active)
- **System Readiness**: Protected Operating System Mounted & Synchronized.

## Next Steps
System is fully synchronized and ready for prompt execution.
```
