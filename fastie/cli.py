#!/usr/bin/env python3
import click
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import shutil
import secrets
from dotenv import load_dotenv
from fastie.core.utils.console import fastie_console

logger = logging.getLogger(__name__)
FASTIE_VERSION = '0.0.1a1'

# Import template engine
try:
    from fastie.template_engine import render_template
    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False
    fastie_console.warning("Fastie templates not available - falling back to inline templates")


class FastieGroup(click.Group):
    def format_help(self, ctx, formatter):
        fastie_console.print_banner()
        super().format_help(ctx, formatter)


def _alembic_command(*args):
    """Build an Alembic command using the current Python environment."""
    return [sys.executable, '-m', 'alembic', *args]


def _run_alembic(*args):
    """Run Alembic and convert process failures into useful CLI errors."""
    try:
        return subprocess.run(_alembic_command(*args), check=True, text=True)
    except FileNotFoundError as exc:
        raise click.ClickException(
            "Alembic is not installed in the active Python environment. "
            "Install the project dependencies first."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(
            f"Alembic command failed with exit code {exc.returncode}: "
            f"{' '.join(_alembic_command(*args))}"
        ) from exc


def _alembic_heads():
    """Return migration heads from the local Alembic script directory."""
    config_path = Path('alembic.ini')
    if not config_path.is_file():
        raise click.ClickException(
            "alembic.ini was not found. Run this command from the project root."
        )

    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config(str(config_path))
        return tuple(ScriptDirectory.from_config(config).get_heads())
    except Exception as exc:
        raise click.ClickException(f"Could not inspect the migration graph: {exc}") from exc


def _ensure_single_migration_head():
    """Reject ambiguous migration graphs before creating or applying revisions."""
    heads = _alembic_heads()
    if len(heads) > 1:
        formatted_heads = ', '.join(heads)
        raise click.ClickException(
            "Multiple Alembic heads detected: "
            f"{formatted_heads}. Resolve them with `alembic merge` before continuing."
        )
    return heads[0] if heads else None


def _environment_name():
    """Read the application environment without overwriting process variables."""
    load_dotenv()
    return os.getenv('ENVIRONMENT', os.getenv('APP_ENV', 'development')).strip().lower()


def _is_production():
    return _environment_name() in {'prod', 'production'}


@click.group(cls=FastieGroup, invoke_without_command=True)
@click.version_option(version=FASTIE_VERSION, prog_name='Fastie CLI')
def cli():
    """Fastie CLI for convention-driven FastAPI projects."""
    # Add current directory to path so it can find 'app'
    sys.path.append(os.getcwd())
    
    if len(sys.argv) == 1:
        fastie_console.print_banner()


@cli.group(name='setup')
def setup():
    """Generate deployment and development setup files."""
    pass


@setup.command(name='docker')
@click.option(
    '--database',
    type=click.Choice(['postgres', 'mysql'], case_sensitive=False),
    default='postgres',
    show_default=True,
    help='Database service to include in the Docker Compose stack.',
)
@click.option(
    '--workers',
    default=2,
    type=click.IntRange(min=1),
    show_default=True,
    help='Default number of Uvicorn workers for the application container.',
)
@click.option('--force', is_flag=True, help='Overwrite existing Docker setup files.')
def setup_docker(database, workers, force):
    """Generate a production-oriented Docker Compose stack."""
    project_root = Path.cwd()
    database = database.lower()
    files = _docker_setup_files(database, workers)

    if not (project_root / 'requirements.txt').is_file():
        raise click.ClickException(
            "requirements.txt was not found. Run this command from a generated project root."
        )

    existing = [str(path) for path in files if (project_root / path).exists()]
    if existing and not force:
        raise click.ClickException(
            "Refusing to overwrite existing Docker setup files: "
            + ', '.join(existing)
            + '. Pass --force to replace them.'
        )

    for relative_path, content in files.items():
        target = project_root / relative_path
        target.write_text(content, encoding='utf-8')

    fastie_console.success(
        f"Docker setup generated for {database} in [bold]{project_root}[/bold]"
    )
    fastie_console.step("cp .env.docker.example .env.docker")
    fastie_console.step("Edit .env.docker: secrets, domains, CORS, and proxy settings")
    fastie_console.step("docker compose --env-file .env.docker up --build")




@cli.command()
@click.argument('project_name')
@click.option(
    '--database',
    '-d',
    type=click.Choice(['sqlite', 'mysql', 'postgres'], case_sensitive=False),
    default='sqlite',
    show_default=True,
    help='Database type',
)
@click.option('--path', '-p', help='Target directory path (default: current directory)')
def new(project_name, database, path):
    """Create a new Fastie project"""
    fastie_console.info(f"Creating new Fastie project: [bold]{project_name}[/bold]")
    
    try:
        if path:
            target_dir = Path(path).resolve()
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                fastie_console.step(f"Created directory: {target_dir}")
            project_path = target_dir / project_name
        else:
            project_path = Path(project_name)
            
        if project_path.exists():
            fastie_console.error(f"Directory {project_path} already exists!")
            return
        
        # Copy from internal stubs instead of current directory
        stubs_path = Path(__file__).parent / "stubs"
        shutil.copytree(stubs_path, project_path, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.git', '.env', 'venv', 'node_modules', '.vscode'
        ))
        
        env_content = _generate_env_content(database)
        with open(project_path / '.env', 'w') as f:
            f.write(env_content)
        
        readme_path = project_path / 'README.md'
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace('Fastie', project_name.title())
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        fastie_console.success(f"Project [bold]{project_name}[/bold] created successfully!")
        fastie_console.info("Next steps:")
        fastie_console.step(f"cd {project_name}")
        fastie_console.step("python -m venv venv")
        fastie_console.step("pip install -r requirements.txt")
        fastie_console.step("fastie dev")
        
    except Exception as e:
        fastie_console.error(f"Error creating project: {str(e)}")




@cli.group(name='db')
def database():
    """Database related commands"""
    pass


@database.command(name='migrate')
def db_migrate():
    """Run database migrations"""
    fastie_console.info("Running database migrations...")
    _ensure_single_migration_head()
    _run_alembic('upgrade', 'head')
    fastie_console.success("Migrations completed successfully!")


@database.command(name='rollback')
@click.option('--steps', '-s', default=1, type=click.IntRange(min=1), help='Number of steps to rollback')
@click.option('--force', is_flag=True, help='Allow rollback in production (use forward-fix when possible)')
def db_rollback(steps, force):
    """Rollback database migrations"""
    if _is_production() and not force:
        raise click.ClickException(
            "Rollback is blocked in production by default. Use a forward-fix migration; "
            "pass --force only with an explicit operational decision."
        )

    _ensure_single_migration_head()
    fastie_console.info(f"Rolling back {steps} migration(s)...")
    for _ in range(steps):
        _run_alembic('downgrade', '-1')
    fastie_console.success("Rollback completed successfully!")


@database.command(name='reset')
@click.confirmation_option(prompt='Are you sure you want to reset the database?')
def db_reset():
    """Reset database (rollback all migrations)"""
    if _is_production():
        raise click.ClickException(
            "Database reset is permanently blocked when ENVIRONMENT is production."
        )

    _ensure_single_migration_head()
    fastie_console.info("Resetting database...")
    _run_alembic('downgrade', 'base')
    _run_alembic('upgrade', 'head')
    fastie_console.success("Database reset completed!")


@database.command(name='status')
def db_status():
    """Show migration status"""
    heads = _alembic_heads()
    if len(heads) > 1:
        fastie_console.warning(
            "Multiple migration heads detected: " + ', '.join(heads)
        )
    _run_alembic('current')
    _run_alembic('history')


@database.command(name='check')
def db_check():
    """Validate the migration graph and detect schema drift."""
    head = _ensure_single_migration_head()
    if head is None:
        raise click.ClickException("No Alembic migration revisions were found.")

    _run_alembic('current', '--check-heads')
    _run_alembic('check')
    fastie_console.success(f"Migration graph is valid and schema matches head {head}.")




@cli.group(name='make')
def make():
    """Generate code files"""
    pass


@make.command(name='migration')
@click.argument('name', required=False)
@click.option('--table', '-t', help='Table name for migration')
@click.option('--empty', is_flag=True, help='Create empty migration (no autogenerate)')
@click.option('--auto', is_flag=True, help='Generate a migration name from the table or timestamp')
def make_migration(name, table, empty, auto):
    """Create a new migration file"""
    if auto and name:
        fastie_console.error("Cannot use both auto mode (--auto) and manual name argument")
        return
        
    if not auto and not name:
        fastie_console.error("Migration name is required in manual mode")
        return
    
    if auto:
        if empty:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            message = f"empty_migration_{timestamp}"
        elif table:
            message = f"update_{table.lower()}_table"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            message = f"update_schema_{timestamp}"
        fastie_console.step(f"Generated name: {message}")
    else:
        if table and not name.startswith('create_'):
            message = f"create_{table}_table"
        else:
            message = name.lower().replace(' ', '_')
        fastie_console.step(f"Creating migration: {message}")

    head = _ensure_single_migration_head()
    cmd = ['revision']
    if not empty:
        cmd.append('--autogenerate')
    cmd.extend(['-m', message])
    if head:
        cmd.extend(['--head', head])

    _run_alembic(*cmd)
    fastie_console.success("Migration created successfully!")


@make.command(name='model')
@click.argument('name')
@click.option('--fields', '-f', help='Model fields (name:type,email:str)')
@click.option('--no-import', is_flag=True, help='Do not auto-import to __init__.py')
def make_model(name, fields, no_import):
    """Create a new model"""
    try:
        model_content = _generate_model_template(name, fields)
        model_file = Path(f"app/models/{_to_snake_case(name)}.py")
        
        with open(model_file, 'w') as f:
            f.write(model_content)
        
        fastie_console.success(f"Model created: [bold]{model_file}[/bold]")
        
        if not no_import:
            if _add_model_to_init(name):
                fastie_console.success(f"Auto-imported {_to_class_name(name)} to models/__init__.py")
            else:
                fastie_console.warning(f"Could not auto-import to __init__.py")
        
        fastie_console.info("Next step: fastie make migration --auto")
    except Exception as e:
        fastie_console.error(f"Error creating model: {str(e)}")


@make.command(name='resource')
@click.argument('name')
@click.option('--fields', '-f', help='Fields such as name:str,email:email,price:decimal')
@click.option(
    '--migrate',
    is_flag=True,
    help='Also create an autogenerated Alembic revision (database must already be at head)',
)
@click.option('--force', is_flag=True, help='Overwrite generated files if they already exist')
def make_resource(name, fields, migrate, force):
    """Create a model, schemas, and a plain FastAPI CRUD router."""
    try:
        snake_name = _to_snake_case(name)
        class_name = _to_class_name(name)
        field_specs = _parse_resource_fields(fields)

        files = {
            Path(f"app/models/{snake_name}.py"): _generate_model_template(name, fields),
            Path(f"app/schemas/requests/{snake_name}/{snake_name}_create_schema.py"):
                _generate_resource_create_schema(name, field_specs),
            Path(f"app/schemas/requests/{snake_name}/{snake_name}_update_schema.py"):
                _generate_resource_update_schema(name, field_specs),
            Path(f"app/schemas/responses/{snake_name}/{snake_name}_response_schema.py"):
                _generate_resource_response_schema(name, field_specs),
            Path(f"app/api/v1/routes/{snake_name}.py"):
                _generate_resource_router(name, field_specs),
        }
        init_files = set()
        for file_path in files:
            init_files.add(file_path.parent / '__init__.py')
        init_files.add(Path('app/api/v1/routes/__init__.py'))

        if not force:
            existing = [str(path) for path in files if path.exists()]
            if existing:
                raise click.ClickException(
                    "Refusing to overwrite existing generated files: " + ', '.join(existing)
                )

        for file_path, content in files.items():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
        for init_file in init_files:
            init_file.parent.mkdir(parents=True, exist_ok=True)
            init_file.touch(exist_ok=True)

        _add_model_to_init(name)
        if _register_resource_route(name):
            fastie_console.success(f"Resource route registered: /api/v1/{snake_name}s")
        else:
            fastie_console.info(
                f"Add {class_name} router to app/routes/api.py if this project was created by an older Fastie version."
            )

        fastie_console.success(f"Resource created: [bold]{class_name}[/bold]")
        if migrate:
            table_name = snake_name if snake_name.endswith('s') else f"{snake_name}s"
            head = _ensure_single_migration_head()
            migration_command = ['revision', '--autogenerate', '-m', f"create_{table_name}_table"]
            if head:
                migration_command.extend(['--head', head])
            _run_alembic(*migration_command)
            fastie_console.success(f"Migration created: create_{table_name}_table")
            fastie_console.step("Review it, then run: fastie db migrate")
        else:
            fastie_console.step(f"Next step: fastie make migration add_{snake_name}_table --auto")
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(f"Error creating resource: {e}") from e


@make.command(name='schema')
@click.argument('name')
@click.option('--type', 'schema_type', type=click.Choice(['request', 'response', 'model']), default='model')
def make_schema(name, schema_type):
    """Create a new schema"""
    snake_name = _to_snake_case(name)
    path_map = {
        'request': (Path(f"app/schemas/requests/{snake_name}"), f"{snake_name}_request_schema.py"),
        'response': (Path(f"app/schemas/responses/{snake_name}"), f"{snake_name}_response_schema.py"),
        'model': (Path(f"app/schemas/models/{snake_name}"), f"{snake_name}_base_schema.py")
    }
    path, file_name = path_map[schema_type]
    
    path.mkdir(parents=True, exist_ok=True)
    (path / '__init__.py').touch()
    
    schema_content = _generate_schema_template(name, schema_type)
    schema_file = path / file_name
    
    with open(schema_file, 'w') as f:
        f.write(schema_content)
    
    fastie_console.success(f"Schema created: [bold]{schema_file}[/bold]")




@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
@click.option('--workers', default=1, type=click.IntRange(min=1), show_default=True)
@click.option('--proxy-headers/--no-proxy-headers', default=False)
@click.option('--forwarded-allow-ips', default=None, help='Trusted proxy IPs for forwarded headers')
def serve(host, port, reload, workers, proxy_headers, forwarded_allow_ips):
    """Start the application server."""
    _serve(host, port, reload, workers, proxy_headers, forwarded_allow_ips)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
def dev(host, port):
    """Start the development server with auto-reload."""
    _serve(host, port, True, 1, False, None)


def _serve(host, port, reload, workers=1, proxy_headers=False, forwarded_allow_ips=None):
    """Run Uvicorn for the current application."""
    if reload and workers != 1:
        raise click.ClickException("--reload cannot be combined with more than one worker")

    fastie_console.print_banner()
    fastie_console.info(f"Starting server at [bold]http://{host}:{port}[/bold]")
    
    cmd = ['uvicorn', 'app.main:app', '--host', host, '--port', str(port)]
    if reload:
        cmd.append('--reload')
    if workers > 1:
        cmd.extend(['--workers', str(workers)])
    if proxy_headers:
        cmd.append('--proxy-headers')
    if forwarded_allow_ips:
        cmd.extend(['--forwarded-allow-ips', forwarded_allow_ips])
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        click.echo("")
        fastie_console.warning("Server stopped by user")




@cli.command()
def routes():
    """Show all registered routes"""
    try:
        from app.main import app
        
        rows = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for method in route.methods:
                    if method != 'HEAD':
                        rows.append([
                            f"[bold cyan]{method}[/bold cyan]",
                            route.path,
                            getattr(route, 'name', 'N/A'),
                            getattr(route, 'summary', 'N/A') or ''
                        ])
            elif hasattr(route, 'path'):
                rows.append([
                    "[dim]MOUNT[/dim]",
                    route.path,
                    getattr(route, 'name', 'N/A'),
                    f"Mount: {type(route).__name__}"
                ])
        
        rows.sort(key=lambda x: x[1])
        fastie_console.table("Application Routes", ["Method", "Path", "Name", "Summary"], rows)
                
    except Exception as e:
        fastie_console.error(f"Error inspecting routes: {e}")
        _show_fallback_routes()


@cli.command()
@click.option('--path', '-p', help='Filter routes by path pattern')
@click.option('--method', '-m', help='Filter routes by HTTP method')
@click.option('--tag', '-t', help='Filter routes by tag')
@click.option('--detail', is_flag=True, help='Show detailed route information')
def route_list(path, method, tag, detail):
    """List routes with optional filters and details"""
    click.echo("Detailed Route Information:")
    click.echo("=" * 100)
    
    try:
        from app.main import app
        
        routes_found = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                for route_method in route.methods:
                    if route_method != 'HEAD':
                        # Apply filters
                        if path and path.lower() not in route.path.lower():
                            continue
                        if method and method.upper() != route_method:
                            continue
                        if tag and not any(tag.lower() in t.lower() for t in getattr(route, 'tags', [])):
                            continue
                            
                        route_info = {
                            'method': route_method,
                            'path': route.path,
                            'name': getattr(route, 'name', 'N/A'),
                            'summary': getattr(route, 'summary', 'N/A'),
                            'description': getattr(route, 'description', 'N/A'),
                            'tags': getattr(route, 'tags', []),
                            'operation_id': getattr(route, 'operation_id', 'N/A'),
                            'dependencies': getattr(route, 'dependencies', []),
                            'response_model': getattr(route, 'response_model', None),
                            'status_code': getattr(route, 'status_code', 200)
                        }
                        routes_found.append(route_info)
        
        if not routes_found:
            click.echo("No routes found matching the filters.")
            return
            
        for i, route_info in enumerate(routes_found):
            if i > 0:
                click.echo("-" * 100)
            
            # Method and path header
            method_color = {
                'GET': 'green',
                'POST': 'blue', 
                'PUT': 'yellow',
                'DELETE': 'red',
                'PATCH': 'magenta'
            }.get(route_info['method'], 'white')
            
            method_styled = click.style(route_info['method'], fg=method_color, bold=True)
            click.echo(f"{method_styled} {route_info['path']}")
            
            if detail:
                # Detailed information
                if route_info['summary'] != 'N/A':
                    click.echo(f"  Summary: {route_info['summary']}")
                if route_info['description'] != 'N/A':
                    click.echo(f"  Description: {route_info['description']}")
                if route_info['tags']:
                    click.echo(f"  Tags: {', '.join(route_info['tags'])}")
                if route_info['name'] != 'N/A':
                    click.echo(f"  Name: {route_info['name']}")
                if route_info['operation_id'] != 'N/A':
                    click.echo(f"  Operation ID: {route_info['operation_id']}")
                click.echo(f"  Status Code: {route_info['status_code']}")
                if route_info['response_model']:
                    click.echo(f"  Response Model: {route_info['response_model']}")
                if route_info['dependencies']:
                    click.echo(f"  Dependencies: {len(route_info['dependencies'])} dependencies")
            else:
                # Compact information
                info_parts = []
                if route_info['summary'] != 'N/A':
                    info_parts.append(route_info['summary'])
                if route_info['tags']:
                    info_parts.append(f"[{', '.join(route_info['tags'])}]")
                if info_parts:
                    click.echo(f"  {' | '.join(info_parts)}")
        
        click.echo("=" * 100)
        click.echo(f"Found {len(routes_found)} route(s)")
        
    except ImportError as e:
        click.echo(f"Failed to import FastAPI app: {e}")
        click.echo("Make sure you're running this from the project root directory.")
    except Exception as e:
        click.echo(f"Error inspecting routes: {e}")


@cli.command()
def install():
    """Install project dependencies"""
    click.echo("Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        click.echo("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Failed to install dependencies: {str(e)}")


# =============================================================================
# TEMPLATE GENERATORS
# =============================================================================

def _docker_setup_files(database, workers):
    """Build Docker deployment files for a generated Fastie project."""
    if database == 'postgres':
        database_service = """  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-fastie}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env.docker}
      POSTGRES_DB: ${POSTGRES_DB:-fastie}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER:-fastie} -d $${POSTGRES_DB:-fastie}"]
      interval: 5s
      timeout: 5s
      retries: 12
    volumes:
      - postgres_data:/var/lib/postgresql/data
"""
        database_url = (
            "postgresql+psycopg2://${POSTGRES_USER:-fastie}:"
            "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env.docker}@"
            "postgres:5432/${POSTGRES_DB:-fastie}"
        )
        volume_name = 'postgres_data'
        database_dependency = 'postgres'
        env_content = f"""# Docker deployment settings
# Keep this file local. Use a secret manager for production credentials.
ENVIRONMENT=production
POSTGRES_USER=fastie
POSTGRES_PASSWORD=change-this-password
POSTGRES_DB=fastie

# Fastie application security
JWT_SECRET=replace-with-a-random-secret-at-least-32-characters-long
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Replace these values with the real public origins and hostnames.
CORS_ALLOWED_ORIGINS=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
TRUSTED_PROXY_IPS=
FORWARDED_ALLOW_IPS=127.0.0.1
WORKERS={workers}
"""
    else:
        database_service = """  mysql:
    image: mysql:8.4
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE:-fastie}
      MYSQL_USER: ${MYSQL_USER:-fastie}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:?set MYSQL_PASSWORD in .env.docker}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?set MYSQL_ROOT_PASSWORD in .env.docker}
    healthcheck:
      test: ["CMD-SHELL", 'mysqladmin ping -h 127.0.0.1 -u root -p"$${MYSQL_ROOT_PASSWORD}"']
      interval: 5s
      timeout: 5s
      retries: 20
    volumes:
      - mysql_data:/var/lib/mysql
"""
        database_url = (
            "mysql+pymysql://${MYSQL_USER:-fastie}:"
            "${MYSQL_PASSWORD:?set MYSQL_PASSWORD in .env.docker}@"
            "mysql:3306/${MYSQL_DATABASE:-fastie}"
        )
        volume_name = 'mysql_data'
        database_dependency = 'mysql'
        env_content = f"""# Docker deployment settings
# Keep this file local. Use a secret manager for production credentials.
ENVIRONMENT=production
MYSQL_DATABASE=fastie
MYSQL_USER=fastie
MYSQL_PASSWORD=change-this-password
MYSQL_ROOT_PASSWORD=change-this-root-password

# Fastie application security
JWT_SECRET=replace-with-a-random-secret-at-least-32-characters-long
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Replace these values with the real public origins and hostnames.
CORS_ALLOWED_ORIGINS=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
TRUSTED_PROXY_IPS=
FORWARDED_ALLOW_IPS=127.0.0.1
WORKERS={workers}
"""

    migration_service = f"""  migrate:
    build:
      context: .
      args:
        FASTIE_PACKAGE: ${{FASTIE_PACKAGE:-fastie-py=={FASTIE_VERSION}}}
    env_file:
      - .env.docker
    environment:
      DATABASE_URL: {database_url}
    depends_on:
      {database_dependency}:
        condition: service_healthy
    command: ["fastie", "db", "migrate"]
    restart: "no"

"""

    compose = f"""services:
  app:
    build:
      context: .
      args:
        FASTIE_PACKAGE: ${{FASTIE_PACKAGE:-fastie-py=={FASTIE_VERSION}}}
    env_file:
      - .env.docker
    environment:
      DATABASE_URL: {database_url}
      REDIS_URL: redis://redis:6379/0
      WORKERS: ${{WORKERS:-{workers}}}
      FORWARDED_ALLOW_IPS: ${{FORWARDED_ALLOW_IPS:-127.0.0.1}}
    ports:
      - "8000:8000"
    depends_on:
      {database_dependency}:
        condition: service_healthy
      redis:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    restart: unless-stopped

{migration_service}{database_service}  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 12
    volumes:
      - redis_data:/data

volumes:
  {volume_name}:
  redis_data:
"""

    dockerfile = f"""FROM python:3.12-slim

ARG FASTIE_PACKAGE=fastie-py=={FASTIE_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \\
    python -m pip install "${{FASTIE_PACKAGE}}" -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

CMD ["sh", "-c", "fastie serve --host 0.0.0.0 --port 8000 --workers ${{WORKERS:-{workers}}} --proxy-headers --forwarded-allow-ips ${{FORWARDED_ALLOW_IPS:-127.0.0.1}}"]
"""

    dockerignore = """.env
.env.*
!.env.docker.example
.git
.gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.venv/
venv/
tests/
app.db
"""

    return {
        Path('Dockerfile'): dockerfile,
        Path('docker-compose.yml'): compose,
        Path('.dockerignore'): dockerignore,
        Path('.env.docker.example'): env_content,
    }


def _generate_env_content(database):
    """Generate .env file content"""
    database = database.lower()
    if database == 'sqlite':
        db_url = "sqlite:///./app.db"
    elif database == 'postgres':
        db_url = "postgresql+psycopg2://user:password@localhost:5432/dbname"
    else:  # mysql
        db_url = "mysql+pymysql://user:password@localhost:3306/dbname"
    
    jwt_secret = secrets.token_urlsafe(32)

    return f"""# Database Configuration
DATABASE_URL={db_url}

# Deployment environment (development, staging, or production)
ENVIRONMENT=development
CORS_ALLOWED_ORIGINS=http://localhost:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT configuration (use a secret manager for production)
JWT_SECRET={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
REDIS_URL=
TRUSTED_PROXY_IPS=
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=3600
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_ECHO=False
"""


def _generate_model_template(name, fields):
    """Generate model template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("model/base_model.mako", name=name, fields=fields)
        except Exception as e:
            logger.warning("Template rendering failed: %s", e)
    
    # Fallback to inline template
    class_name = _to_class_name(name)
    template = f'''from sqlalchemy import Column, Integer, String, Boolean, DateTime
from fastie.models.abstract_model import AbstractModel

class {class_name}(AbstractModel):
    __tablename__ = '{_to_snake_case(name)}s'

'''
    
    if fields:
        for field in fields.split(','):
            if ':' in field:
                field_name, field_type = field.split(':')
                if field_type.lower() in ['str', 'string']:
                    template += f"    {field_name} = Column(String(255), nullable=False)\n"
                elif field_type.lower() in ['int', 'integer']:
                    template += f"    {field_name} = Column(Integer, nullable=False)\n"
                elif field_type.lower() in ['bool', 'boolean']:
                    template += f"    {field_name} = Column(Boolean, default=True)\n"
                else:
                    template += f"    {field_name} = Column(String(255), nullable=False)  # {field_type}\n"
    else:
        template += "    # Add your model fields here\n"
        template += "    # name = Column(String(100), nullable=False)\n"
    
    return template


def _generate_schema_template(name, schema_type):
    """Generate schema template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            template_map = {
                'response': 'schema/response.mako',
                'request': 'schema/request.mako',
                'model': 'schema/base.mako'
            }
            template_name = template_map.get(schema_type, 'schema/base.mako')
            return render_template(template_name, name=name, schema_type=schema_type)
        except Exception as e:
            logger.warning("Template rendering failed: %s", e)
    
    # Fallback to inline template
    if schema_type == 'response':
        return f'''from pydantic import BaseModel, ConfigDict

class {name.title()}ResponseSchema(BaseModel):
    """Response schema for {name.title()}"""
    id: int
    # Add response fields here
    
    model_config = ConfigDict(from_attributes=True)
'''
    elif schema_type == 'request':
        return f'''from pydantic import BaseModel

class {name.title()}RequestSchema(BaseModel):
    """Request schema for {name.title()}"""
    # Add request fields here
    pass
'''
    else:  # model
        return f'''from pydantic import BaseModel, ConfigDict

class {name.title()}BaseSchema(BaseModel):
    """Base schema for {name.title()}"""
    # Add base fields here
    
    model_config = ConfigDict(from_attributes=True)
'''


def _parse_resource_fields(fields):
    """Parse the small, safe field DSL used by ``make resource``."""
    if not fields:
        return []

    type_map = {
        'str': ('str', None, None),
        'string': ('str', None, None),
        'text': ('str', None, None),
        'int': ('int', None, None),
        'integer': ('int', None, None),
        'bool': ('bool', None, 'True'),
        'boolean': ('bool', None, 'True'),
        'datetime': ('datetime', 'datetime', None),
        'date': ('date', 'date', None),
        'float': ('float', None, None),
        'decimal': ('Decimal', 'Decimal', None),
        'email': ('EmailStr', 'EmailStr', None),
        'url': ('HttpUrl', 'HttpUrl', None),
        'phone': ('str', None, None),
        'json': ('dict', None, 'None'),
    }
    parsed = []
    for raw_field in fields.split(','):
        parts = [part.strip() for part in raw_field.split(':')]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise click.ClickException(
                f"Invalid field '{raw_field}'. Use the format name:type, for example name:str."
            )

        field_name = _to_snake_case(parts[0])
        field_type = parts[1].lower()
        if field_type not in type_map:
            supported = ', '.join(sorted(type_map))
            raise click.ClickException(
                f"Unsupported type '{field_type}' for '{field_name}'. Supported types: {supported}."
            )
        python_type, import_name, default = type_map[field_type]
        parsed.append({
            'name': field_name,
            'python_type': python_type,
            'import_name': import_name,
            'default': default,
        })
    return parsed


def _resource_schema_imports(fields):
    imports = {'from pydantic import BaseModel, ConfigDict'}
    if any(field['import_name'] == 'EmailStr' for field in fields):
        imports.add('from pydantic import EmailStr')
    if any(field['import_name'] == 'HttpUrl' for field in fields):
        imports.add('from pydantic import HttpUrl')
    if any(field['import_name'] == 'datetime' for field in fields):
        imports.add('from datetime import datetime')
    if any(field['import_name'] == 'date' for field in fields):
        imports.add('from datetime import date')
    if any(field['import_name'] == 'Decimal' for field in fields):
        imports.add('from decimal import Decimal')
    return '\n'.join(sorted(imports))


def _generate_resource_create_schema(name, fields):
    class_name = _to_class_name(name)
    field_lines = [
        f"    {field['name']}: {field['python_type']}"
        + (f" = {field['default']}" if field['default'] is not None else '')
        for field in fields
    ] or ['    pass']
    return f'''{_resource_schema_imports(fields)}


class {class_name}CreateSchema(BaseModel):
    """Validated input for creating a {class_name}."""
{chr(10).join(field_lines)}

    model_config = ConfigDict(str_strip_whitespace=True)
'''


def _generate_resource_update_schema(name, fields):
    class_name = _to_class_name(name)
    field_lines = [
        f"    {field['name']}: {field['python_type']} | None = None"
        for field in fields
    ] or ['    pass']
    return f'''{_resource_schema_imports(fields)}
from typing import Optional


class {class_name}UpdateSchema(BaseModel):
    """Optional fields for updating a {class_name}."""
{chr(10).join(field_lines)}

    model_config = ConfigDict(str_strip_whitespace=True)
'''


def _generate_resource_response_schema(name, fields):
    class_name = _to_class_name(name)
    field_lines = [
        f"    {field['name']}: {field['python_type']}"
        + (f" = {field['default']}" if field['default'] is not None else '')
        for field in fields
    ]
    if not field_lines:
        field_lines = ['    pass']
    imports = _resource_schema_imports(fields)
    if 'from datetime import datetime' not in imports:
        imports += '\nfrom datetime import datetime'
    return f'''{imports}


class {class_name}ResponseSchema(BaseModel):
    """Public representation of a {class_name}."""
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
{chr(10).join(field_lines)}

    model_config = ConfigDict(from_attributes=True)
'''


def _generate_resource_router(name, fields):
    if TEMPLATES_AVAILABLE:
        try:
            return render_template(
                'resource/router.mako',
                name=name,
                fields=fields,
            )
        except Exception as e:
            logger.warning("Template rendering failed: %s", e)

    snake_name = _to_snake_case(name)
    class_name = _to_class_name(name)
    return f'''from fastapi import APIRouter

# Template rendering is unavailable. Re-run after installing the Fastie template dependencies.
router = APIRouter()
'''


def _show_fallback_routes():
    """Show fallback routes when app inspection fails"""
    fallback_routes = [
        ("GET", "/docs", "API Documentation"),
        ("GET", "/redoc", "ReDoc Documentation"),
        ("GET", "/openapi.json", "OpenAPI Schema"),
        ("POST", "/auth/login", "User Login"),
        ("GET", "/auth/greet", "Greeting Endpoint"),
        ("GET", "/user/", "Get All Users"),
        ("POST", "/user/register", "Register User"),
    ]
    
    rows = []
    for method, path, description in fallback_routes:
        rows.append([f"[bold cyan]{method}[/bold cyan]", path, description])
    
    fastie_console.table("Fallback Routes", ["Method", "Path", "Description"], rows)


def _to_class_name(name):
    """Convert name to proper PascalCase class name"""
    parts = name.lower().replace('-', '_').split('_')
    return ''.join(word.capitalize() for word in parts)


def _to_snake_case(name):
    """Convert a CLI name to the convention used by generated modules."""
    return name.lower().replace('-', '_')


def _add_model_to_init(name):
    """Add model import to models/__init__.py"""
    init_file = Path("app/models/__init__.py")
    
    try:
        if not init_file.exists():
            class_name = _to_class_name(name)
            init_content = f"""from fastie.models.abstract_model import AbstractModel
from .{_to_snake_case(name)} import {class_name}

__all__ = ['AbstractModel', '{class_name}']
"""
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_content)
            return True
        
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_name = _to_class_name(name)
        import_line = f"from .{_to_snake_case(name)} import {class_name}"
        if import_line in content:
            return True
        
        lines = content.split('\n')
        new_lines = []
        import_added = False
        all_updated = False
        
        for i, line in enumerate(lines):
            if line.startswith('from .') and not import_added:
                new_lines.append(line)
                next_line_idx = i + 1
                if (next_line_idx >= len(lines) or 
                    not lines[next_line_idx].startswith('from .')):
                    new_lines.append(import_line)
                    import_added = True
            
            elif line.strip().startswith('__all__') and not all_updated:
                if "'" in line or '"' in line:
                    import re
                    items = re.findall(r"['\"]([^'\"]+)['\"]", line)
                    if class_name not in items:
                        items.append(class_name)
                    items_str = ', '.join([f"'{item}'" for item in items])
                    new_lines.append(f"__all__ = [{items_str}]")
                    all_updated = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # If import wasn't added (no existing imports), add at the end
        if not import_added:
            # Find a good place to insert
            insert_idx = 0
            for i, line in enumerate(new_lines):
                if line.strip().startswith('#') or line.strip() == '':
                    continue
                insert_idx = i
                break
            new_lines.insert(insert_idx, import_line)
        
        # Write back
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        return True
        
    except Exception as e:
        logger.exception("Could not update app/models/__init__.py: %s", e)
        return False


def _register_resource_route(name):
    """Register a generated router in the marker section of a new project."""
    routes_file = Path('app/routes/api.py')
    if not routes_file.exists():
        return False

    content = routes_file.read_text(encoding='utf-8')
    snake_name = _to_snake_case(name)
    class_name = _to_class_name(name)
    import_marker = '# Fastie resource routes - generated imports'
    include_marker = '# Fastie resource routes - generated includes'
    import_line = (
        f'from app.api.v1.routes.{snake_name} import router as {snake_name}_router'
    )
    include_line = (
        f'api_router.include_router({snake_name}_router, '
        f'prefix="/{snake_name if snake_name.endswith("s") else snake_name + "s"}", '
        f'tags=["{class_name}"])'
    )

    if import_marker not in content or include_marker not in content:
        return False
    if import_line in content:
        return True

    content = content.replace(
        import_marker,
        f'{import_line}\n{import_marker}',
        1,
    )
    content = content.replace(
        include_marker,
        f'{include_line}\n{include_marker}',
        1,
    )
    routes_file.write_text(content, encoding='utf-8')
    return True


if __name__ == '__main__':
    cli()
