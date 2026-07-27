"""Orchestration and wiring. The only layer that composes everything else."""

from sentinel.services.auth import AuthService, hash_pin
from sentinel.services.container import Container, build_container
from sentinel.services.dispatcher import DispatchResult, EventDispatcher
from sentinel.services.errors import AuthError, InvalidPinError, LockedOutError

__all__ = [
    "AuthError",
    "AuthService",
    "Container",
    "DispatchResult",
    "EventDispatcher",
    "InvalidPinError",
    "LockedOutError",
    "build_container",
    "hash_pin",
]
