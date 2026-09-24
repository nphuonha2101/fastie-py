# Fastie Project

This project was generated with Fastie and uses ordinary FastAPI, SQLAlchemy,
Pydantic, and Alembic code.

## Start locally

```bash
pip install -r requirements.txt
fastie db migrate
fastie dev
```

The API is served at `http://127.0.0.1:8000`.

## API documentation

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Project layout

```text
app/
  main.py              # FastAPI application and health endpoints
  routes/
    api.py             # /api namespace composition
    v1.py              # Stable /api/v1 router
    vN.py              # Created automatically for additional API versions
    auth.py            # Authentication and refresh-token routes
    users.py           # User routes
    resources/         # Versioned resource routers (v1/, v2/, v3/, ...)
  models/              # SQLAlchemy models
  schemas/             # Pydantic request and response schemas
alembic/               # Database migrations
tests/                 # Generated API tests
resources/             # Static resources
```

## Database workflow

```bash
fastie db check
fastie db migrate
fastie make resource Product --fields "name:str,price:decimal"
# Reuse the existing Product model for another contract.
fastie make resource Product --version v3 --reuse-model --fields "name:str,price:decimal"
# Or generate a separate persistence model/table explicitly.
fastie make resource Product --version v2 --model ProductV2 --fields "name:str,price:decimal"
fastie make migration add_products_table --auto
fastie db check
fastie db migrate
```

Review generated code and migrations before applying them in production.
Resource versions accept any positive numeric form (`v1`, `v2`, `v3`, ...).
Each version gets its own route/schema contract while the SQLAlchemy model and
migration history remain shared by default. Pass `--model ModelName` to opt into
a separate ORM model/table and manage its migration independently.
