# TIDOS Firebase Configuration

Single source of truth for the TIDOS Firebase Authentication backend. Reference these values instead of hardcoding them.

## Project

```yaml
firebase:
  project_id: tidos-framework
  project_number: 640232479990
  project_name: TIDOS Framework Auth
  console_url: https://console.firebase.google.com/project/tidos-framework
```

## Web App (SDK config — public by design)

```yaml
firebase.web:
  app_id: 1:640232479990:web:dd6117b3d8599ac295a0d7
  api_key: AIzaSyDzbyda_7ygLaWtqjLZtiHrqSd0b_CYBQk
  auth_domain: tidos-framework.firebaseapp.com
  storage_bucket: tidos-framework.firebasestorage.app
  messaging_sender_id: 640232479990
  project_number: 640232479990
```

> The web `apiKey`, `appId`, `authDomain`, etc. are **public** by design (embedded in client apps).
> Never commit secrets. Service-account keys, OAuth client secrets, or admin credentials MUST live in
> `.env` / a key vault only — see `docs/firebase_auth.md` §Security.

## Authenticated Methods (Framework Default)

```yaml
firebase.auth.methods:
  email_password:
    enabled: true
    verification: required
    password_reset: required
  google_sign_in:
    enabled: true
    web_redirect: firebaseui (per project)
    consent_screen: GCP OAuth (per project)
```

## Usage

Reference the config values as `{{ config.firebase.project_id }}` and `{{ config.firebase.web.api_key }}`
in docs and scripts — single update point if the project or app is recreated.