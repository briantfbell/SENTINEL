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


def test_main_serves_the_app_on_valid_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = tmp_path / "sentinel.toml"
    config_path.write_text(
        f'[auth]\npin_hash = "x"\n\n'
        f'[storage]\nrecordings_path = "{tmp_path / "recordings"}"\n\n'
        f'[database]\npath = "{tmp_path / "sentinel.db"}"\n'
    )
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)
    serve_calls: list[tuple[object, str, int]] = []
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app, host, port: serve_calls.append((app, host, port)),
    )

    main()

    output = capsys.readouterr().out
    assert "Configuration loaded" in output
    assert "Serving on http://127.0.0.1:8000" in output
    assert len(serve_calls) == 1
    assert serve_calls[0][1:] == ("127.0.0.1", 8000)


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
