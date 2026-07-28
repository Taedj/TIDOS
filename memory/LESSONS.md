# Lessons Learned

## TIDOS v3.0 Multi-Project Ecosystem

- **Issue**: Hardcoded repository URL scattered across documentation
- **Root Cause**: No centralized configuration file
- **Resolution**: Added `config/framework.md` as single source of truth for repository metadata
- **Lesson**: Centralize configuration early to avoid update cascading across dozens of files
- **Applied**: TIDOS v3.0 config-driven architecture

## TIDOS v2.0 Centralized Refactoring

- **Issue**: TIDOS previously lived inside each project as `.tidos/`, leading to fragmentation
- **Root Cause**: No centralized version control or update mechanism
- **Resolution**: Refactored to standalone Git repository with consumption protocols
- **Lesson**: Platform frameworks must be versioned and centrally maintained to prevent drift
- **Applied**: TIDOS v2.0 centralized architecture with Git submodule/symlink/injection support

## General

| Date | Lesson | Context | Validation |
|------|--------|---------|------------|
| - | - | - | - |
