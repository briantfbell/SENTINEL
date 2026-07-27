from sentinel.errors import SentinelError


class ConfigError(SentinelError):
    """Raised when configuration fails to load or fails validation."""
