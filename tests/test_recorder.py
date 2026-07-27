from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel.camera import MockCamera
from sentinel.database import RecordingRepository, apply_migrations, open_engine
from sentinel.services import Recorder

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)


def _recorder(
    tmp_path: Path, current: dict[str, datetime]
) -> tuple[Recorder, RecordingRepository]:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repository = RecordingRepository(engine)
    recorder = Recorder(
        camera_provider=MockCamera(),
        recording_repository=repository,
        recordings_path=tmp_path / "recordings",
        clock=lambda: current["now"],
    )
    return recorder, repository


def test_start_then_stop_persists_a_finalized_recording(tmp_path: Path) -> None:
    current = {"now": NOW}
    recorder, repository = _recorder(tmp_path, current)

    recorder.start(trigger_event_id=42)
    current["now"] = NOW + timedelta(seconds=30)
    recording_id = recorder.stop()

    assert recording_id is not None
    recordings = repository.recent(10)
    assert len(recordings) == 1
    assert recordings[0].started_at == NOW
    assert recordings[0].ended_at == NOW + timedelta(seconds=30)
    assert recordings[0].trigger_event_id == 42
    assert recordings[0].size_bytes > 0


def test_start_writes_a_bookend_frame_to_disk(tmp_path: Path) -> None:
    current = {"now": NOW}
    recorder, _repository = _recorder(tmp_path, current)

    recorder.start()

    clip_dirs = list((tmp_path / "recordings").iterdir())
    assert len(clip_dirs) == 1
    assert (clip_dirs[0] / "start.jpg").exists()


def test_stop_without_start_is_a_safe_no_op(tmp_path: Path) -> None:
    current = {"now": NOW}
    recorder, repository = _recorder(tmp_path, current)

    result = recorder.stop()

    assert result is None
    assert repository.recent(10) == []


def test_start_while_already_recording_does_not_restart_it(tmp_path: Path) -> None:
    current = {"now": NOW}
    recorder, _repository = _recorder(tmp_path, current)

    recorder.start(trigger_event_id=1)
    current["now"] = NOW + timedelta(seconds=5)
    recorder.start(trigger_event_id=2)  # re-entry action; must be ignored
    current["now"] = NOW + timedelta(seconds=10)
    recorder.stop()

    clip_dirs = list((tmp_path / "recordings").iterdir())
    assert len(clip_dirs) == 1  # not two separate recordings
