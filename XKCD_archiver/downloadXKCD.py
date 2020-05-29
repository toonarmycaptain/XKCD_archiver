#!./downloadXKCD_env/Scripts/python
"""
downloadXKCD.py - Downloads every single XKCD comic.
"""
from XKCD_archiver.downloader import Downloader

__version__ = '2.0.0'

import sys
import time


def is_venv() -> bool:
    """
    Test if successfully running inside virtualenv.

    returns: bool
    """
    return (hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def run_mode_selector() -> bool:
    """
    Asks user to decide whether to run in quick/update or full mode.
    Returns True for full mode, False for quick/update

    Returns: bool
    """
    while True:

        print('Please select mode:\n'
              'Enter 0 for Quick mode, or 1 for Full Mode.\n'
              'Or enter Q to exit.')
        run_mode_selection = input('Mode: ')

        if run_mode_selection == '0':
            return False  # Quick mode

        elif run_mode_selection == '1':
            return True  # Full mode

        elif run_mode_selection.lower() == 'q':
            return sys.exit()


def timed_run(downloader: Downloader) -> None:
    start = time.time()

    downloader.download_comics()

    time_total = time.time() - start
    if time_total > 60:
        mins = time_total // 60
        sec = time_total - mins * 60
        print(f"Runtime: {mins:.0f} minutes, {sec:.2f} seconds")
    else:
        print(f"Runtime: {time_total:.2f} seconds")


def script_tagline() -> None:
    print('This script searches xkcd.com and downloads each comic.')


def env_indicator() -> None:
    if is_venv():
        print('This script is running in its own virtualenv.')
    else:
        print('Script running outside virtualenv or venv')


def select_mode() -> bool:
    print('There are two mode options:\n'
          '\nQuick mode: Or "refresh mode", iterates backwards over latest '
          '100 comics until it finds a previously downloaded comic.\n'
          ' Full mode: Checks every comic, downloads undownloaded comics.\n'
          )

    return run_mode_selector()  # Prompt user to set run_mode


def cli_run() -> None:
    script_tagline()

    # Test if successfully running in virtualenv
    env_indicator()

    # User input for full run or until finding already downloaded comic.
    mode = select_mode()

    downloader = Downloader(mode)

    # Run downloader inside a timing wrapper.
    timed_run(downloader)

    print('Done.')


if __name__ == "__main__":
    cli_run()
