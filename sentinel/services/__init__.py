"""Orchestration and wiring. The only layer that composes everything else."""

from sentinel.services.dispatcher import DispatchResult, EventDispatcher

__all__ = ["DispatchResult", "EventDispatcher"]
