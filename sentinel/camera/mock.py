"""No hardware required to run the test suite (AGENTS.md section 2 rule 2)."""

from pathlib import Path

from sentinel.camera.errors import CameraError

_BUNDLED_STILLS_DIR = Path(__file__).resolve().parent / "stills"


class MockCamera:
    """Cycles through a directory of JPEG stills, looping indefinitely.

    Defaults to the small fixture set bundled with this package so the
    system is runnable out of the box (AGENTS.md section 2 rule 3);
    `stills_dir` can point at a real directory of test images instead.
    """

    def __init__(self, stills_dir: Path | None = None) -> None:
        self._stills_dir = stills_dir or _BUNDLED_STILLS_DIR
        self._frames = sorted(self._stills_dir.glob("*.jpg"))
        if not self._frames:
            raise CameraError(f"No .jpg stills found in {self._stills_dir}")
        self._index = 0

    def get_snapshot(self) -> bytes:
        frame_path = self._frames[self._index]
        self._index = (self._index + 1) % len(self._frames)
        return frame_path.read_bytes()
