from sentinel.errors import SentinelError


class IllegalTransitionError(SentinelError):
    """Raised when an event is not legal for the current state."""
