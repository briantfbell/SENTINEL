from sentinel.errors import SentinelError


class DetectionError(SentinelError):
    """Raised when a detector fails to produce a result."""
