# TIDOS Scripts (`scripts/`)

The `scripts/` directory contains helper scripts for TIDOS framework operations. These scripts automate common tasks such as initialization, synchronization, and verification.

## Planned Scripts

- `setup.sh` - One-command TIDOS repository setup
- `sync.sh` - Cross-project memory synchronization
- `doctor.sh` - System health check
- `update.ps1` - Update Gate Step 0 (Windows): fetch + memory-safe force-sync before boot (exit 0 ready / 1 blocked / 2 error)
- `update.sh` - Update Gate Step 0 (Linux/macOS): same behavior as `update.ps1`
- `auth_verify.ps1` - Firebase Auth helper (Windows): mandatory boot gate (`-Session` remember-me, blocks boot on exit 1), `-Login`/`-Register` (email/password, verification email), `-Verify` (foreign ID token), `-Logout`, `-Status`. Session persisted in `~/.tidos` (outside repo). Config in `config/firebase.md`; API key from `FIREBASE_API_KEY` env var or `.env`
- `auth_verify.sh` - Firebase Auth helper (Linux/macOS): same as `auth_verify.ps1` (requires `jq` + `curl`)
- `verify_chora_trigger.ps1` - CHORA Trigger Engine verification harness (NONE / RECOMMENDED / REQUIRED, escalation, manual override, decline, dedup, context change, persistence)
- `verify_chora_session.ps1` - CHORA Session structural validator (engine chain, authority hierarchy, prompt schema, templates, config, commands, dry-run chain)
- `gptid.ps1` - GPTID relay control (Windows): `start|stop|status|test|reset|ask|review|audit` over `browser_relay/gptid_cli.py` (localhost relay, no secrets)
- `gptid.sh` - GPTID relay control (Linux/macOS): same as `gptid.ps1`
- `verify_gptid.ps1` - GPTID structural + protocol validator (files, persona/engine/config/commands markers, selector fallbacks, secret-mirror checks, python unit tests)
