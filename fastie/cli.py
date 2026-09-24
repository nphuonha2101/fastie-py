#!/usr/bin/env python3
import click
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import shutil
import secrets
from dotenv import load_dotenv
from fastie.core.utils.console import fastie_console

# Import template engine
try:
    from fastie.template_engine import render_template, get_template_helpers
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
@click.version_option(version='0.0.1a1', prog_name='Fastie CLI')
def cli():
    """Fastie CLI for convention-driven FastAPI projects."""
    # Add current directory to path so it can find 'app'
    sys.path.append(os.getcwd())
    
    if len(sys.argv) == 1:
        fastie_console.print_banner()




@cli.command()
@click.argument('project_name')
@click.option('--database', '-d', default='mysql', help='Database type (mysql, sqlite, postgres)')
@click.option('--auth', is_flag=True, help='Deprecated: authentication is included by default')
@click.option('--path', '-p', help='Target directory path (default: current directory)')
def new(project_name, database, auth, path):
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


@make.command(name='controller')
@click.argument('name')
@click.option('--resource', '-r', is_flag=True, help='Create resource controller with CRUD methods')
def make_controller(name, resource):
    """Create a new controller"""
    path = Path(f"app/api/v1/controllers/{name.lower()}")
    path.mkdir(parents=True, exist_ok=True)
    (path / '__init__.py').touch()
    
    controller_content = _generate_controller_template(name, resource)
    controller_file = path / f"{name.lower()}_controller.py"
    
    with open(controller_file, 'w') as f:
        f.write(controller_content)
    
    fastie_console.success(f"Controller created: [bold]{controller_file}[/bold]")
    _update_routes_registration(name)


@make.command(name='service')
@click.argument('name')
def make_service(name):
    """Create a new service"""
    interface_path = Path(f"app/services/interfaces/{name.lower()}")
    interface_path.mkdir(parents=True, exist_ok=True)
    (interface_path / '__init__.py').touch()
    
    interface_content = _generate_service_interface_template(name)
    interface_file = interface_path / f"i_{name.lower()}_service.py"
    with open(interface_file, 'w') as f:
        f.write(interface_content)
    
    impl_path = Path(f"app/services/implements/{name.lower()}")
    impl_path.mkdir(parents=True, exist_ok=True)
    (impl_path / '__init__.py').touch()
    
    impl_content = _generate_service_implementation_template(name)
    impl_file = impl_path / f"{name.lower()}_service.py"
    with open(impl_file, 'w') as f:
        f.write(impl_content)
    
    fastie_console.success(f"Service created: [bold]{name.title()}[/bold]")
    fastie_console.step(f"Interface: {interface_file}")
    fastie_console.step(f"Implementation: {impl_file}")


@make.command(name='repository')
@click.argument('name')
def make_repository(name):
    """Create a new repository"""
    interface_path = Path(f"app/repositories/interfaces/{name.lower()}")
    interface_path.mkdir(parents=True, exist_ok=True)
    (interface_path / '__init__.py').touch()
    
    interface_content = _generate_repository_interface_template(name)
    interface_file = interface_path / f"i_{name.lower()}_repository.py"
    with open(interface_file, 'w') as f:
        f.write(interface_content)
    
    impl_path = Path(f"app/repositories/implements/{name.lower()}")
    impl_path.mkdir(parents=True, exist_ok=True)
    (impl_path / '__init__.py').touch()
    
    impl_content = _generate_repository_implementation_template(name)
    impl_file = impl_path / f"{name.lower()}_repository.py"
    with open(impl_file, 'w') as f:
        f.write(impl_content)
    
    fastie_console.success(f"Repository created: [bold]{name.title()}[/bold]")
    fastie_console.step(f"Interface: {interface_file}")
    fastie_console.step(f"Implementation: {impl_file}")


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
@click.option('--force', is_flag=True, help='Overwrite generated files if they already exist')
def make_resource(name, fields, force):
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
        fastie_console.step(f"Review the model and run: fastie make migration add_{snake_name}_table --auto")
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
def serve(host, port, reload):
    """Start the application server."""
    _serve(host, port, reload)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind')
@click.option('--port', default=8000, help='Port to bind')
def dev(host, port):
    """Start the development server with auto-reload."""
    _serve(host, port, True)


def _serve(host, port, reload):
    """Run Uvicorn for the current application."""
    fastie_console.print_banner()
    fastie_console.info(f"Starting server at [bold]http://{host}:{port}[/bold]")
    
    cmd = ['uvicorn', 'app.main:app', '--host', host, '--port', str(port)]
    if reload:
        cmd.append('--reload')
    
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
    click.echo("📋 Detailed Route Information:")
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
            click.echo("⚠️  No routes found matching the filters!")
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
                    click.echo(f"  📝 Summary: {route_info['summary']}")
                if route_info['description'] != 'N/A':
                    click.echo(f"  📄 Description: {route_info['description']}")
                if route_info['tags']:
                    click.echo(f"  🏷️  Tags: {', '.join(route_info['tags'])}")
                if route_info['name'] != 'N/A':
                    click.echo(f"  🔍 Name: {route_info['name']}")
                if route_info['operation_id'] != 'N/A':
                    click.echo(f"  🆔 Operation ID: {route_info['operation_id']}")
                click.echo(f"  📊 Status Code: {route_info['status_code']}")
                if route_info['response_model']:
                    click.echo(f"  📤 Response Model: {route_info['response_model']}")
                if route_info['dependencies']:
                    click.echo(f"  🔗 Dependencies: {len(route_info['dependencies'])} dependencies")
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
        click.echo(f"📊 Found {len(routes_found)} route(s)")
        
    except ImportError as e:
        click.echo(f"❌ Failed to import FastAPI app: {e}")
        click.echo("💡 Make sure you're running this from the project root directory")
    except Exception as e:
        click.echo(f"❌ Error inspecting routes: {e}")


@cli.command()
def install():
    """Install project dependencies"""
    click.echo("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        click.echo("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to install dependencies: {str(e)}")


# =============================================================================
# TEMPLATE GENERATORS
# =============================================================================

def _generate_env_content(database):
    """Generate .env file content"""
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

# JWT configuration (use a secret manager for production)
JWT_SECRET={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ISSUER=fastie
JWT_AUDIENCE=fastie-api
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=

# Application Settings
DEBUG=True
"""


def _generate_controller_template(name, resource):
    """Generate controller template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            template_name = "controller/resource_controller.mako" if resource else "controller/simple_controller.mako"
            return render_template(template_name, name=name, resource=resource)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
            click.echo("📄 Falling back to inline template...")
    
    # Fallback to inline template
    class_name = f"{name.title()}Controller"
    service_interface = f"I{name.title()}Service"
    
    template = f'''from abc import ABC
from fastie.controllers.base_controller import BaseController
from fastie.core.decorators.di import controller, inject
from app.services.interfaces.{name.lower()}.i_{name.lower()}_service import {service_interface}

@controller
@inject
class {class_name}(BaseController, ABC):
    def __init__(self, {name.lower()}_service: {service_interface}):
        super().__init__()
        self.{name.lower()}_service = {name.lower()}_service

    def define_routes(self):
        """Define all routes for this controller"""'''
    
    if resource:
        template += f'''
        self.router.get("/", summary="Get All {name.title()}", status_code=200)(self.index)
        self.router.post("/", summary="Create {name.title()}", status_code=201)(self.create)
        self.router.get("/{{id}}", summary="Get {name.title()}", status_code=200)(self.show)
        self.router.put("/{{id}}", summary="Update {name.title()}", status_code=200)(self.update)
        self.router.delete("/{{id}}", summary="Delete {name.title()}", status_code=204)(self.delete)

    def index(self):
        """Get all {name.lower()}s"""
        try:
            {name.lower()}s = self.{name.lower()}_service.get_all()
            return self.success(content={name.lower()}s, message="{name.title()}s retrieved successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def create(self):
        """Create a new {name.lower()}"""
        try:
            # Implementation needed
            return self.success(message="{name.title()} created successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def show(self, id: int):
        """Get {name.lower()} by ID"""
        try:
            {name.lower()} = self.{name.lower()}_service.get_by_id(id)
            return self.success(content={name.lower()}, message="{name.title()} retrieved successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def update(self, id: int):
        """Update {name.lower()}"""
        try:
            # Implementation needed
            return self.success(message="{name.title()} updated successfully.")
        except Exception as e:
            return self.error(message=str(e))

    def delete(self, id: int):
        """Delete {name.lower()}"""
        try:
            self.{name.lower()}_service.delete(id)
            return self.success(message="{name.title()} deleted successfully.")
        except Exception as e:
            return self.error(message=str(e))
'''
    else:
        template += f'''
        self.router.get("/", summary="Get {name.title()}", status_code=200)(self.index)

    def index(self):
        """Handle {name.lower()} requests"""
        try:
            return self.success(message="{name.title()} endpoint working!")
        except Exception as e:
            return self.error(message=str(e))
'''
    
    return template


def _generate_service_interface_template(name):
    """Generate service interface template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("service/interface.mako", name=name)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
    
    # Fallback to inline template
    return f'''from fastie.services.interfaces.i_service import IService

class I{name.title()}Service(IService):
    """Interface for {name.title()} service"""
    pass
'''


def _generate_service_implementation_template(name):
    """Generate service implementation template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("service/implementation.mako", name=name)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
    
    # Fallback to inline template
    return f'''from fastie.core.decorators.di import service
from app.repositories.interfaces.{name.lower()}.i_{name.lower()}_repository import I{name.title()}Repository
from fastie.services.implements.service import Service
from app.services.interfaces.{name.lower()}.i_{name.lower()}_service import I{name.title()}Service

@service
class {name.title()}Service(Service, I{name.title()}Service):
    def __init__(self, repository: I{name.title()}Repository):
        # Update with appropriate response schema
        super().__init__(repository, None)  # Replace None with response schema class
'''


def _generate_repository_interface_template(name):
    """Generate repository interface template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("repository/interface.mako", name=name)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
    
    # Fallback to inline template
    return f'''from fastie.repositories.interfaces.i_repository import IRepository

class I{name.title()}Repository(IRepository):
    """Interface for {name.title()} repository"""
    pass
'''


def _generate_repository_implementation_template(name):
    """Generate repository implementation template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("repository/implementation.mako", name=name)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
    
    # Fallback to inline template
    return f'''from fastie.core.decorators.di import repository
from fastie.repositories.implements.repository import Repository
from app.repositories.interfaces.{name.lower()}.i_{name.lower()}_repository import I{name.title()}Repository
# from app.models.{name.lower()} import {name.title()}  # Uncomment when model exists

@repository
class {name.title()}Repository(Repository, I{name.title()}Repository):
    def __init__(self):
        # Update with actual model class
        super().__init__(None)  # Replace None with model class
'''


def _generate_model_template(name, fields):
    """Generate model template using Mako templates"""
    if TEMPLATES_AVAILABLE:
        try:
            return render_template("model/base_model.mako", name=name, fields=fields)
        except Exception as e:
            click.echo(f"⚠️  Template error: {e}")
    
    # Fallback to inline template
    class_name = _to_class_name(name)
    template = f'''from sqlalchemy import Column, Integer, String, Boolean, DateTime
from fastie.models.abstract_model import AbstractModel
from typing import Optional

from pydantic import BaseModel

class {class_name}(AbstractModel):
    __tablename__ = '{_to_snake_case(name)}s'
    
    def get_response_model(self) -> Optional[BaseModel]:
        return None

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
            click.echo(f"⚠️  Template error: {e}")
    
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
            click.echo(f"⚠️  Template error: {e}")

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
        click.echo(f"Error updating __init__.py: {str(e)}")
        return False


def _update_routes_registration(name):
    """Update routes registration in api.py"""
    routes_file = Path("app/routes/api.py")
    if routes_file.exists():
        fastie_console.info(f"Don't forget to register {name.title()}Controller in [bold]app/routes/api.py[/bold]")


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
