"""Entry point for the `sentinel` command.

This is the process the systemd unit and `docker compose` both launch.
"""

import sys
from pathlib import Path

import uvicorn

from sentinel import __version__
from sentinel.api import create_app
from sentinel.config import ConfigError, load_settings
from sentinel.services import build_container

DEFAULT_CONFIG_PATH = Path("config/sentinel.toml")


def main() -> None:
    """Print the version banner, validate config, then serve the dashboard.

    A fresh checkout has no `config/sentinel.toml` (it's gitignored), so
    running with none is not an error — that's rule 3 in AGENTS.md, the
    repository is always runnable; it just doesn't serve anything yet. A
    config file that fails validation exits with a readable message and
    status 1, never a traceback.
    """
    print(f"Sentinel v{__version__} — local-first home monitoring and deterrence")

    if not DEFAULT_CONFIG_PATH.is_file():
        print(
            f"No config at {DEFAULT_CONFIG_PATH}; "
            "copy config/sentinel.example.toml to get started."
        )
        return

    try:
        settings = load_settings(DEFAULT_CONFIG_PATH)
    except ConfigError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Configuration loaded from {DEFAULT_CONFIG_PATH}")

    container = build_container(settings)
    app = create_app(container)
    print(f"Serving on http://{settings.system.host}:{settings.system.port}")
    uvicorn.run(app, host=settings.system.host, port=settings.system.port)


if __name__ == "__main__":
    main()
