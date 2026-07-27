"""Nested Settings model and TOML loader.

AGENTS.md section 8.1: every threshold, timeout, path, and volume in the
codebase is a config key, validated at startup. A bad value must exit
with a readable message, never a stack trace — `load_settings` raises
`ConfigError` with that message and leaves turning it into a process
exit to the caller (see `sentinel.cli`).
"""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from sentinel.config.errors import ConfigError


class SystemSettings(BaseModel):
    """Process-level bind address and locale."""

    host: str = "127.0.0.1"
    port: int = Field(default=8000, gt=0, le=65535)
    timezone: str = "UTC"

    @model_validator(mode="after")
    def _reject_all_interfaces(self) -> "SystemSettings":
        if self.host == "0.0.0.0":
            raise ValueError(
                "must not be 0.0.0.0; bind explicitly to the LAN interface "
                "(AGENTS.md section 4.6)"
            )
        return self


class AuthSettings(BaseModel):
    """Server-side PIN auth. The PIN itself never appears here, only its hash."""

    pin_hash: str = Field(min_length=1)
    session_ttl_seconds: int = Field(default=900, gt=0)
    max_attempts: int = Field(default=5, gt=0)
    lockout_seconds: int = Field(default=300, gt=0)


class CameraSettings(BaseModel):
    """Camera provider selection. RTSP URLs are required only for the real provider."""

    provider: Literal["mock", "rtsp"] = "mock"
    main_stream_url: str = ""
    substream_url: str = ""
    # None means "use the stills bundled with sentinel/camera/stills/".
    # Point this at a real directory to preview with your own test images.
    mock_stills_dir: Path | None = None

    @model_validator(mode="after")
    def _require_urls_for_rtsp(self) -> "CameraSettings":
        missing = not self.main_stream_url or not self.substream_url
        if self.provider == "rtsp" and missing:
            raise ValueError(
                "main_stream_url and substream_url are required when provider is 'rtsp'"
            )
        return self


class DetectionSettings(BaseModel):
    """Detection debouncer thresholds. See AGENTS.md section 4.4."""

    provider: Literal["mock", "onnx"] = "mock"
    model_path: str = "models/yolov8n.onnx"
    confidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    consecutive_frames: int = Field(default=3, ge=1)
    absence_seconds: float = Field(default=8.0, gt=0)
    min_box_area_ratio: float = Field(default=0.01, ge=0.0, le=1.0)
    max_inference_fps: float = Field(default=3.0, gt=0)


class AudioSettings(BaseModel):
    """Announcement playback via aplay/amixer (DECISIONS.md 0012)."""

    provider: Literal["mock", "device"] = "mock"
    device: str = "default"
    mixer_control: str = "Master"
    warning_volume: float = Field(default=0.5, ge=0.0, le=1.0)
    escalated_volume: float = Field(default=1.0, ge=0.0, le=1.0)
    warning_clip_path: Path = Path("sounds/warning.wav")
    escalated_clip_path: Path = Path("sounds/escalated.wav")


class StateSettings(BaseModel):
    """Escalation ladder timer durations. Not specified in AGENTS.md section
    8.1's required-sections list; added in slice 4 to close a real gap — the
    transition table's GraceExpired/WarningExpired/CooldownExpired timers
    need a duration from somewhere, and "no magic numbers" (section 8.1)
    rules out hardcoding it. See DECISIONS.md 0011.
    """

    grace_seconds: float = Field(default=10.0, gt=0)
    warning_seconds: float = Field(default=30.0, gt=0)
    cooldown_seconds: float = Field(default=60.0, gt=0)


class StorageSettings(BaseModel):
    """Recording/snapshot retention. No default path: must be explicit (section 4.8)."""

    recordings_path: Path
    retention_days: int = Field(default=14, ge=1)
    max_gb: float = Field(default=50.0, gt=0)


class DatabaseSettings(BaseModel):
    """SQLite database location."""

    path: Path = Path("data/sentinel.db")


class DashboardSettings(BaseModel):
    """Server-rendered dashboard behavior.

    property_address and response_units are lock-screen display copy,
    not operational thresholds — but they're still deployment-specific
    (a home address), so they default empty rather than shipping a
    placeholder in the example config that someone might forget to
    change. The lock screen hides those blocks entirely when empty.
    """

    snapshot_poll_interval_ms: int = Field(default=1000, gt=0)
    status_poll_interval_ms: int = Field(default=2000, gt=0)
    property_address: str = ""
    response_units: list[str] = Field(default_factory=list)


class LoggingSettings(BaseModel):
    """Structured logging output."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_format: bool = False


class Settings(BaseSettings):
    """Root configuration. One field per required section (AGENTS.md section 8.1)."""

    model_config = SettingsConfigDict(
        env_prefix="SENTINEL__",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )

    system: SystemSettings = SystemSettings()
    auth: AuthSettings
    camera: CameraSettings = CameraSettings()
    detection: DetectionSettings = DetectionSettings()
    audio: AudioSettings = AudioSettings()
    state: StateSettings = StateSettings()
    storage: StorageSettings
    database: DatabaseSettings = DatabaseSettings()
    dashboard: DashboardSettings = DashboardSettings()
    logging: LoggingSettings = LoggingSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # The TOML file is passed in as init kwargs by load_settings(); putting
        # env_settings first means SENTINEL__ environment variables override it.
        return env_settings, init_settings


def load_settings(config_path: Path) -> Settings:
    """Load, merge, and validate configuration from a TOML file.

    Environment variables prefixed `SENTINEL__` with double-underscore
    nesting (e.g. `SENTINEL__AUTH__MAX_ATTEMPTS`) override the file.
    Raises `ConfigError` with a readable message on any failure; never
    lets a `tomllib` or pydantic exception escape.
    """
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as handle:
            toml_data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{config_path} is not valid TOML: {exc}") from exc

    try:
        return Settings(**toml_data)
    except ValidationError as exc:
        raise ConfigError(_format_validation_error(config_path, exc)) from exc


def _format_validation_error(config_path: Path, exc: ValidationError) -> str:
    lines = [f"Invalid configuration in {config_path}:"]
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        lines.append(f"  {location}: {error['msg']}")
    return "\n".join(lines)
