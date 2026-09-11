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

## CHORA Trigger Engine

```yaml
chora:
  enabled: true
  automatic_trigger:
    enabled: true
  levels:
    recommended: true
    required: true
  repeated_failure_threshold: 3
  high_risk_domains:
    security: required
    trading_risk: required
    persistent_data: required
    database_migration: required
    financial_logic: required
  user_can_decline:
    recommended: true
    required: false
  deduplicate_sessions: true
  session:
    max_rounds: 2
    human_bridge: true
    no_external_apis: true
    persist_under: memory/
```

## Usage

Reference the URL in documentation as:

```
{{ config.repository.url }}
```

This allows a single update point if the repository moves.
