"""Entry point for the `sentinel-admin` command.

Currently just `set-pin`, which prints an Argon2 hash to paste into
config/sentinel.toml. The PIN is prompted for interactively and never
accepted as an argument, so it never appears in shell history
(AGENTS.md section 4.6).
"""

import argparse
import getpass
import sys

from sentinel.services import hash_pin


def main() -> None:
    parser = argparse.ArgumentParser(prog="sentinel-admin")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "set-pin", help="Generate an Argon2 hash for the arm/disarm PIN"
    )

    args = parser.parse_args()
    if args.command == "set-pin":
        _set_pin()


def _set_pin() -> None:
    pin = getpass.getpass("New PIN: ")
    confirm = getpass.getpass("Confirm PIN: ")
    if not pin:
        print("PIN must not be empty.", file=sys.stderr)
        raise SystemExit(1)
    if pin != confirm:
        print("PINs did not match.", file=sys.stderr)
        raise SystemExit(1)

    print("\nAdd this to config/sentinel.toml under [auth]:\n")
    print(f'pin_hash = "{hash_pin(pin)}"')


if __name__ == "__main__":
    main()
