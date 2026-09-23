# Fastie

**Fastie** is a modern web framework built on top of **FastAPI**, inspired by the design philosophy of **Laravel Artisan**. It provides a structured project boilerplate, a robust Dependency Injection system, and a professional CLI to accelerate your production-ready application development.

Vietnamese: [Tiếng Việt](README.vi.md)

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Clean Architecture**: Separation of concerns using Repository & Service layers.
- **Dependency Injection**: Automatic dependency management with decorators (`@inject`, `@controller`).
- **Fastie CLI**: Powerful command-line tools for generating boilerplate code and managing migrations.
- **Soft Delete**: Built-in soft-delete support in the base repository layer.
- **Modern UI**: Professional terminal interface with gradient banners and styled output.

## Installation

Install via pip:

```bash
pip install fastie-py
```

Initialize a new project:

```bash
fastie new my_project
cd my_project
```

## CLI Reference

### Project & Server
- `fastie new <name>`: Create a new project.
- `fastie serve`: Start the development server (auto-reload).
- `fastie routes`: List all registered routes.

### Code Generation (make)
- `fastie make controller <Name>`: Generate a new Controller.
- `fastie make service <Name>`: Generate a new Service.
- `fastie make repository <Name>`: Generate a new Repository.
- `fastie make model <Name>`: Generate a new SQLAlchemy Model.
- `fastie make migration <Name>`: Create a new migration file.

### Database Management (db)
- `fastie db migrate`: Run pending migrations.
- `fastie db rollback`: Rollback the last migration in development; production requires `--force`.
- `fastie db reset`: Rebuild the database in development only.
- `fastie db status`: Check current migration status.
- `fastie db check`: Validate that the migration graph has one head and the database matches the models.

### Migration workflow

Create and review every migration before applying it:

```bash
fastie make migration add_profile_fields --auto
fastie db check
fastie db migrate
```

Fastie enforces one migration head. If parallel branches create multiple heads, resolve them explicitly
before applying or creating another migration:

```bash
alembic merge -m "merge migration heads" <head-one> <head-two>
fastie db check
```

Production deployments should run `fastie db migrate` as a separate deploy step before rolling out the
application. The application does not run migrations during startup, and destructive rollback/reset
operations are not part of the production workflow.

For production, configure `JWT_SECRET` with a random value of at least 32 characters, set
`CORS_ALLOWED_ORIGINS` explicitly, and provide `REDIS_URL` for shared rate limiting across workers.

## Usage Examples

### Dependency Injection

```python
@controller
@inject
class UserController(BaseController):
    def __init__(self, user_service: IUserService):
        self.user_service = user_service
        
    def define_routes(self):
        self.router.get("/")(self.index)

    async def index(self):
        return self.success(content=self.user_service.get_all())
```

### Soft Delete

```python
# Soft delete
self.repository.delete(id)

# Restore
self.repository.restore(id)

# Query including deleted items
items = self.repository.get_all(with_trash=True)
```

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more details.

---
Developed with ❤️ by **Phuong Nha Nguyen** in collaboration with **Antigravity (Google DeepMind)**.
