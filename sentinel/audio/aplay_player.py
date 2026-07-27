"""Plays clips via `aplay`, volume via `amixer` (DECISIONS.md 0012).

Requires `alsa-utils` on the host. Not exercised by the test suite —
AGENTS.md section 2 rule 2 requires every provider to have a mock, and
this one is verified against real hardware by hand, not in CI.
"""

import subprocess
from pathlib import Path

from sentinel.audio.errors import AudioError


class AplayAudioPlayer:
    def __init__(self, device: str, mixer_control: str) -> None:
        self._device = device
        self._mixer_control = mixer_control
        self._process: subprocess.Popen[bytes] | None = None

    def play(self, clip_path: Path, volume: float) -> None:
        volume_percent = round(max(0.0, min(1.0, volume)) * 100)
        try:
            subprocess.run(
                ["amixer", "-q", "sset", self._mixer_control, f"{volume_percent}%"],
                check=True,
            )
            process = subprocess.Popen(
                ["aplay", "-q", "-D", self._device, str(clip_path)]
            )
            self._process = process
            process.wait()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise AudioError(f"Failed to play {clip_path}: {exc}") from exc
        finally:
            self._process = None

    def stop(self) -> None:
        if self._process is not None:
            self._process.terminate()
