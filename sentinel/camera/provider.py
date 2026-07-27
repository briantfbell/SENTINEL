"""The CameraProvider interface.

AGENTS.md section 4.2: the MVP dashboard polls a JPEG snapshot endpoint
rather than streaming — deliberately the least impressive option because
it's the one that cannot break. `get_snapshot` is the entire surface a
provider needs for that; a future `RtspCamera` (slice 9) implements the
same protocol without the dashboard's contract changing at all.
"""

from typing import Protocol


class CameraProvider(Protocol):
    def get_snapshot(self) -> bytes:
        """Return a single JPEG frame."""
        ...
