# Fastie

Fastie is a convention-driven backend starter built on **FastAPI**. Its
default project is ordinary FastAPI code: `APIRouter`, `Depends(get_db)`,
SQLAlchemy, Pydantic, and explicit migrations. The older controller/service/
repository and decorator DI APIs remain available for existing projects, but
they are optional compatibility features.

Vietnamese: [Tiếng Việt](README.vi.md)

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What you get

- FastAPI-first generated application with request-scoped SQLAlchemy sessions.
- OAuth2 password flow with bearer tokens, PyJWT claim validation, and Argon2
  password hashing through `pwdlib` (with legacy bcrypt verification and
  automatic upgrade after a successful login).
- SQLAlchemy/Alembic migrations with a single-head check and schema drift check.
- `fastie make resource` for a model, Pydantic schemas, and a CRUD router.
- Soft-delete support in the optional base repository.
- Redis-backed rate limiting when `REDIS_URL` is configured.

## Quick start

```bash
pip install fastie-py
fastie new my_project --database sqlite
cd my_project
pip install -r requirements.txt
fastie db migrate
fastie dev
```

The generated API is available under `/api/v1`. The standard OAuth2 token
endpoint is `POST /api/v1/auth/token` with form fields `username` and
`password`; `/api/v1/auth/login` is also kept as a JSON-friendly convenience.

## Generate a resource

```bash
fastie make resource Product --fields "name:str,price:decimal,is_active:bool"
fastie make migration add_products_table --auto
fastie db check
fastie db migrate
```

The resource generator creates a SQLAlchemy model, create/update/response
schemas, a plain FastAPI CRUD router, and registers that router in the new
project. Review generated code before applying the migration.

## CLI reference

### Project and server

- `fastie new <name>`: Create a project.
- `fastie dev`: Run Uvicorn with auto-reload on localhost.
- `fastie serve`: Run Uvicorn without auto-reload by default.
- `fastie routes`: List application routes.

### Code generation

- `fastie make resource <Name>`: Generate the default CRUD path.
- `fastie make model <Name>`: Generate only a model.
- `fastie make migration <Name>`: Create a reviewed Alembic revision.
- `fastie make controller/service/repository <Name>`: Legacy APIs for projects
  that deliberately use the compatibility architecture.

### Database

- `fastie db migrate`: Apply migrations.
- `fastie db check`: Ensure one migration head and no schema drift.
- `fastie db status`: Show migration state and history.
- `fastie db rollback`: Roll back in development; production requires `--force`.
- `fastie db reset`: Rebuild a non-production database.

Production should run `fastie db check` and `fastie db migrate` as explicit
deployment steps before the application rollout. The application never runs
migrations during startup.

## Authentication configuration

Set these values through the environment or a secret manager in production:

```dotenv
JWT_SECRET=<random secret with at least 32 characters>
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ALLOWED_ORIGINS=https://api.example.com
REDIS_URL=redis://localhost:6379/0
```

JWT payloads are signed, not encrypted. Do not put passwords or sensitive
personal data in them. For a larger deployment, the JWT wrapper can be
replaced with an external OIDC provider and JWKS validation without changing
the route dependency shape.

## Compatibility architecture

Fastie still ships `BaseController`, `Service`, `Repository`, `DbContext`, and
decorator-based DI so existing applications can migrate incrementally. New
features should start with a router and dependencies; introduce a service or
repository only when the business logic actually benefits from one.

## License

MIT License. See [LICENSE](LICENSE).
