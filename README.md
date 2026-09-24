# Fastie

Fastie is a convention-driven backend starter built on **FastAPI**. Generated
projects use ordinary FastAPI code: `APIRouter`, `Depends(get_db)`, SQLAlchemy,
Pydantic, and explicit migrations.

> Fastie is not published to PyPI yet. The commands below assume a local source
> checkout and an editable install.

Vietnamese: [Tiếng Việt](README.vi.md)

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What you get

- FastAPI-first generated application with request-scoped SQLAlchemy sessions.
- OAuth2 password flow with bearer tokens, PyJWT claim validation, and Argon2
  password hashing through `pwdlib`.
- SQLAlchemy/Alembic migrations with a single-head check and schema drift check.
- `fastie make resource` for a model, Pydantic schemas, and a CRUD router.
- Soft-delete fields on the shared model base.
- Redis-backed rate limiting when `REDIS_URL` is configured.

## Quick start

```bash
git clone https://github.com/nphuonha2101/fastie-py.git
cd fastie-py
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
fastie new my_project --database sqlite
cd my_project
pip install -r requirements.txt
fastie db migrate
fastie dev
```

The generated API is available under `/api/v1`. The OAuth2 token endpoint is
`POST /api/v1/auth/token` with form fields `username` and `password`. It
returns a short-lived access token and a rotating refresh token. Refresh token
reuse invalidates the whole token family.

For a ready-to-run local container stack with PostgreSQL, Redis, a non-root
application container, and a one-shot migration service, point Docker setup at
the local Fastie checkout while the package is unpublished:

```bash
fastie setup docker --database postgres --local-source ..
cp .env.docker.example .env.docker
# Edit .env.docker before starting the stack.
docker compose --env-file .env.docker up --build
```

Use `--database mysql` for MySQL. The generated Compose stack runs migrations
in a separate service before the API container starts; review the generated
environment values and use a secret manager for real production credentials.
The `--local-source` option builds a local wheel into `.fastie-local/`.

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
- `fastie setup docker`: Generate a Dockerfile, Compose stack, and Docker environment template. Use `--local-source <path>` to test an unpublished checkout.
- `fastie dev`: Run Uvicorn with auto-reload on localhost.
- `fastie serve`: Run Uvicorn without auto-reload by default.
- `fastie routes`: List application routes.
- `fastie test`: Run the generated test suite. Install `requirements-test.txt` first.

### Code generation

- `fastie make resource <Name>`: Generate the default CRUD path.
- `fastie make model <Name>`: Generate only a model.
- `fastie make migration <Name>`: Create a reviewed Alembic revision.

### Database

- `fastie db migrate`: Apply migrations.
- `fastie db check`: Ensure one migration head and no schema drift.
- `fastie db status`: Show migration state and history.
- `fastie db rollback`: Roll back in development; production requires `--force`.
- `fastie db reset`: Rebuild a non-production database.

Production should run `fastie db check` and `fastie db migrate` as explicit
deployment steps before the application rollout. The application never runs
migrations during startup.

## Testing

Generated projects include a SQLite test fixture, FastAPI `TestClient`, and
dependency overrides. Install the test dependencies and run the suite from the
project root:

```bash
pip install -r requirements-test.txt
fastie test
```

Use `fastie test --coverage` for a coverage report. Pass additional pytest
arguments after the command, for example `fastie test tests/api/test_auth.py`.

For reproducible Fastie development and CI installs, use `uv sync --locked`.
The committed `uv.lock` keeps the framework dependency graph stable.

## Authentication configuration

Set these values through the environment or a secret manager in production:

```dotenv
JWT_SECRET=<random secret with at least 32 characters>
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ALLOWED_ORIGINS=https://api.example.com
ALLOWED_HOSTS=api.example.com
REDIS_URL=redis://localhost:6379/0
TRUSTED_PROXY_IPS=10.0.0.0/8
```

JWT payloads are signed, not encrypted. Do not put passwords or sensitive
personal data in them. For a larger deployment, the JWT wrapper can be
replaced with an external OIDC provider and JWKS validation without changing
the route dependency shape.

For production, run multiple workers behind a trusted reverse proxy, set
`--proxy-headers` with an explicit `--forwarded-allow-ips` value, and run
`fastie db check` before `fastie db migrate`. Do not use SQLite or wildcard
CORS/host settings in production.

## License

MIT License. See [LICENSE](LICENSE).
