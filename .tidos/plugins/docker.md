# TIDOS Plugin: Docker & Containerization

## 1. Detection Rules
- **Signature Files**: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.dockerignore`

## 2. Initialization Steps
- Verify Docker daemon availability (`docker info`).
- Validate `Dockerfile` syntax (`dockerfilelint` / `hadolint`).

## 3. Documentation to Generate
- `CONTAINER_ARCHITECTURE.md`: Document multi-stage build stages, base images, and container networking.

## 4. Best Practices
- Use multi-stage builds to minimize final production container image size.
- Run container processes as non-root users (`USER node` / `USER app`).

## 5. Coding Standards
- Pin base images to specific tags or digests (e.g., `node:20-alpine`, `python:3.11-slim`).
- Include explicit `.dockerignore` to exclude `node_modules`, `.git`, `.env`, and local build artifacts.

## 6. Review & Quality Rules
- Validate zero hardcoded credentials inside `Dockerfile` or `docker-compose.yml`.
- Verify container health check instructions (`HEALTHCHECK`).

## 7. Research Topics
- Docker Rootless mode, Podman compatibility, Distroless base images.
