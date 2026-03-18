import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastie.core.providers.app_service_providers import initialize_application
from fastie.core.service_containers.service_containers import get_registry
from fastie.core.config.config import Config
from fastie.support.logging import LogManager

def test_logging():
    print("Loading .env...")
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Initializing application...")
    initialize_application()
    
    registry = get_registry()
    cfg = registry.resolve(Config)
    print(f"Full Logging Config: {cfg.get('logging')}")
    print(f"Logging default: {cfg.get('logging.default')}")
    print(f"Logging channels: {cfg.get('logging.channels')}")
    log = registry.resolve(LogManager)
    
    print("\nTesting default channel (stack -> daily)...")
    log.info("This is an info message from the default channel")
    log.error("This is an error message from the default channel")
    
    print("\nTesting single channel...")
    log.channel("single").debug("This is a debug message from the single channel")
    
    print("\nTesting errorlog channel...")
    log.channel("errorlog").warning("This is a warning message from the errorlog channel")

    print("\nChecking log files...")
    log_dir = Path("storage/logs")
    if log_dir.exists():
        for file in log_dir.glob("*.log"):
            print(f"File found: {file}")
            with open(file, "r") as f:
                print(f"Content of {file.name}:")
                print(f.read())
    else:
        print("Log directory not found!")

if __name__ == "__main__":
    test_logging()
