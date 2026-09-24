import importlib
import logging
import os
import pkgutil
from pathlib import Path
from fastie.core.decorators.di import load_components

logger = logging.getLogger(__name__)

def discover_components():
    """
    Automatically discover and import all components to trigger decorators.
    Recursively scans the entire app and fastie packages.
    """
    def scan_package(package_name):
        try:
            package = importlib.import_module(package_name)
            package_dir = os.path.dirname(package.__file__)

            for _, name, is_pkg in pkgutil.iter_modules([package_dir]):
                full_name = f"{package_name}.{name}"
                try:
                    importlib.import_module(full_name)
                    if is_pkg:
                        scan_package(full_name)
                except Exception as exc:
                    logger.exception("Failed to import component module %s", full_name)
                    raise RuntimeError(f"Failed to import component module {full_name}") from exc
        except Exception as exc:
            logger.exception("Failed to import package %s", package_name)
            raise RuntimeError(f"Failed to import package {package_name}") from exc

    # Start the recursive scan from both framework and application packages
    for base_package in ["fastie", "app"]:
        try:
            importlib.import_module(base_package)
            scan_package(base_package)
        except Exception as exc:
            logger.exception("Failed to import base package %s", base_package)
            raise RuntimeError(f"Failed to import base package {base_package}") from exc

def discover_submodules(package_name):
    """Recursively import all submodules of a package."""
    package = importlib.import_module(package_name)
    package_dir = os.path.dirname(package.__file__)

    for _, name, is_pkg in pkgutil.iter_modules([package_dir]):
        full_name = f"{package_name}.{name}"
        try:
            importlib.import_module(full_name)
            if is_pkg:
                discover_submodules(full_name)
        except Exception as exc:
            logger.exception("Error importing %s", full_name)
            raise RuntimeError(f"Error importing {full_name}") from exc

def initialize_application():
    """Initialize legacy decorator components for existing applications."""
    # Discover and import all component classes
    discover_components()

    # Initialize all non-lazy components
    load_components()

    # Any additional application-specific initialization
    # that can't be handled by decorators
