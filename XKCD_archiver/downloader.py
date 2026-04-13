"""Downloader class using ThreadPoolExecutor."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from time import sleep

import requests
from requests.adapters import HTTPAdapter

from XKCD_archiver.metadata import embed_metadata


@dataclass
class DownloadProgress:
    """Progress report emitted per comic."""

    comic_number: int
    total: int
    status: str  # "downloaded", "skipped", "failed"
    error: str | None = None


class Downloader:
    """
    Downloads XKCD comics using a thread pool.

    Each worker thread gets its own requests.Session to avoid
    lock contention on a shared connection pool.

    Attributes
    ----------
    max_workers : int
        Maximum number of concurrent download threads.
    output_dir : Path
        Directory to save comics to.
    max_retries : int
        Number of retry attempts per comic on failure.
    progress_callback : callable or None
        Called with a DownloadProgress for each comic processed.
    """

    BASE_URL = "https://xkcd.com"
    TIMEOUT = 30

    def __init__(
        self,
        max_workers: int = 10,
        output_dir: Path = Path("xkcd"),
        max_retries: int = 3,
        progress_callback: callable = None,
    ) -> None:
        self.max_workers = max_workers
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.progress_callback = progress_callback
        self._thread_local = threading.local()

    def _get_session(self) -> requests.Session:
        """Get or create a per-thread requests.Session."""
        if not hasattr(self._thread_local, "session"):
            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
            session.mount("https://", adapter)
            self._thread_local.session = session
        return self._thread_local.session

    def _report(self, comic_number: int, total: int, status: str, error: str | None = None) -> None:
        if self.progress_callback:
            self.progress_callback(DownloadProgress(comic_number, total, status, error))

    def _get_latest_comic(self, session: requests.Session) -> int:
        response = session.get(f"{self.BASE_URL}/info.0.json", timeout=self.TIMEOUT)
        return response.json()["num"]

    def _get_comic_json(self, session: requests.Session, comic_number: int) -> dict | None:
        response = session.get(f"{self.BASE_URL}/{comic_number}/info.0.json", timeout=self.TIMEOUT)
        if response.status_code != 200:
            return None
        return response.json()

    def _set_comic_filename(self, comic: dict) -> Path:
        return Path(f"{comic['num']}-{Path(comic['img']).name}")

    def _download_image(self, session: requests.Session, comic_url: str, filepath: Path) -> bool:
        """Download image. Returns True if saved, False if image unavailable."""
        response = session.get(comic_url, timeout=self.TIMEOUT)
        if response.status_code != 200:
            return False

        with open(filepath, "xb") as image_file:
            for chunk in response.iter_content(100_000):
                image_file.write(chunk)
        return True

    def _download_one(self, comic_number: int, total: int) -> DownloadProgress:
        session = self._get_session()
        for attempt in range(self.max_retries):
            try:
                comic = self._get_comic_json(session, comic_number)
                if not comic:
                    return DownloadProgress(comic_number, total, "skipped")

                if comic_number != comic["num"]:
                    return DownloadProgress(
                        comic_number,
                        total,
                        "failed",
                        f"Requested comic {comic_number} but API returned comic {comic['num']}",
                    )

                filename = self._set_comic_filename(comic)
                filepath = self.output_dir / filename

                if filepath.exists():
                    return DownloadProgress(comic_number, total, "skipped")

                if self._download_image(session, comic["img"], filepath):
                    embed_metadata(filepath, comic)
                    return DownloadProgress(comic_number, total, "downloaded")
                return DownloadProgress(comic_number, total, "skipped", "image unavailable")

            except FileExistsError:
                return DownloadProgress(comic_number, total, "skipped")

            except requests.RequestException as e:
                if attempt < self.max_retries - 1:
                    sleep(1.0 * (2**attempt))
                    continue
                return DownloadProgress(comic_number, total, "failed", str(e))

        return DownloadProgress(comic_number, total, "failed", "max retries exceeded")

    def download_comics(self, mode: str = "full") -> list[DownloadProgress]:
        """
        Download comics from xkcd.com.

        Args:
            mode: "full" to check all comics, "quick" to check only the latest 100.

        Returns:
            List of DownloadProgress results for each comic processed.
        """
        self.output_dir.mkdir(exist_ok=True)

        session = self._get_session()
        latest = self._get_latest_comic(session)

        comic_numbers = range(max(1, latest - 99), latest + 1) if mode == "quick" else range(1, latest + 1)

        total = len(comic_numbers)
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._download_one, num, total): num for num in comic_numbers}

            for future in as_completed(futures):
                progress = future.result()
                results.append(progress)
                self._report(progress.comic_number, progress.total, progress.status, progress.error)

        return results
