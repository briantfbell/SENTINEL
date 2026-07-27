"""Entry point for the `sentinel` command.

This is the process the systemd unit and `docker compose` both launch.
Startup wiring (config load, composition root, uvicorn server) is added
slice by slice; today it only proves the package installs and runs.
"""

from sentinel import __version__


def main() -> None:
    """Print the version banner.

    Serves as the slice 0 acceptance check: a fresh checkout can be
    installed and run without any hardware, network, or config present.
    """
    print(f"Sentinel v{__version__} — local-first home monitoring and deterrence")


if __name__ == "__main__":
    main()
