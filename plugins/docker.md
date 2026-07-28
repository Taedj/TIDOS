# TIDOS Plugin: Docker & Containerization (v3.0)

## 1. Detection Rules
- **Signature Files**: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.dockerignore`

## 2. Initialization Steps
- Verify Docker Engine and Docker Compose installation (`docker --version`, `docker compose version`).

## 3. Documentation to Generate
- `DOCKER_ARCHITECTURE.md`: Document multi-stage builds, image layering, and compose orchestration.

## 4. Best Practices
- Use multi-stage builds to minimize production image size.
- Pin base image versions with SHA digests for reproducible builds.

## 5. Coding Standards
- Require `.dockerignore` excluding `node_modules/`, `.git/`, `.env`, build artifacts.
- Run containers as non-root users (`USER appuser`).

## 6. Review & Quality Rules
- Validate zero `RUN` instructions installing dev dependencies in production stage.
- Verify health check endpoints configured in `docker-compose.yml`.

## 7. Research Topics
- Docker Build Cloud, Buildx Bake multi-platform builds, Distroless base images.
