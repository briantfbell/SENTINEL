from pathlib import Path

import pytest

from sentinel.camera import CameraError, MockCamera


def test_mock_camera_uses_bundled_stills_by_default() -> None:
    camera = MockCamera()

    snapshot = camera.get_snapshot()

    assert snapshot.startswith(b"\xff\xd8")  # JPEG magic bytes


def test_mock_camera_cycles_through_frames_in_order(tmp_path: Path) -> None:
    (tmp_path / "a.jpg").write_bytes(b"frame-a")
    (tmp_path / "b.jpg").write_bytes(b"frame-b")
    camera = MockCamera(stills_dir=tmp_path)

    sequence = [camera.get_snapshot() for _ in range(4)]

    assert sequence == [b"frame-a", b"frame-b", b"frame-a", b"frame-b"]


def test_mock_camera_raises_on_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(CameraError, match="No .jpg stills"):
        MockCamera(stills_dir=tmp_path)


def test_mock_camera_ignores_non_jpg_files(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("not an image")
    (tmp_path / "only.jpg").write_bytes(b"frame")
    camera = MockCamera(stills_dir=tmp_path)

    assert camera.get_snapshot() == b"frame"
