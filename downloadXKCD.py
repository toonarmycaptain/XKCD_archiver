#!./downloadXKCD_env/Scripts/python
# ^ sets script to run in virtual environment inside project directory.
# downloadXKCD.py - Downloads every single XKCD comic.
# Version 1.0
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
        - use a second script, run with a command line arguement for Quick/Full
        - will display "downloading comic x" or error messages, sans imput text
        - ability to run via another script, or use separate backgorund process
            by default

    - Implement a GUI.

    - Check to see if archive folder already exists,
        - give option to set location/name for new folder
        - Use datafile/mod to script itself(?) to default to an existing folder



Derived from original project: https://automatetheboringstuff.com/chapter11/

@author: david.antonini // toonarmycaptain
"""

__version__ = '1.0'

import time
import os
import threading

import requests
import bs4


print('This script searches xkcd.com and downloads each comic.')

# Test if successfully running in virtualenv
import sys


def is_venv():
    return (hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


if is_venv():
    print('This script is running in its own virtualenv.')
else:
    print('outside virtualenv or venv')

# User input for full run or until finding already downloaded comic.
print('There are two mode options:\n'
      '\nQuick mode: Or "refresh mode", checked until it finds '
      'a previously downloaded comic.\n'
      ' Full mode: Checks for every comic, downloads undownloaded comics.\n'
      )

while True:
    try:
        print('Please select mode:\n'
              'Enter 0 for Quick mode, or 1 for Full Mode')
        run_mode_selection = input('Mode: ')
        if int(run_mode_selection) == 0:
            run_mode = False  # Quick mode
            break
        if int(run_mode_selection) == 1:
            run_mode = True  # Full mode
            break
    except ValueError:
        continue

start = time.time()

os.makedirs('xkcd', exist_ok=True)  # store comics in ./xkcd


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
        print(f'Downloading image {comic_url}...')

        for chunk in res.iter_content(100000):
            image_file.write(chunk)


#    image_file.close()

# TODO: Needs feature update where title text
#       is in properties of downloaded image.


def download_xkcd(comic_start, comic_end, direction):
    """
    Iterate over comic numbers, download comic page, find comic image, check if
    file with comic name already exists, if not, download comic image.

    Args:
        comic_start (int): the number of the first comic thread iterates over.
        comic_end (int): the number of the last comic thread iterates over.
        direction (int): 1 or -1 iterating forwards or backwards based on mode.
    """
    with requests.Session() as session:
        for url_number in range(comic_start, comic_end, direction):
            try:
                res = session.get(f'http://xkcd.com/{url_number}')
                res.raise_for_status()
                soup = bs4.BeautifulSoup(res.text, 'lxml')
            except requests.exceptions.HTTPError:
                continue
            # Find the URL of the comic image.
            comic_image = soup.select_one('#comic img[src]')
            if not comic_image:
                print(f'Could not find comic image {url_number}.')
                continue

            try:
                comic_url = 'https:' + comic_image['src']
                download_image(session, comic_url,
                               f'{url_number} - {os.path.basename(comic_url)}')
            except requests.exceptions.MissingSchema:
                print(f'--- Missing comic {url_number}.---')
                continue  # skip this comic
            except FileExistsError:
                # print(f'--- Comic {url_number} already downloaded.---')
                if run_mode:  # Full mode
                    continue  # skip this comic
                if not run_mode:
                    # print(f'Finished updating archive, '
                    #       f'comics {comic_start}-{comic_end}.')
                    break


# Get latest comic number:
url = 'https://xkcd.com'
res = requests.get(url)
res.raise_for_status()
soup = bs4.BeautifulSoup(res.text, 'lxml')
penultimate_comic = soup.select('a[rel="prev"]')[0]
# penultimate Comic +1 for most recent comic
latest_comic = int(penultimate_comic.get('href')[1:-1]) + 1

# Create and start the Thread objects.
download_threads = []  # a list of all the Thread objects
for i in range(0, latest_comic, 100):
    if run_mode:
        download_thread = threading.Thread(target=download_xkcd,
                                           args=(i, i + 100, 1))
    if not run_mode:  # quick mode iterates back until pre-existing file
        download_thread = threading.Thread(target=download_xkcd,
                                           args=(i + 100, i, -1))
    download_threads.append(download_thread)
    download_thread.start()

# Wait for all threads to end.
for download_thread in download_threads:
    download_thread.join()

print('Done.')

timetotal = time.time() - start
if timetotal > 60:
    mins = timetotal // 60
    sec = timetotal - mins * 60
    print(f"Runtime: {mins:.0f} minutes, {sec:.2f} seconds")
else:
    print(f"Runtime: {timetotal:.2f} seconds")

# TODO:
# implement if __name__ == "__main__":
#     execute only if run as a script
#     pass 0/1//True/False for run mode via main(mode)?
#     main(mode)
