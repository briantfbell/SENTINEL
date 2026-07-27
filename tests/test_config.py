from pathlib import Path

import pytest

from sentinel.config import ConfigError, load_settings

VALID_TOML = """
[auth]
pin_hash = "argon2-placeholder-hash"

[storage]
recordings_path = "data/recordings"
"""


def _write(tmp_path: Path, content: str) -> Path:
    config_path = tmp_path / "sentinel.toml"
    config_path.write_text(content)
    return config_path


def test_valid_config_loads_with_defaults(tmp_path: Path) -> None:
    settings = load_settings(_write(tmp_path, VALID_TOML))

    assert settings.auth.pin_hash == "argon2-placeholder-hash"
    assert settings.storage.recordings_path == Path("data/recordings")
    assert settings.detection.confidence_threshold == 0.55
    assert settings.dashboard.snapshot_poll_interval_ms == 1000


def test_example_config_loads() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    load_settings(repo_root / "config" / "sentinel.example.toml")


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "does-not-exist.toml")


def test_missing_required_section_raises_readable_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="storage"):
        load_settings(_write(tmp_path, '[auth]\npin_hash = "x"\n'))


def test_bad_toml_syntax_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_settings(_write(tmp_path, "not = [valid"))


def test_out_of_range_value_raises_readable_error(tmp_path: Path) -> None:
    bad = VALID_TOML + "\n[detection]\nconfidence_threshold = 1.5\n"
    with pytest.raises(ConfigError, match="confidence_threshold"):
        load_settings(_write(tmp_path, bad))


def test_wildcard_host_is_rejected(tmp_path: Path) -> None:
    bad = VALID_TOML + '\n[system]\nhost = "0.0.0.0"\n'
    with pytest.raises(ConfigError, match="0.0.0.0"):
        load_settings(_write(tmp_path, bad))


def test_rtsp_provider_requires_stream_urls(tmp_path: Path) -> None:
    bad = VALID_TOML + '\n[camera]\nprovider = "rtsp"\n'
    with pytest.raises(ConfigError, match="main_stream_url"):
        load_settings(_write(tmp_path, bad))


def test_env_var_overrides_toml_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL__AUTH__MAX_ATTEMPTS", "3")
    settings = load_settings(_write(tmp_path, VALID_TOML))

    assert settings.auth.max_attempts == 3
    # Unrelated fields in the same section still come from the file.
    assert settings.auth.pin_hash == "argon2-placeholder-hash"
