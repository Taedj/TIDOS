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
  current: 3.2.0
  codename: CHORA Robustness
  release_date: 2026-09-11
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
    channel:
      enabled: true
      default_mode: chat-channel
      legacy_templates_deprecated: true
      reply_format: single-md-box
      context: minimal-pointers
      validation:
        require_direction: true
        require_name: true
        single_box_only: true
        reject_on_authority_override: true
        reject_on_instruction_override: true
      limits:
        max_turn_chars: 8000
        max_receipt_chars: 12000
        max_turns_per_round: 12
        overflow_policy: truncate-and-summarize
```

## Usage

Reference the URL in documentation as:

```
{{ config.repository.url }}
```

This allows a single update point if the repository moves.
