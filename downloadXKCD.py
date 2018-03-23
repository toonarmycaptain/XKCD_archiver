#!./downloadXKCD_env/Scripts/python
# ^ sets script to run in virtual environment inside project directory.
# downloadXKCD.py - Downloads every single XKCD comic.
# version 1.2.1.devl
"""
Webscraper that downloads xkcd comics.
Uses multithreading, checks if comic already downloaded for increased
    efficiency on rerun.

Two run modess: Full and Quick
Full mode goes through every comic.
Quick mode checked latest 100 comics, quits when it reaches the
    first comic that is already downloaded.


1.1.0 changes:
    - implemented relative path for virtualenv
    - typos fixed: 'imput,' 'arguement,' 'backgorund' in docstring

1.1.1 changes:
    - refactored to run as import module/implemented if __name__ == "__main__":
    - added function documentation
    - print "Downloading image...." only in quick mode.

1.1.2 changes:
    - changed venv not activated text, prefixed with "Script running "
    - explicitly pass variables
        (depreciating use of globals aids import functionality)

1.2.0 changes:
    - implement json

1.2.1 changes:
    - refactored thread setup to separate quick/full modes
    - depreciate json title use in filename.
        revert to using file names from json as filename to save image
    - quick mode only downloads last 100 comics
    - modified run_mode to eliminate try/except necessity,
        added Q to quit option.
    - made default parameter download_comics: run_mode=True
        (for potential future use)
    - removed unused latest_comic param from comic_json

    - #TODO add press x to exit for if __name__ == '__main__' script

    - #TODO: fix documentation all functions


Derived from original project: https://automatetheboringstuff.com/chapter11/

@author: david.antonini // toonarmycaptain
"""

__version__ = '1.2.1.dev1'

import os
import string
import sys
import time
import threading

import requests


def is_venv():
    """
    Test if successfully running inside virtualenv.

    returns: bool
    """
    return (hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def run_mode():
    """
    Asks user to decide whether to run in quick/update or full mode.
    Returns True for full mode, False for quick/update

    Returns: int
    """
    while True:

        print('Please select mode:\n'
              'Enter 0 for Quick mode, or 1 for Full Mode.\n'
              'Or enter Q to exit.')
        run_mode_selection = input('Mode: ')

        if run_mode_selection == '0':
            return False  # Quick mode

        elif run_mode_selection == '1':
            return True    # Full mode

        elif run_mode_selection.lower() == 'q':
            return sys.exit()


def download_image(session, comic_url, filename):
    """
    Download the image file.

    Args:
        session (class 'requests.sessions.Session'): the Session object.
        comic_url (str): String containing the image url.
        filename (str): String of the filename to save the image to.

    Returns: None
    """
    # print(f'Downloading page http://xkcd.com/{url_number}...')

    res = session.get(comic_url)
#    res.raise_for_status()

    with open(os.path.join('xkcd', filename), 'xb') as image_file:
        if not run_mode:
            print(f'Downloading image {comic_url}...')

        for chunk in res.iter_content(100000):
            image_file.write(chunk)

    # TODO: Needs feature update where title text
    #       is in properties of downloaded image.


def comic_json(comic_number):
    """
    """
    return requests.get(
            'https://xkcd.com/'+str(comic_number)+'/info.0.json').json()


def set_comic_filename(comic):
    """
    Factored out to provide for future optional naming features.

    Args:
        comic (dict): json data from comic.

    Returns: str
    """
    return f"{comic['num']} - {os.path.basename(comic['img'])}"


def punct_stripper():
    return str.maketrans('', '', string.punctuation)


def threaded_download(comic_start, comic_end, run_mode, latest_comic):
    """
    Iterate over comic numbers, download comic page, find comic image, check if
    file with comic name already exists, if not, download comic image.

    Args:
        comic_start (int): the number of the first comic thread iterates over.
        comic_end (int): the number of the last comic thread iterates over.

        run_mode (bool): the run mode - True for full, False for quick.
        latest_comic (int): latest comic number
    Returns: None
    """

    if run_mode:
        direction = 1
    if not run_mode:
        direction = -1

    with requests.Session() as session:
        for comic_number in range(comic_start, comic_end, direction):
            if comic_number == 404:
                continue
            if comic_number == latest_comic+1:
                break
            try:
                comic = comic_json(comic_number)
                assert comic_number == comic['num']
                filename = set_comic_filename(comic)
                download_image(session, comic['img'], filename)

            except FileExistsError:
#                print(f'--- Comic {comic_number} already downloaded.---')
                if run_mode:  # Full mode
                    continue  # skip this comic
                if not run_mode:
#                    print(f'Finished updating archive, '
#                          f'comics {comic_start}-{comic_end+1}.')
                    break


def download_comics(run_mode=True):
    """
    Starts a number of threads based on the total number of comics.
    Executes download code inside each thread on 100 comics each.
    Times execution.

    Args:
        run_mode (bool): Sets run_mode quick/full.

    returns: None
    """
    start = time.time()

    os.makedirs('xkcd', exist_ok=True)   # store comics in ./xkcd

    # Get latest comic number:
    url = 'https://xkcd.com/info.0.json'
    latest_data = requests.get(url).json()
    latest_comic = latest_data['num']

    # Create and start the Thread objects.
    download_threads = []  # a list of all the Thread objects
    if run_mode:
        for i in range(1, latest_comic+1, 100):
            download_thread = threading.Thread(
                    target=threaded_download,
                    args=(i, i+100, run_mode, latest_comic))
            download_threads.append(download_thread)
            download_thread.start()
    if not run_mode:  # 10 threads of 10
        for i in range(latest_comic-100, latest_comic, 10):
            download_thread = threading.Thread(
                    target=threaded_download,
                    args=(i+10, i, run_mode, latest_comic))
            download_threads.append(download_thread)
            download_thread.start()

    # Wait for all threads to end.
    for download_thread in download_threads:
        download_thread.join()

    timetotal = time.time() - start
    if timetotal > 60:
        mins = timetotal//60
        sec = timetotal-mins*60
        print(f"Runtime: {mins:.0f} minutes, {sec:.2f} seconds")
    else:
        print(f"Runtime: {timetotal:.2f} seconds")


if __name__ == "__main__":

    print('This script searches xkcd.com and downloads each comic.')

    # Test if successfully running in virtualenv
    if is_venv():
        print('This script is running in its own virtualenv.')
    else:
        print('Script running outside virtualenv or venv')

    # User input for full run or until finding already downloaded comic.
    print('There are two mode options:\n'
          '\nQuick mode: Or "refresh mode", iterates backwards over latest '
          '100 comics until it finds a previously downloaded comic.\n'
          ' Full mode: Checks every comic, downloads undownloaded comics.\n'
          )

    run_mode = run_mode()  # Prompt user to set run_mode

    download_comics(run_mode)  # Download the comics

    print('Done.')
