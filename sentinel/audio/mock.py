"""No hardware required to run the test suite (AGENTS.md section 2 rule 2)."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlaybackCall:
    clip_path: Path
    volume: float


class MockAudioPlayer:
    """Records what would have played instead of touching real audio."""

    def __init__(self) -> None:
        self.calls: list[PlaybackCall] = []
        self.stop_count = 0

    def play(self, clip_path: Path, volume: float) -> None:
        self.calls.append(PlaybackCall(clip_path, volume))

    def stop(self) -> None:
        self.stop_count += 1
