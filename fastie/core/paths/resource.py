from pathlib import Path


def __resources_path__() -> Path:
    """
    Returns the path to the resources directory.
    :return: Path object pointing to the resources' directory.
    """
    # Need to go up 4 levels: paths -> core -> app -> root
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    resources_path = base_dir / "resources"
    return resources_path

def __assets(filename: str) -> Path:
    """
    Returns the path to the specified asset file.

    Args:
        filename (str): The name of the asset file.

    Returns: a Path object pointing to the asset file.
    """
    resources_path = __resources_path__()
    asset_path = resources_path / "assets" / filename
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset file '{filename}' not found in {asset_path}")
    return asset_path