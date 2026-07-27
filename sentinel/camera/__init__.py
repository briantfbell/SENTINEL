"""CameraProvider protocol and implementations."""

from sentinel.camera.errors import CameraError
from sentinel.camera.mock import MockCamera
from sentinel.camera.provider import CameraProvider

__all__ = ["CameraError", "CameraProvider", "MockCamera"]
