#!/usr/bin/env python3
import click
import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import shutil
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

@click.group(cls=FastieGroup, invoke_without_command=True)
@click.version_option(version='0.0.1a1', prog_name='Fastie CLI')
def cli():
    """Fastie Framework CLI - Laravel Artisan-like command line interface"""
    # Add current directory to path so it can find 'app'
    sys.path.append(os.getcwd())
    
    if len(sys.argv) == 1:
        fastie_console.print_banner()




@cli.command()
@click.argument('project_name')
@click.option('--database', '-d', default='mysql', help='Database type (mysql, sqlite, postgres)')
@click.option('--auth', is_flag=True, help='Include authentication boilerplate')
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
        fastie_console.step("fastie serve")
        
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
    try:
        subprocess.run(['alembic', 'upgrade', 'head'], check=True)
        fastie_console.success("Migrations completed successfully!")
    except subprocess.CalledProcessError as e:
        fastie_console.error(f"Migration failed: {str(e)}")


@database.command(name='rollback')
@click.option('--steps', '-s', default=1, help='Number of steps to rollback')
def db_rollback(steps):
    """Rollback database migrations"""
    fastie_console.info(f"Rolling back {steps} migration(s)...")
    try:
        for _ in range(steps):
            subprocess.run(['alembic', 'downgrade', '-1'], check=True)
        fastie_console.success("Rollback completed successfully!")
    except subprocess.CalledProcessError as e:
        fastie_console.error(f"Rollback failed: {str(e)}")


@database.command(name='reset')
@click.confirmation_option(prompt='Are you sure you want to reset the database?')
def db_reset():
    """Reset database (rollback all migrations)"""
    fastie_console.info("Resetting database...")
    try:
        subprocess.run(['alembic', 'downgrade', 'base'], check=True)
        subprocess.run(['alembic', 'upgrade', 'head'], check=True)
        fastie_console.success("Database reset completed!")
    except subprocess.CalledProcessError as e:
        fastie_console.error(f"Database reset failed: {str(e)}")


@database.command(name='status')
def db_status():
    """Show migration status"""
    try:
        subprocess.run(['alembic', 'current'], check=True)
        subprocess.run(['alembic', 'history'], check=True)
    except subprocess.CalledProcessError as e:
        fastie_console.error(f"Failed to get database status: {str(e)}")




@cli.group(name='make')
def make():
    """Generate code files"""
    pass


@make.command(name='migration')
@click.argument('name', required=False)
@click.option('--table', '-t', help='Table name for migration')
@click.option('--empty', is_flag=True, help='Create empty migration (no autogenerate)')
@click.option('--auto', is_flag=True, help='Auto-generate migration name based on detected changes')
def make_migration(name, table, empty, auto):
    """Create a new migration file"""
    if auto and name:
        fastie_console.error("Cannot use both auto mode (--auto) and manual name argument")
        return
        
    if not auto and not name:
        fastie_console.error("Migration name is required in manual mode")
        return
    
    try:
        if auto:
            fastie_console.info("Analyzing database changes...")
            if empty:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                message = f"empty_migration_{timestamp}"
            else:
                message = _generate_auto_migration_name(table)
            fastie_console.step(f"Generated name: {message}")
        else:
            if table and not name.startswith('create_'):
                message = f"create_{table}_table"
            else:
                message = name.lower().replace(' ', '_')
            fastie_console.step(f"Creating migration: {message}")
        
        cmd = ['alembic', 'revision', '-m', message]
        if not empty:
            cmd.insert(2, '--autogenerate')
            
        subprocess.run(cmd, check=True)
        fastie_console.success("Migration created successfully!")
                
    except subprocess.CalledProcessError as e:
        fastie_console.error(f"Failed to create migration: {str(e)}")


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
        model_file = Path(f"app/models/{name.lower()}.py")
        
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


@make.command(name='schema')
@click.argument('name')
@click.option('--type', 'schema_type', type=click.Choice(['request', 'response', 'model']), default='model')
def make_schema(name, schema_type):
    """Create a new schema"""
    path_map = {
        'request': (Path(f"app/schemas/requests/{name.lower()}"), f"{name.lower()}_request_schema.py"),
        'response': (Path(f"app/schemas/responses/{name.lower()}"), f"{name.lower()}_response_schema.py"),
        'model': (Path(f"app/schemas/models/{name.lower()}"), f"{name.lower()}_base_schema.py")
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
    """Start the development server"""
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
# AUTO MIGRATION NAME GENERATOR
# =============================================================================

def _generate_auto_migration_name(table_hint=None):
    """Generate migration name based on detected database changes"""
    from datetime import datetime
    import tempfile
    import re
    
    try:
        # Create a temporary migration to analyze changes
        temp_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_message = f"temp_analysis_{temp_timestamp}"
        
        # Run autogenerate to see what changes would be made
        result = subprocess.run([
            'alembic', 'revision', '--autogenerate', '-m', temp_message, '--head', 'head'
        ], capture_output=True, text=True, check=True)
        
        # Find the generated migration file
        migration_dir = Path('alembic/versions')
        if migration_dir.exists():
            # Get the most recent migration file (our temp one)
            migration_files = list(migration_dir.glob('*.py'))
            if migration_files:
                latest_migration = max(migration_files, key=lambda x: x.stat().st_mtime)
                
                # Read and analyze the migration content
                with open(latest_migration, 'r') as f:
                    content = f.read()
                
                # Parse operations to generate descriptive name
                name_parts = []
                
                # Check for table operations
                if 'op.create_table(' in content:
                    tables = re.findall(r"op\.create_table\(['\"](\w+)['\"]", content)
                    if tables:
                        name_parts.append(f"create_{tables[0]}_table")
                
                if 'op.drop_table(' in content:
                    tables = re.findall(r"op\.drop_table\(['\"](\w+)['\"]", content)
                    if tables:
                        name_parts.append(f"drop_{tables[0]}_table")
                
                # Check for column operations
                if 'op.add_column(' in content:
                    columns = re.findall(r"op\.add_column\(['\"](\w+)['\"].*?['\"](\w+)['\"]", content)
                    if columns:
                        table_name, col_name = columns[0]
                        name_parts.append(f"add_{col_name}_to_{table_name}")
                
                if 'op.drop_column(' in content:
                    columns = re.findall(r"op\.drop_column\(['\"](\w+)['\"].*?['\"](\w+)['\"]", content)
                    if columns:
                        table_name, col_name = columns[0]
                        name_parts.append(f"remove_{col_name}_from_{table_name}")
                
                # Check for index operations
                if 'op.create_index(' in content:
                    name_parts.append("add_indexes")
                
                if 'op.drop_index(' in content:
                    name_parts.append("remove_indexes")
                
                # Check for foreign key operations
                if 'op.create_foreign_key(' in content:
                    name_parts.append("add_foreign_keys")
                
                if 'op.drop_constraint(' in content and 'foreignkey' in content.lower():
                    name_parts.append("remove_foreign_keys")
                
                # Clean up temp migration file
                latest_migration.unlink()
                
                # Generate final name
                if name_parts:
                    # Take first few operations to avoid very long names
                    final_name = "_and_".join(name_parts[:2])
                    if len(name_parts) > 2:
                        final_name += f"_and_{len(name_parts)-2}_more"
                else:
                    # No meaningful changes detected
                    final_name = f"update_schema_{temp_timestamp}"
                
                return final_name
        
        # Fallback if analysis fails
        return f"auto_migration_{temp_timestamp}"
        
    except subprocess.CalledProcessError as e:
        # Fallback to table hint or timestamp
        if table_hint:
            return f"update_{table_hint}_table"
        return f"auto_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    except Exception as e:
        # Ultimate fallback
        return f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


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
    
    return f"""# Database Configuration
DATABASE_URL={db_url}

# Application Settings
DEBUG=True
SECRET_KEY=your-secret-key-here

# JWT Settings (if using authentication)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
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
    __tablename__ = '{name.lower()}s'
    
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


def _add_model_to_init(name):
    """Add model import to models/__init__.py"""
    init_file = Path("app/models/__init__.py")
    
    try:
        if not init_file.exists():
            class_name = _to_class_name(name)
            init_content = f"""from .abstract_model import AbstractModel
from .{name.lower()} import {class_name}

__all__ = ['AbstractModel', '{class_name}']
"""
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write(init_content)
            return True
        
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_name = _to_class_name(name)
        import_line = f"from .{name.lower()} import {class_name}"
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
        click.echo(f"❌ Error updating __init__.py: {str(e)}")
        return False


def _update_routes_registration(name):
    """Update routes registration in api.py"""
    routes_file = Path("app/routes/api.py")
    if routes_file.exists():
        fastie_console.info(f"Don't forget to register {name.title()}Controller in [bold]app/routes/api.py[/bold]")


if __name__ == '__main__':
    cli()