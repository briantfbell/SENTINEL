import pytest

from sentinel import __version__
from sentinel.cli import main


def test_main_prints_version_banner(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert "Sentinel" in captured.out
