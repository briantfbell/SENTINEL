"""Configuration loading and validation. Imports nothing else internal."""

from sentinel.config.errors import ConfigError
from sentinel.config.settings import Settings, load_settings

__all__ = ["ConfigError", "Settings", "load_settings"]
