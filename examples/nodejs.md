# TIDOS + Node.js Integration Example

## Project Type
Node.js backend microservices or API server.

## TIDOS Connection

```bash
cd nodejs_backend
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/nodejs.md` - Node.js specification
- `plugins/postgresql.md` or `plugins/sqlite.md` - Database
- `plugins/docker.md` - Containerization

## Architecture Enforced

- Layered architecture (routes -> controllers -> services -> repositories)
- Express.js or Fastify for HTTP server
- Middleware chain for auth, validation, error handling
- Environment-based configuration
- Jest or Vitest for testing

## Best Practices

- Input validation at controller layer
- Structured error responses
- Rate limiting and security headers
- Logging with structured levels
