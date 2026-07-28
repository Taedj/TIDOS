# TIDOS Starter Template

Use this template to create a new project with TIDOS pre-configured.

## Quick Start

```bash
# Method 1: Manual setup
mkdir my-project
cd my-project
git init
git submodule add https://github.com/tidjani/TIDOS.git .tidos

# Method 2: Using install script
mkdir my-project
cd my-project
bash .tidos/scripts/install.sh
```

## Recommended Project Structure

```
my-project/
├── .tidos/                    # TIDOS submodule
├── src/                       # Application source
│   ├── domain/                # Domain layer (entities, use cases)
│   ├── data/                  # Data layer (repositories, DTOs)
│   └── presentation/          # Presentation layer (UI)
├── test/                      # Tests
├── docs/                      # Project documentation
│   ├── decisions/             # ADRs
│   └── lessons/               # Lessons learned
├── README.md
├── CHANGELOG.md
└── .gitignore
```

## Startup Sequence

After creating the project, the AI agent should:

1. Read `.tidos/TIDSTART.md`
2. Load `core/`, `engines/`, `personas/`, `rules/`
3. Mount matching plugins from `.tidos/plugins/`
4. Analyze project structure
5. Generate startup report
6. Await user instructions

## .gitignore

```
# TIDOS submodule is tracked, but its .git is not
.tidos/.git
```

## Commit Your Project

```bash
git add .
git commit -m "initial: project scaffold with TIDOS v3.0"
```
