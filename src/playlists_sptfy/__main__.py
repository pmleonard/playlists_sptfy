"""Entry point for `python -m playlists_sptfy`."""

from __future__ import annotations

import argparse

from .main import load_settings
from .main import main as run_pipeline


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="playlists-sptfy")
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate settings/config files and exit.",
    )
    args = parser.parse_args(argv)

    if args.validate_config:
        load_settings()
        print("Configuration is valid.")
        return 0

    run_pipeline()
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
