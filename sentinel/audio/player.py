"""The AudioPlayer provider interface. `play` is a blocking call by
design — callers (the services-layer dispatcher) are responsible for
running it off the event loop, the same way camera/detection loops run
in threads rather than in async code (AGENTS.md section 5).
"""

from pathlib import Path
from typing import Protocol


class AudioPlayer(Protocol):
    def play(self, clip_path: Path, volume: float) -> None:
        """Play a clip synchronously at the given volume (0.0 to 1.0)."""
        ...

    def stop(self) -> None:
        """Stop any playback currently in progress. Safe to call when idle."""
        ...
