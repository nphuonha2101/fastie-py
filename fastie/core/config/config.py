from pathlib import Path
from dynaconf import Dynaconf

from fastie.core.decorators import component_decorator
from fastie.core.paths.config import __config_path__

@component_decorator
class Config:
    def __init__(self):
        config_dir = __config_path__()
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

