import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUBS_ROOT = PROJECT_ROOT / "fastie" / "stubs"


class MigrationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        shutil.copytree(STUBS_ROOT, self.project_dir, dirs_exist_ok=True)

        self.env = os.environ.copy()
        self.env.update(
            {
                "DATABASE_URL": f"sqlite:///{self.project_dir / 'app.db'}",
                "ENVIRONMENT": "development",
                "JWT_SECRET": "12345678901234567890123456789012",
                "JWT_ALGORITHM": "HS256",
                "PYTHONPATH": str(PROJECT_ROOT),
            }
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_alembic(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=self.project_dir,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def run_fastie(self, *args):
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "from fastie.cli import cli; cli()",
                *args,
            ],
            cwd=self.project_dir,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def run_python(self, script):
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=self.project_dir,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def test_clean_database_can_upgrade_and_pass_schema_check(self):
        migrate = self.run_fastie("db", "migrate")
        self.assertEqual(migrate.returncode, 0, migrate.stdout + migrate.stderr)

        check = self.run_fastie("db", "check")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("schema matches", check.stdout + check.stderr)

        repeat = self.run_fastie("db", "migrate")
        self.assertEqual(repeat.returncode, 0, repeat.stdout + repeat.stderr)

    def test_multiple_heads_are_rejected_before_migration(self):
        initial_revision = "c4f1d6a8e9b0"
        first = self.run_alembic("revision", "-m", "branch_a", "--head", initial_revision)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)

        second = self.run_alembic(
            "revision",
            "-m",
            "branch_b",
            "--head",
            initial_revision,
            "--splice",
        )
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)

        check = self.run_fastie("db", "check")
        self.assertNotEqual(check.returncode, 0)
        self.assertIn("Multiple Alembic heads detected", check.stdout + check.stderr)

    def test_auto_migration_name_does_not_create_a_temporary_revision(self):
        result = self.run_fastie("make", "migration", "--auto", "--empty")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        revisions = sorted((self.project_dir / "alembic" / "versions").glob("*.py"))
        self.assertEqual(len(revisions), 4)
        self.assertTrue(any("empty_migration_" in revision.name for revision in revisions))

    def test_production_rollback_is_blocked_without_force(self):
        self.env["ENVIRONMENT"] = "production"
        rollback = self.run_fastie("db", "rollback")

        self.assertNotEqual(rollback.returncode, 0)
        self.assertIn("Rollback is blocked in production", rollback.stdout + rollback.stderr)

    def test_production_config_rejects_sqlite(self):
        self.env["ENVIRONMENT"] = "production"
        result = self.run_python(
            "from fastie.core.config.config import get_config; get_config()"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("server database", result.stdout + result.stderr)

    def test_docker_setup_generates_stack_without_overwriting(self):
        result = self.run_fastie("setup", "docker", "--database", "postgres")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        expected_files = {
            "Dockerfile",
            "docker-compose.yml",
            ".dockerignore",
            ".env.docker.example",
        }
        self.assertEqual(
            {path.name for path in self.project_dir.iterdir() if path.name in expected_files},
            expected_files,
        )
        compose = (self.project_dir / "docker-compose.yml").read_text()
        self.assertIn("postgres:16-alpine", compose)
        self.assertIn("redis:7-alpine", compose)
        self.assertIn('"fastie", "db", "migrate"', compose)
        self.assertIn("service_completed_successfully", compose)

        repeat = self.run_fastie("setup", "docker")
        self.assertNotEqual(repeat.returncode, 0)
        self.assertIn("Refusing to overwrite", repeat.stdout + repeat.stderr)

        mysql = self.run_fastie("setup", "docker", "--database", "mysql", "--workers", "4", "--force")
        self.assertEqual(mysql.returncode, 0, mysql.stdout + mysql.stderr)
        mysql_compose = (self.project_dir / "docker-compose.yml").read_text()
        self.assertIn("mysql:8.4", mysql_compose)
        self.assertIn("WORKERS=4", (self.project_dir / ".env.docker.example").read_text())

        local = self.run_fastie(
            "setup",
            "docker",
            "--local-source",
            str(PROJECT_ROOT),
            "--force",
        )
        self.assertEqual(local.returncode, 0, local.stdout + local.stderr)
        local_wheels = list((self.project_dir / ".fastie-local").glob("fastie_py-*.whl"))
        self.assertTrue(local_wheels)
        local_dockerfile = (self.project_dir / "Dockerfile").read_text()
        self.assertIn("COPY .fastie-local/", local_dockerfile)
        self.assertNotIn("ARG FASTIE_PACKAGE", local_dockerfile)

    def test_generated_app_authenticates_database_users(self):
        migrate = self.run_fastie("db", "migrate")
        self.assertEqual(migrate.returncode, 0, migrate.stdout + migrate.stderr)

        auth_flow = self.run_python(
            """
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.routes.api import get_current_user, logout, refresh, register_user, token as issue_token
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.requests.refresh_token.refresh_token_request_schema import RefreshTokenRequestSchema
from fastapi.security import OAuth2PasswordRequestForm
from fastie.core.securities.jwt import Jwt
from fastie.infrastructures.database.dependencies import get_database

database = get_database()
create_db = database.get_session()
created_response = register_user(UserCreateSchema(
    name='Test User',
    email='test@example.com',
    password='correct-horse-battery-staple',
), create_db)
created_id = created_response['data'].id
stored_hash = create_db.query(User).filter(User.id == created_id).one().password
assert stored_hash.startswith('$argon2')
create_db.close()

login_db = database.get_session()
login_response = issue_token(OAuth2PasswordRequestForm(
    username='test@example.com',
    password='correct-horse-battery-staple',
), login_db)
token = login_response['access_token']
refresh_token = login_response['refresh_token']
payload = Jwt.decode_token(token)
current_user = get_current_user(token, login_db)
assert current_user.id == created_id
assert payload['sub'] == str(created_id)

rotated = refresh(RefreshTokenRequestSchema(refresh_token=refresh_token), login_db)
assert rotated['access_token']
assert rotated['refresh_token'] != refresh_token
refresh_rows = login_db.query(RefreshToken).order_by(RefreshToken.id).all()
assert len(refresh_rows) == 2
assert refresh_rows[0].family_id == refresh_rows[1].family_id
try:
    refresh(RefreshTokenRequestSchema(refresh_token=refresh_token), login_db)
except Exception as exc:
    assert getattr(exc, 'status_code', None) == 401
    assert getattr(exc, 'detail', None) == 'Refresh token reuse detected'
else:
    raise AssertionError('Refresh token rotation did not revoke the old token')
assert login_db.query(RefreshToken).filter(RefreshToken.revoked_at.is_(None)).count() == 0
try:
    refresh(RefreshTokenRequestSchema(refresh_token=rotated['refresh_token']), login_db)
except Exception as exc:
    assert getattr(exc, 'status_code', None) == 401
    assert getattr(exc, 'detail', None) == 'Refresh token reuse detected'
else:
    raise AssertionError('Refresh token family was not revoked after reuse')
logout(RefreshTokenRequestSchema(refresh_token=rotated['refresh_token']), login_db)

login_db.close()
            """
        )
        self.assertEqual(auth_flow.returncode, 0, auth_flow.stdout + auth_flow.stderr)

    def test_resource_generator_creates_plain_fastapi_feature(self):
        base_migrate = self.run_fastie("db", "migrate")
        self.assertEqual(base_migrate.returncode, 0, base_migrate.stdout + base_migrate.stderr)

        result = self.run_fastie(
            "make",
            "resource",
            "Product",
            "--fields",
            "name:str,price:decimal,is_active:bool",
            "--migrate",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.project_dir / "app/models/product.py").is_file())
        self.assertTrue((self.project_dir / "app/api/v1/routes/product.py").is_file())
        self.assertEqual(
            len(list((self.project_dir / "alembic/versions").glob("*.py"))),
            4,
        )

        migrate = self.run_fastie("db", "migrate")
        self.assertEqual(migrate.returncode, 0, migrate.stdout + migrate.stderr)

        routes = (self.project_dir / "app/routes/api.py").read_text()
        self.assertIn("product_router", routes)

        compile_result = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "app"],
            cwd=self.project_dir,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)

        import_result = self.run_python(
            """
from app.main import app
assert any(route.path == '/api/v1/products/' for route in app.routes)
            """
        )
        self.assertEqual(import_result.returncode, 0, import_result.stdout + import_result.stderr)

    def test_generated_app_exposes_standard_oauth2_and_health_routes(self):
        result = self.run_python(
            """
from app.main import app

paths = app.openapi()['paths']
assert '/api/v1/auth/token' in paths
assert '/api/v1/auth/refresh' in paths
assert '/api/v1/auth/logout' in paths
assert '/healthz' in paths
assert '/readyz' in paths
security = paths['/api/v1/user/']['get']['security']
assert security and security[0].get('OAuth2PasswordBearer') == []
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
