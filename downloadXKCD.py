#!./downloadXKCD_env/Scripts/python
# ^ sets script to run in virtual environment inside project directory.
# downloadXkcd.py - Downloads every single XKCD comic.
# version 1.1.3.dev1
"""
Webscraper that downloads xkcd comics.
Checks if comic already downloaded so for increased efficiency on rerun.

Two run modess: Full and Quick
Full mode goes through every comic.
Quick mode quits when it reaches the first comic that is already downloaded.

Feature updates - multithreading, max 100 comics/thread.
To implement dual modes required iterating backwards through the comics in
each thread until already downloaded comic found.

Planned:
    - change to use JSON data, rather than downloading page for each comic:
        - response = requests.get('http://xkcd.com/comic#(eg1905)/info.0.json')
        - json.loads(response.text) <- returns a dict with the info

    - feature update where title text is in properties of downloaded image.

    - feature update implement counts to provide feedback as to how many
        comics downloaded in current run.

    - implement if __name__ == "__main__":
        - use a second script, run with a command line argument for Quick/Full
        - will display "downloading comic x" or error messages, sans input text
        - ability to run via another script, or use separate background process
            by default

    - Implement a GUI.

    - Check to see if archive folder already exists,
        - give option to set location/name for new folder
        - Use datafile/mod to script itself(?) to default to an existing folder

        - Implement logging
        - per run, eg performance/runtime, comics downloaded
        - errors

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

1.1.3 changes:
    implement json

Derived from original project: https://automatetheboringstuff.com/chapter11/

@author: david.antonini // toonarmycaptain
"""

__version__ = '1.1.3.dev1'

import time
import os
import string
import sys
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

    returns: int
    """
    while True:
        try:
            print('Please select mode:\n'
                  'Enter 0 for Quick mode, or 1 for Full Mode')
            run_mode_selection = input('Mode: ')
            if int(run_mode_selection) == 0:
                return False  # Quick mode
                break
            if int(run_mode_selection) == 1:
                return True    # Full mode
                break
        except ValueError:
            continue


def download_image(session, comic_url, filename):
    """
    Download the image file.

    Args:
        session (class 'requests.sessions.Session'): the Session object.
        comic_url (str): String containing the image url.
        filename (str): String of the filename to save the image to.
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
    try:
        return requests.get('https://xkcd.com/'+str(comic_number)+'/info.0.json').json()
    except:
        print(comic_number)


def punct_stripper():
    return str.maketrans('', '', string.punctuation)

def threaded_download(comic_start, comic_end, direction, run_mode):
    """
    Iterate over comic numbers, download comic page, find comic image, check if
    file with comic name already exists, if not, download comic image.

    Args:
        comic_start (int): the number of the first comic thread iterates over.
        comic_end (int): the number of the last comic thread iterates over.
        direction (int): 1 or -1 iterating forwards or backwards based on mode.
        run_mode (bool): the run mode - True for full, False for quick.

    Returns: None
    """
    with requests.Session() as session:
        for comic_number in range(comic_start, comic_end, direction):
            if comic_number == 404:
                continue
            try:
                comic = comic_json(comic_number)  # get comic json data
                title_cleaner = punct_stripper()
                clean_title = comic['safe_title'].translate(title_cleaner)
                if not clean_title.isalpha():
                    clean_title = os.path.basename(comic['img'])
                assert comic_number == comic['num']
                base_url, file_type = os.path.splitext(comic['img'])
                download_image(
                        session,
                        comic['img'],
                        f"{comic['num']} - {clean_title}{file_type}")
            except FileExistsError:
                # print(f'--- Comic {url_number} already downloaded.---')
                if run_mode:  # Full mode
                    continue  # skip this comic
                if not run_mode:
                    # print(f'Finished updating archive, '
                    #       f'comics {comic_start}-{comic_end}.')
                    break



def download_comics(run_mode):
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
    for i in range(1, latest_comic-100, 100):
        if run_mode:
            download_thread = threading.Thread(
                    target=threaded_download,
                    args=(i, i+100, 1, run_mode))
        if not run_mode:  # quick mode iterates back until pre-existing file
            download_thread = threading.Thread(
                    target=threaded_download,
                    args=(i+100, i, -1, run_mode))
        download_threads.append(download_thread)
        download_thread.start()
    if run_mode:
        download_thread = threading.Thread(
                target=threaded_download,
                args=(latest_comic-100, latest_comic+1, 1, run_mode))
    if not run_mode:
        download_thread = threading.Thread(
                target=threaded_download,
                args=(i+100, latest_comic-1, -1, run_mode))
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
          '\nQuick mode: Or "refresh mode", checked until it finds '
          'a previously downloaded comic.\n'
          ' Full mode: Checks for every comic, '
          'downloads undownloaded comics.\n'
          )

    run_mode = run_mode()  # Prompt user to set run_mode

    download_comics(run_mode)  # Download the comics

    print('Done.')
