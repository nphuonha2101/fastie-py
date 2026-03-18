import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler, SysLogHandler
from typing import Dict, Any, Optional, List, Union

from fastie.core.decorators.di import component_decorator, inject
from fastie.core.config.config import Config

class Logger:
    """
    A wrapper around Python's logging.Logger to provide a Laravel-like API.
    """
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger

    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self.logger.critical(message, *args, **kwargs)

    def log(self, level: int, message: str, *args, **kwargs):
        self.logger.log(level, message, *args, **kwargs)

@component_decorator
class LogManager:
    """
    Manages logging channels and drivers, similar to Laravel's LogManager.
    """
    @inject
    def __init__(self, config: Config):
        self._config = config
        self._channels: Dict[str, Logger] = {}
        # Try multiple common keys for default channel (Laravel-style and Dynaconf-style)
        self._default_channel = (
            self._config.get("LOG_CHANNEL") or 
            self._config.get("logging.default") or 
            self._config.get("logging_default") or 
            self._config.get("default", "stack")
        )

    def channel(self, name: Optional[str] = None) -> Logger:
        """
        Get a logging channel by name.
        """
        name = name or self._default_channel
        
        if name not in self._channels:
            self._channels[name] = self._create_channel(name)
            
        return self._channels[name]

    def _create_channel(self, name: str) -> Logger:
        """
        Create a new logging channel based on configuration.
        """
        # Try multiple nested paths for channel configuration
        config = (
            self._config.get(f"logging.channels.{name}") or 
            self._config.get(f"logging_channels.{name}") or
            self._config.get(f"channels.{name}")
        )
        if not config:
            # Fallback to a basic internal logger if not configured
            logger = logging.getLogger(f"fastie.{name}")
            if not logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
            return Logger(name, logger)

        driver = config.get("driver", "single")
        
        if driver == "stack":
            return self._create_stack_driver(name, config)
        elif driver == "single":
            return self._create_single_driver(name, config)
        elif driver == "daily":
            return self._create_daily_driver(name, config)
        elif driver == "syslog":
            return self._create_syslog_driver(name, config)
        elif driver == "errorlog":
            return self._create_errorlog_driver(name, config)
        else:
            raise ValueError(f"Unsupported log driver: {driver}")

    def _create_stack_driver(self, name: str, config: Dict[str, Any]) -> Logger:
        """
        Create a stack driver that aggregates multiple channels.
        """
        channels = config.get("channels", [])
        logger = logging.getLogger(f"fastie.stack.{name}")
        logger.propagate = False
        
        for ch_name in channels:
            ch_logger = self.channel(ch_name)
            for handler in ch_logger.logger.handlers:
                logger.addHandler(handler)
        
        level = self._get_level(config.get("level", "debug"))
        logger.setLevel(level)
        
        return Logger(name, logger)

    def _create_single_driver(self, name: str, config: Dict[str, Any]) -> Logger:
        """
        Create a single file log driver.
        """
        path = config.get("path", f"storage/logs/fastie.log")
        self._ensure_dir(path)
        
        handler = RotatingFileHandler(
            filename=path,
            maxBytes=config.get("max_bytes", 10485760), # 10MB default
            backupCount=config.get("backup_count", 5)
        )
        return self._configure_handler(name, handler, config)

    def _create_daily_driver(self, name: str, config: Dict[str, Any]) -> Logger:
        """
        Create a daily rotating file log driver.
        """
        path = config.get("path", f"storage/logs/fastie.log")
        self._ensure_dir(path)
        
        handler = TimedRotatingFileHandler(
            filename=path,
            when="midnight",
            interval=1,
            backupCount=config.get("days", 7)
        )
        return self._configure_handler(name, handler, config)

    def _create_syslog_driver(self, name: str, config: Dict[str, Any]) -> Logger:
        """
        Create a syslog driver.
        """
        facility = config.get("facility", SysLogHandler.LOG_USER)
        handler = SysLogHandler(address='/dev/log', facility=facility)
        return self._configure_handler(name, handler, config)

    def _create_errorlog_driver(self, name: str, config: Dict[str, Any]) -> Logger:
        """
        Create an errorlog driver (logs to stderr).
        """
        handler = logging.StreamHandler()
        return self._configure_handler(name, handler, config)

    def _configure_handler(self, name: str, handler: logging.Handler, config: Dict[str, Any]) -> Logger:
        """
        Common configuration for handlers.
        """
        level = self._get_level(config.get("level", "debug"))
        handler.setLevel(level)
        
        formatter_str = config.get("formatter", '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter(formatter_str)
        handler.setFormatter(formatter)
        
        logger = logging.getLogger(f"fastie.{name}")
        logger.setLevel(level)
        logger.addHandler(handler)
        
        return Logger(name, logger)

    def _get_level(self, level: str) -> int:
        """
        Convert string level to logging integer level.
        """
        levels = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        return levels.get(level.lower(), logging.INFO)

    def _ensure_dir(self, file_path: str):
        """
        Ensure the directory for the log file exists.
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    # Proxy methods for the default channel
    def debug(self, message: str, *args, **kwargs):
        self.channel().debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        self.channel().info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.channel().warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        self.channel().error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        self.channel().critical(message, *args, **kwargs)
