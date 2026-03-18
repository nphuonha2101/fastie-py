from pathlib import Path


def __config_path__():
    """
    Returns the path to the configuration file.
    """
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    config_path = base_dir / "app" / "core" / "config"
    return config_path
