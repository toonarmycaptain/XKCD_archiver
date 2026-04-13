"""
downloadXKCD.py - Downloads every single XKCD comic.
"""

import argparse
import sys
import time
from pathlib import Path

from XKCD_archiver.downloader import Downloader

__version__ = "3.2.0"


def is_venv() -> bool:
    """
    Test if successfully running inside virtualenv.

    returns: bool
    """
    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def run_mode_selector() -> str:
    """
    Asks user to decide whether to run in quick/update or full mode.

    Returns: "full" or "quick"
    """
    while True:
        print("Please select mode:\nEnter 0 for Quick mode, or 1 for Full Mode.\nOr enter Q to exit.")
        run_mode_selection = input("Mode: ")

        if run_mode_selection == "0":
            return "quick"

        elif run_mode_selection == "1":
            return "full"

        elif run_mode_selection.lower() == "q":
            return sys.exit()


def timed_run(downloader: Downloader, mode: str) -> None:
    start = time.time()

    downloader.download_comics(mode=mode)

    time_total = time.time() - start
    if time_total > 60:
        mins = time_total // 60
        sec = time_total - mins * 60
        print(f"Runtime: {mins:.0f} minutes, {sec:.2f} seconds")
    else:
        print(f"Runtime: {time_total:.2f} seconds")


def script_tagline() -> None:
    print("This script searches xkcd.com and downloads each comic.")


def env_indicator() -> None:
    if is_venv():
        print("This script is running in its own virtualenv.")
    else:
        print("Script running outside virtualenv or venv")


def select_mode() -> str:
    print(
        "There are two mode options:\n"
        '\nQuick mode: Or "refresh mode", checks the latest '
        "100 comics and downloads any missing.\n"
        " Full mode: Checks every comic, downloads undownloaded comics.\n"
    )

    return run_mode_selector()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Downloads every single XKCD comic.")
    parser.add_argument("--mode", "-m", choices=["quick", "full"], help="Download mode (interactive if omitted)")
    parser.add_argument("--output", "-o", type=Path, default=Path("xkcd"), help="Output directory (default: xkcd)")
    parser.add_argument("--workers", "-w", type=int, default=10, help="Number of concurrent workers (default: 10)")
    return parser.parse_args(argv)


def cli_run(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    script_tagline()
    env_indicator()

    mode = args.mode if args.mode else select_mode()

    downloader = Downloader(output_dir=args.output, max_workers=args.workers)

    timed_run(downloader, mode)

    print("Done.")


if __name__ == "__main__":
    cli_run()
