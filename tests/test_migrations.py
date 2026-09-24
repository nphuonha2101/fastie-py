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
        initial_revision = "043ea57085e0"
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
        self.assertEqual(len(revisions), 2)
        self.assertTrue(any("empty_migration_" in revision.name for revision in revisions))

    def test_production_rollback_is_blocked_without_force(self):
        self.env["ENVIRONMENT"] = "production"
        rollback = self.run_fastie("db", "rollback")

        self.assertNotEqual(rollback.returncode, 0)
        self.assertIn("Rollback is blocked in production", rollback.stdout + rollback.stderr)

    def test_generated_app_authenticates_database_users(self):
        migrate = self.run_fastie("db", "migrate")
        self.assertEqual(migrate.returncode, 0, migrate.stdout + migrate.stderr)

        auth_flow = self.run_python(
            """
from app.main import app
from app.models.user import User
from app.routes.api import get_current_user, login, register_user
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.requests.access_token.access_token_request_schema import AccessTokenRequestSchema
import bcrypt
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
login_response = login(AccessTokenRequestSchema(
    email='test@example.com',
    password='correct-horse-battery-staple',
), login_db)
token = login_response['data']['access_token']
payload = Jwt.decode_token(token)
current_user = get_current_user(token, login_db)
assert current_user.id == created_id
assert payload['sub'] == str(created_id)

legacy = User(
    name='Legacy User',
    email='legacy@example.com',
    password=bcrypt.hashpw(b'legacy-password', bcrypt.gensalt()).decode(),
)
login_db.add(legacy)
login_db.commit()
legacy_id = legacy.id
login(AccessTokenRequestSchema(
    email='legacy@example.com',
    password='legacy-password',
), login_db)
assert login_db.query(User).filter(User.id == legacy_id).one().password.startswith('$argon2')
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
            2,
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
assert '/api/v1/auth/login' in paths
assert '/healthz' in paths
assert '/readyz' in paths
security = paths['/api/v1/user/']['get']['security']
assert security and security[0].get('OAuth2PasswordBearer') == []
            """
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
