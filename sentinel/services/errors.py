from sentinel.errors import SentinelError


class AuthError(SentinelError):
    """Base class for authentication failures."""


class InvalidPinError(AuthError):
    """The submitted PIN did not match."""


class LockedOutError(AuthError):
    """Too many failed attempts from this client IP; locked out."""

    def __init__(self, retry_after_seconds: float) -> None:
        super().__init__(f"Locked out for {retry_after_seconds:.0f} more seconds")
        self.retry_after_seconds = retry_after_seconds
