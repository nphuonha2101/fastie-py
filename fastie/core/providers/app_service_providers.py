import importlib
import os
import pkgutil
from pathlib import Path
from fastie.core.decorators.di import load_components

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
                except Exception:
                    pass
        except Exception:
            pass

    # Start the recursive scan from both framework and application packages
    for base_package in ["fastie", "app"]:
        try:
            importlib.import_module(base_package)
            scan_package(base_package)
        except Exception:
            pass

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
        except Exception as e:
            print(f"Error importing {full_name}: {e}")

def initialize_application():
    """Initialize the application components."""
    # Discover and import all component classes
    discover_components()

    # Initialize all non-lazy components
    load_components()

    # Any additional application-specific initialization
    # that can't be handled by decorators