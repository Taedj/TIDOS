# TIDOS v3.0 Dependency Diagram

## System Architecture Overview

```
                       ┌─────────────────────────────┐
                       │        TIDSTART.md           │
                       │   (Session Entry Protocol)   │
                       └──────────────┬──────────────┘
                                      │
                                      ▼
              ┌─────────────────────────────────────────────────┐
              │                 KERNEL LAYER                    │
              │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
              │  │ kernel.md│  │identity.│  │ bootstrap.md │  │
              │  │          │  │   md     │  │              │  │
              │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
              └───────┼─────────────┼────────────────┼──────────┘
                      │             │                │
                      ▼             ▼                ▼
              ┌─────────────────────────────────────────────────┐
              │               ENGINES LAYER                     │
              │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
              │  │ workflow │  │ quality  │  │   memory     │  │
              │  │  engine  │  │  engine  │  │   engine     │  │
              │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
              │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
              │  │ learning │  │ research │  │   plugin     │  │
              │  │  engine  │  │  engine  │  │   engine     │  │
              │  └──────────┘  └──────────┘  └──────┬───────┘  │
              └──────────────────────────────────────┼──────────┘
                                                     │
                      ┌──────────────────────────────┼──────────────┐
                      │                              │              │
                      ▼                              ▼              ▼
              ┌──────────────┐              ┌────────────────┐ ┌──────────┐
              │    RULES     │              │    PLUGINS     │ │ PERSONAS │
              │  ┌────────┐  │              │  ┌──────────┐  │ │ ┌──────┐ │
              │  │Arch    │  │              │  │flutter   │  │ │ │Roles │ │
              │  │ Rules  │  │              │  │firebase  │  │ │ │ 30+  │ │
              │  ├────────┤  │              │  ├──────────┤  │ │ └──────┘ │
              │  │Security│  │              │  │supabase  │  │ └──────────┘
              │  │ Rules  │  │              │  │react     │  │
              │  ├────────┤  │              │  ├──────────┤  │
              │  │Coding  │  │              │  │...18 more│  │
              │  │Standards│ │              │  └──────────┘  │
              │  └────────┘  │              └────────────────┘
              └──────────────┘
                      │
                      ▼
              ┌─────────────────────────────────────────────────┐
              │            SUPPORTING LAYERS                    │
              │                                                │
              │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
              │  │ COMMANDS │  │CHECKLISTS│  │  TEMPLATES   │  │
              │  │  (1 file)│  │  (1 file)│  │  (13 files)  │  │
              │  └──────────┘  └──────────┘  └──────────────┘  │
              │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
              │  │  PROMPTS │  │   DOCS   │  │   EXAMPLES   │  │
              │  │ (scaffold)│  │(10+ files)│  │  (9 files)   │  │
              │  └──────────┘  └──────────┘  └──────────────┘  │
              └─────────────────────────────────────────────────┘
                                      │
                                      ▼
              ┌─────────────────────────────────────────────────┐
              │            DYNAMIC LAYERS                       │
              │                                                │
              │  ┌──────────────────┐  ┌────────────────────┐  │
              │  │     MEMORY/      │  │    EVOLUTION/      │  │
              │  │  User Profile    │  │  SUGGESTIONS.md    │  │
              │  │  Project History │  │  (Improvement      │  │
              │  │  Preferences     │  │   Proposals)       │  │
              │  │  Patterns        │  └────────────────────┘  │
              │  │  Lessons         │                           │
              │  │  Best Practices  │                           │
              │  └──────────────────┘                           │
              └─────────────────────────────────────────────────┘
```

## Data Flow

1. **Session Start** → `TIDSTART.md` triggers core loading
2. **Kernel** → Loads identity, executes bootstrap detection
3. **Engines** → Workflow, quality, memory, learning, research, plugin engines initialize
4. **Rules** → Architecture, security, and coding standards enforced
5. **Plugins** → Technology-specific plugins mounted based on stack detection
6. **Personas** → Virtual AI roles activated for task execution
7. **Memory** → User profile and project history hydrated
8. **Evolution** → Suggestions collected without modifying protected core

## Layer Relationships

```
Protected System (read-only)
  ├── core/     → defines HOW the OS operates
  ├── engines/    → defines WHAT the OS does
  ├── rules/      → defines CONSTRAINTS on execution
  ├── personas/   → defines WHO performs the work
  ├── commands/   → defines USER INTERACTION patterns
  ├── checklists/ → defines VERIFICATION criteria
  ├── templates/  → defines OUTPUT formats
  ├── plugins/    → defines TECHNOLOGY specializations
  └── prompts/    → defines AGENT INITIALIZATION

Dynamic System (evolving)
  ├── memory/     → accumulates USER INTELLIGENCE
  └── evolution/  → collects IMPROVEMENT proposals

Supporting System (read/write by maintainers)
  ├── docs/       → DOCUMENTATION
  ├── examples/   → INTEGRATION BLUEPRINTS
  ├── scripts/    → AUTOMATION helpers
  └── .github/    → CI/CD configuration
```
