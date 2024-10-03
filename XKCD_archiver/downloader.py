""" Downloader class """

from pathlib import Path
import threading

import requests

from typing import (Dict,
                    List,
                    Optional,
                    )


class Downloader:
    """
    Class that downloads XKCD comics.
    ...
    Attributes
    ----------
    run_mode : bool
        Determines whether full archive is run, or the most recent 100 comics.
    latest_comic_number : int
        Cleaned string safe to use in file names and paths.
    _download_threads : list[threading.Thread]
        Internal list of threads.

    """

    def __init__(self,
                 run_mode: bool=True) -> None:
        self.run_mode: bool = run_mode

        self.latest_comic_number: int
        self._download_threads: List[threading.Thread]

    def _download_image(self, session: requests.sessions.Session, comic_url: str, filename: Path) -> None:
        """
        Download the image file.

        Args:
            session (class 'requests.sessions.Session'): the Session object.
            comic_url (str): String containing the image url.
            filename (str): String of the filename to save the image to.

        Returns: None
        """
        # print(f'Downloading page http://xkcd.com/{url_number}...')

        response = session.get(comic_url)
        if response.status_code != 200:
            # At present two comics - 1608 and 1668 don't have an image - 403
            # and 404 returns 404.
            # Is there a better way to handle this, in case there are redirects etc?
            return None

        with open(Path('xkcd', filename), 'xb') as image_file:
            if not self.run_mode:
                print(f'Downloading image {comic_url}...')

            for chunk in response.iter_content(100000):
                image_file.write(chunk)

        # TODO: Needs feature update where title text
        #       is in properties of downloaded image.

    def _get_comic_json(self, session: requests.sessions.Session, comic_number: int) -> Optional[Dict]:
        """
        """
        response = session.get(
            'https://xkcd.com/' + str(comic_number) + '/info.0.json')
        if response.status_code != 200:
            # handle
            return None
        return response.json()

    def _set_comic_filename(self, comic: dict) -> Path:
        """
        Factored out to provide for future optional naming features.

        Args:
            comic (dict): json data from comic.

        Returns: str
        """
        return Path(f"{comic['num']}-{Path(comic['img']).name}")

    def _threaded_download(self, comic_start: int, comic_end: int) -> None:
        """
        Iterate over comic numbers, download comic page, find comic image, check if
        file with comic name already exists, if not, download comic image.

        Args:
            comic_start (int): the number of the first comic thread iterates over.
            comic_end (int): the number of the last comic thread iterates over.

        Returns: None
        """

        if not self.run_mode:
            direction = -1
            # Reverse direction requires reversing start/end
            comic_start, comic_end = comic_end, comic_start
        else:
            direction = 1

        with requests.Session() as session:
            for comic_number in range(comic_start, comic_end, direction):
                if comic_number == self.latest_comic_number + 1:
                    break
                try:
                    self._download_comic(session, comic_number)
                except FileExistsError:
                    # print(f'--- Comic {comic_number} already downloaded.---')
                    if self.run_mode:  # Full mode
                        continue  # skip this comic
                    if not self.run_mode:
                        # print(f'Finished updating archive, '
                        #       f'comics {comic_start}-{comic_end+1}.')
                        break

    def _download_comic(self, session: requests.sessions.Session, comic_number: int) -> None:
        comic = self._get_comic_json(session, comic_number)
        if comic:
            assert comic_number == comic['num']
            filename = self._set_comic_filename(comic)
            if not filename.exists():
                self._download_image(session, comic['img'], filename)

    def _get_latest_comic(self) -> int:
        url = 'https://xkcd.com/info.0.json'
        latest_data = requests.get(url).json()
        return latest_data['num']

    def download_comics(self, set_run_mode: Optional[bool] = None) -> None:
        """
        Starts a number of threads based on the total number of comics.
        Executes download code inside each thread on 100 comics each.
        Times execution.

        Args:
            set_run_mode (bool): Sets run_mode quick/full.

        returns: None
        """
        if set_run_mode is not None:
            run_mode = set_run_mode
        else:
            # Use run mode set in __init__
            run_mode = self.run_mode

        Path('xkcd').mkdir(exist_ok=True)  # store comics in ./xkcd

        # Get latest comic number:
        self.latest_comic_number = self._get_latest_comic()

        # Create and start the Thread objects.
        self._download_threads = []  # Initialise list of Thread objects

        if run_mode:
            self._start_threads(1, self.latest_comic_number + 1, 100)
        if not run_mode:  # 10 threads of 10
            self._start_threads(self.latest_comic_number - 100, self.latest_comic_number + 1, 10)

        # Wait for all threads to end.
        for download_thread in self._download_threads:
            download_thread.join()

    def _start_threads(self, first_comic: int, last_comic: int, step: int) -> None:
        for i in range(first_comic, last_comic + 1, step):
            download_thread = self._setup_download_thread(i, i + step)
            self._download_threads.append(download_thread)
            download_thread.start()

    def _setup_download_thread(self, first_comic: int, last_comic: int) -> threading.Thread:
        download_thread = threading.Thread(target=self._threaded_download,
                                           args=(first_comic, last_comic)
                                           )

        return download_thread
