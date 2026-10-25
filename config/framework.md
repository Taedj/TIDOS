# TIDOS Framework Configuration

This file is the single source of truth for TIDOS repository metadata. All documentation references should use these values instead of hardcoding URLs.

## Repository

```yaml
repository:
  owner: Taedj
  name: TIDOS
  url: https://github.com/Taedj/TIDOS
  default_branch: main
```

## Version

```yaml
version:
  current: 5.2.0
  codename: Arise
  release_date: 2026-10-25
```

## Persona Factory (self-learning persona generation)
```yaml
persona_factory:
  enabled: true
  os_freeze_exception: approved  # user-granted 2026-09-13: NEW personas in personas/ only
  new_files_only: true           # never edit/delete existing personas
  triggers:
    stack_gap: true              # uncovered stack seen across >= 2 sessions
    domain_recurrence: true      # domain vocab recurs across >= 2 user requests, no active coverage
  depth_threshold: 2             # sessions/sources needed before generation
  one_run_per_boot: true
  auto_sync: true                # factory_sync commits persona+registry+evolution on a review branch + opens a PR (never pushes main)
  auto_sync_force: false         # NEVER force-push
```

## GPTID Browser Relay (local ChatGPT Free bridge — no API, no key)

```yaml
gptid:
  enabled: false               # optional channel; TIDOS works normally when off/unreachable
  browser: auto               # auto (Playwright, dedicated profile, default) | manual (human bridge fallback)
  relay_host: 127.0.0.1        # local-only; non-localhost refused unless GPTID_ALLOW_REMOTE=1
  relay_port: 8765
  chatgpt_url: https://chatgpt.com/
  timeout_seconds: 30
  response_timeout_seconds: 180
  dedicated_conversation: true # prefer one GPTID conversation; reset via TIDOS GPTID reset
  auto:
    browser: chromium            # chromium = Playwright-bundled build (default) | firefox (installed) | firefox-nightly
    headless: true             # false (--headed) for the first manual login window
    profile_dir: ~/.tidos/gptid-profile
    auto_fallback_to_manual: false  # AUTO failure never silently switches modes
  limits:
    max_context_chars: 6000
    max_files: 8
    max_response_chars: 12000
    max_history: 5
    overflow_policy: truncate-and-label
```

## Usage

Reference the URL in documentation as:

```
{{ config.repository.url }}
```

This allows a single update point if the repository moves.
