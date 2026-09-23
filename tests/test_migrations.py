import os
import shutil
import subprocess
import sys
import tempfile
import threading
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
from app.api.v1.controllers.user_account.user_account_controller import UserAccountController
from app.models.user import User
from app.schemas.models.user.user_create_schema import UserCreateSchema
from app.schemas.models.user.user_update_schema import UserUpdateSchema
from fastie.core.securities.auth import Auth
from fastie.core.securities.jwt import Jwt
from fastie.core.service_containers.service_containers import get_registry

controller = get_registry().resolve(UserAccountController)
created = controller.user_service.create(UserCreateSchema(
    name='Test User',
    email='test@example.com',
    password='correct-horse-battery-staple',
))
updated = controller.user_service.update(created.id, UserUpdateSchema(name='Updated User'))
authenticated = Auth.authenticate(
    User,
    {'email': 'test@example.com', 'password': 'correct-horse-battery-staple'},
)
token = Auth.create_access_token({'sub': str(authenticated.id)})
payload = Jwt.decode_token(token)
assert created.id == authenticated.id
assert updated.name == 'Updated User'
assert payload['sub'] == str(created.id)
            """
        )
        self.assertEqual(auth_flow.returncode, 0, auth_flow.stdout + auth_flow.stderr)

    def test_repository_session_is_local_to_each_execution_context(self):
        from fastie.repositories.implements.repository import Repository

        repository = Repository(object)
        barrier = threading.Barrier(2)
        observed = []

        def worker():
            session = object()
            repository.set_session(session)
            barrier.wait()
            observed.append(repository.session is session)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(observed, [True, True])


if __name__ == "__main__":
    unittest.main()
