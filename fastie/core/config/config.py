from dynaconf import Dynaconf

from fastie.core.decorators import component_decorator
from fastie.core.paths.config import __config_path__

@component_decorator
class Config:
    def __init__(self):
        self.settings = Dynaconf(
            settings_files=[f"{__config_path__()}/security.toml"],
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

