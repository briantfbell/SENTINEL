"""Configuration loading and validation. Imports nothing else internal."""

from sentinel.config.errors import ConfigError
from sentinel.config.settings import (
    AudioSettings,
    DetectionSettings,
    Settings,
    StateSettings,
    load_settings,
)

__all__ = [
    "AudioSettings",
    "ConfigError",
    "DetectionSettings",
    "Settings",
    "StateSettings",
    "load_settings",
]
