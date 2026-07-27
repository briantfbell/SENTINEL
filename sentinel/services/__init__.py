"""Orchestration and wiring. The only layer that composes everything else."""

from sentinel.services.auth import AuthService, hash_pin
from sentinel.services.container import Container, build_container
from sentinel.services.detection_loop import DetectionLoop
from sentinel.services.dispatcher import DispatchResult, EventDispatcher
from sentinel.services.errors import AuthError, InvalidPinError, LockedOutError
from sentinel.services.recorder import Recorder

__all__ = [
    "AuthError",
    "AuthService",
    "Container",
    "DetectionLoop",
    "DispatchResult",
    "EventDispatcher",
    "InvalidPinError",
    "LockedOutError",
    "Recorder",
    "build_container",
    "hash_pin",
]
