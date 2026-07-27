"""Entry point for the `sentinel` command.

This is the process the systemd unit and `docker compose` both launch.
Full startup wiring (composition root, uvicorn server) is added slice by
slice; today it proves the package installs, runs without a config file
present, and never lets a bad config value surface as a stack trace.
"""

import sys
from pathlib import Path

from sentinel import __version__
from sentinel.config import ConfigError, load_settings

DEFAULT_CONFIG_PATH = Path("config/sentinel.toml")


def main() -> None:
    """Print the version banner, then validate config if one is present.

    A fresh checkout has no `config/sentinel.toml` (it's gitignored), so
    running with none is not an error — that's rule 3 in AGENTS.md, the
    repository is always runnable. A config file that fails validation
    exits with a readable message and status 1, never a traceback.
    """
    print(f"Sentinel v{__version__} — local-first home monitoring and deterrence")

    if not DEFAULT_CONFIG_PATH.is_file():
        print(
            f"No config at {DEFAULT_CONFIG_PATH}; "
            "copy config/sentinel.example.toml to get started."
        )
        return

    try:
        load_settings(DEFAULT_CONFIG_PATH)
    except ConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Configuration loaded from {DEFAULT_CONFIG_PATH}")


if __name__ == "__main__":
    main()
