"""The Detector interface: raw, per-frame, no hysteresis applied.

AGENTS.md section 4.3: nothing outside detection (and camera) may import
onnxruntime or cv2 or reference a model file path — a real detector
(slice 10) keeps that entirely behind this Protocol.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Detection:
    """One raw hit in one frame. Confidence and box size only — enough
    for the debouncer's thresholds (section 4.4), nothing a real
    bounding box would add that isn't needed yet.
    """

    confidence: float
    box_area_ratio: float


class Detector(Protocol):
    def detect(self, frame: bytes) -> list[Detection]:
        """Return every raw hit in one frame. Empty list means no hits."""
        ...
