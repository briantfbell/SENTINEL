from pathlib import Path

import pytest

import sentinel.cli as cli
from sentinel import __version__
from sentinel.cli import main


def test_main_prints_version_banner(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert "Sentinel" in captured.out


def test_main_runs_with_no_config_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", tmp_path / "sentinel.toml")

    main()

    assert "No config at" in capsys.readouterr().out


def test_main_confirms_valid_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "sentinel.toml"
    config_path.write_text(
        '[auth]\npin_hash = "x"\n\n[storage]\nrecordings_path = "data"\n'
    )
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)

    main()

    assert "Configuration loaded" in capsys.readouterr().out


def test_main_exits_on_invalid_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "sentinel.toml"
    config_path.write_text("not = [valid")
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "Configuration error" in capsys.readouterr().err
