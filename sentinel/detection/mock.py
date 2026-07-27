"""No hardware or model file required to run the test suite
(AGENTS.md section 2 rule 2).
"""

from sentinel.detection.provider import Detection


class MockDetector:
    """Replays a scripted sequence of per-frame detections, one call per
    frame. Holds on the last scripted frame once exhausted rather than
    looping, so a demo script's tail state (e.g. "gone") is stable.

    Defaults to an empty script — always "no detection" — so a live
    system with this provider configured stays inert until a script is
    deliberately injected, rather than fabricating intrusions.
    """

    def __init__(self, script: list[list[Detection]] | None = None) -> None:
        self._script = script or [[]]
        self._index = 0

    def detect(self, frame: bytes) -> list[Detection]:
        result = self._script[self._index]
        self._index = min(self._index + 1, len(self._script) - 1)
        return result
