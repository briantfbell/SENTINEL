"""Detector protocol, debouncer, and implementations."""

from sentinel.detection.debouncer import DetectionDebouncer
from sentinel.detection.errors import DetectionError
from sentinel.detection.mock import MockDetector
from sentinel.detection.provider import Detection, Detector

__all__ = [
    "Detection",
    "DetectionDebouncer",
    "DetectionError",
    "Detector",
    "MockDetector",
]
