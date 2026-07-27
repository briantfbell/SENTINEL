import subprocess
from pathlib import Path

import pytest

from sentinel.audio import AplayAudioPlayer, AudioError, MockAudioPlayer, PlaybackCall


def test_mock_player_records_calls() -> None:
    player = MockAudioPlayer()

    player.play(Path("sounds/warning.wav"), 0.5)

    assert player.calls == [PlaybackCall(Path("sounds/warning.wav"), 0.5)]


def test_mock_player_counts_stops() -> None:
    player = MockAudioPlayer()

    player.stop()
    player.stop()

    assert player.stop_count == 2


def test_aplay_player_sets_volume_then_plays(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool) -> None:
        calls.append(cmd)

    class FakePopen:
        def __init__(self, cmd: list[str]) -> None:
            calls.append(cmd)

        def wait(self) -> None:
            pass

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    player = AplayAudioPlayer(device="default", mixer_control="Master")
    player.play(Path("sounds/warning.wav"), 0.5)

    assert calls[0] == ["amixer", "-q", "sset", "Master", "50%"]
    assert calls[1] == ["aplay", "-q", "-D", "default", "sounds/warning.wav"]


def test_aplay_player_wraps_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_run(cmd: list[str], check: bool) -> None:
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", failing_run)

    player = AplayAudioPlayer(device="default", mixer_control="Master")

    with pytest.raises(AudioError):
        player.play(Path("sounds/warning.wav"), 0.5)


def test_aplay_player_stop_terminates_the_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminated = []

    class FakeProcess:
        def wait(self) -> None:
            pass

        def terminate(self) -> None:
            terminated.append(True)

    monkeypatch.setattr(subprocess, "run", lambda cmd, check: None)
    monkeypatch.setattr(subprocess, "Popen", lambda cmd: FakeProcess())

    player = AplayAudioPlayer(device="default", mixer_control="Master")
    player._process = FakeProcess()  # type: ignore[assignment]
    player.stop()

    assert terminated == [True]
