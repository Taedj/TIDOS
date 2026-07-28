# TIDOS Plugin: GitHub Actions & CI/CD Pipelines

## 1. Detection Rules
- **Signature Directory / Files**: `.github/workflows/`, `.github/pull_request_template.md`

## 2. Initialization Steps
- Verify workflow file YAML syntax.
- Check GitHub repository secrets configuration requirements.

## 3. Documentation to Generate
- `CICD_PIPELINE.md`: Document workflow triggers, matrix strategies, and deployment environments.

## 4. Best Practices
- Pin GitHub Action versions to explicit commit SHAs or major version tags (`actions/checkout@v4`).
- Use dependency caching (`actions/cache` / setup action built-in caching) to accelerate workflow runtimes.

## 5. Coding Standards
- Isolate secret credentials using GitHub Repository Secrets or OIDC environment roles.
- Configure job timeouts (`timeout-minutes: 15`) to prevent runaway build charges.

## 6. Review & Quality Rules
- Validate zero plain-text secret key assignments in workflow YAML files.
- Verify security scanning steps (`CodeQL`, `dependabot`).

## 7. Research Topics
- GitHub Actions Reusable Workflows, OIDC authentication for AWS/GCP, Custom self-hosted runners.
