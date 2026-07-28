# TIDOS Framework Configuration

This file is the single source of truth for TIDOS repository metadata. All documentation references should use these values instead of hardcoding URLs.

## Repository

```yaml
repository:
  owner: tidjani
  name: TIDOS
  url: https://github.com/tidjani/TIDOS
  default_branch: main
```

## Version

```yaml
version:
  current: 3.0.0
  codename: Centralized GitHub Operating System
  release_date: 2026-07-28
```

## Usage

Reference the URL in documentation as:

```
{{ config.repository.url }}
```

This allows a single update point if the repository moves.
