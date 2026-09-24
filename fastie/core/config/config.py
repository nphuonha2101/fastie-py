import os
from functools import lru_cache
from pathlib import Path
from dynaconf import Dynaconf
from dotenv import load_dotenv

from fastie.core.paths.config import __config_path__

class Config:
    def __init__(self):
        config_dir = __config_path__()
        load_dotenv()
        self.settings = Dynaconf(
            environments=True,
            load_dotenv=True,
            envvar_prefix="FASTIE",
            merge_enabled=True,
        )
        
        # Explicitly load logging.toml if it exists in framework or app
        framework_config = Path(__file__).resolve().parent / "logging.toml"
        if framework_config.exists():
            self.settings.load_file(path=str(framework_config))
            
        app_config = config_dir / "logging.toml"
        if app_config.exists():
            self.settings.load_file(path=str(app_config))

        # Load security.toml
        security_config = config_dir / "security.toml"
        if security_config.exists():
            self.settings.load_file(path=str(security_config))

        # Security and deployment values intentionally accept unprefixed
        # environment variables so generated projects can use a conventional
        # .env file without duplicating secrets under FASTIE_* names.
        for key in (
            "JWT_SECRET",
            "JWT_ALGORITHM",
            "JWT_ISSUER",
            "JWT_AUDIENCE",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "CORS_ALLOWED_ORIGINS",
            "REDIS_URL",
        ):
            value = os.getenv(key)
            if value is not None:
                self.settings.set(key, value)

        environment = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
        if environment in {"prod", "production"}:
            secret = self.settings.get("JWT_SECRET") or self.settings.get("SECRET_KEY")
            if not secret or len(str(secret)) < 32:
                raise RuntimeError(
                    "JWT_SECRET must be configured with at least 32 characters in production"
                )

    def get(self, key: str, default=None):
        """
        Retrieve a configuration value by key.

        Args:
            key (str): The key of the configuration value.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value or the default value if the key is not found.
        """
        return self.settings.get(key, default)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the process-local application configuration."""
    return Config()
