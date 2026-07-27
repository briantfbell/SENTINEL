from pathlib import Path

import pytest

from sentinel.config import Settings
from sentinel.services import hash_pin

TEST_PIN = "1234"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        auth={"pin_hash": hash_pin(TEST_PIN), "max_attempts": 3, "lockout_seconds": 5},
        storage={"recordings_path": tmp_path / "recordings"},
        database={"path": tmp_path / "sentinel.db"},
        state={
            "grace_seconds": 0.01,
            "warning_seconds": 0.01,
            "cooldown_seconds": 0.01,
        },
    )
