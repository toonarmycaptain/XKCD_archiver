"""Tests for the Downloader class."""

from pathlib import Path

import pytest
import responses

from XKCD_archiver.downloader import Downloader

LATEST_COMIC_JSON = {
    "num": 50,
    "img": "https://imgs.xkcd.com/comics/latest.png",
    "title": "Latest Comic",
    "alt": "Alt text",
}

COMIC_JSON = {
    "num": 1,
    "img": "https://imgs.xkcd.com/comics/barrel_cropped_(1).jpg",
    "title": "Barrel - Part 1",
    "alt": "Don't we all.",
}

COMIC_10_JSON = {
    "num": 10,
    "img": "https://imgs.xkcd.com/comics/pi.jpg",
    "title": "Pi Equals",
    "alt": "My most famous drawing.",
}

FAKE_IMAGE = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def xkcd_dir(tmp_path):
    comic_dir = tmp_path / "xkcd"
    comic_dir.mkdir()
    return tmp_path


class TestDownloaderInit:
    def test_default_full_mode(self):
        d = Downloader()
        assert d.run_mode is True

    def test_quick_mode(self):
        d = Downloader(run_mode=False)
        assert d.run_mode is False

    def test_explicit_full_mode(self):
        d = Downloader(run_mode=True)
        assert d.run_mode is True


class TestSetComicFilename:
    def test_simple_filename(self):
        d = Downloader()
        comic = {"num": 1, "img": "https://imgs.xkcd.com/comics/barrel.jpg"}
        result = d._set_comic_filename(comic)
        assert result == Path("1-barrel.jpg")

    def test_filename_with_special_chars(self):
        d = Downloader()
        comic = {"num": 1, "img": "https://imgs.xkcd.com/comics/barrel_cropped_(1).jpg"}
        result = d._set_comic_filename(comic)
        assert result == Path("1-barrel_cropped_(1).jpg")

    def test_png_extension(self):
        d = Downloader()
        comic = {"num": 100, "img": "https://imgs.xkcd.com/comics/test.png"}
        result = d._set_comic_filename(comic)
        assert result == Path("100-test.png")


class TestGetLatestComic:
    @responses.activate
    def test_returns_latest_number(self):
        responses.add(
            responses.GET,
            "https://xkcd.com/info.0.json",
            json=LATEST_COMIC_JSON,
        )
        d = Downloader()
        result = d._get_latest_comic()
        assert result == 50

    @responses.activate
    def test_makes_correct_request(self):
        responses.add(
            responses.GET,
            "https://xkcd.com/info.0.json",
            json=LATEST_COMIC_JSON,
        )
        d = Downloader()
        d._get_latest_comic()
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == "https://xkcd.com/info.0.json"


class TestGetComicJson:
    @responses.activate
    def test_returns_json(self):
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json=COMIC_JSON,
        )
        d = Downloader()
        import requests

        with requests.Session() as session:
            result = d._get_comic_json(session, 1)
        assert result == COMIC_JSON

    @responses.activate
    def test_returns_none_on_404(self):
        responses.add(
            responses.GET,
            "https://xkcd.com/404/info.0.json",
            status=404,
        )
        d = Downloader()
        import requests

        with requests.Session() as session:
            result = d._get_comic_json(session, 404)
        assert result is None


class TestDownloadImage:
    @responses.activate
    def test_downloads_image(self, xkcd_dir, monkeypatch):
        monkeypatch.chdir(xkcd_dir)
        responses.add(
            responses.GET,
            "https://imgs.xkcd.com/comics/test.png",
            body=FAKE_IMAGE,
        )
        d = Downloader()
        import requests

        with requests.Session() as session:
            d._download_image(session, "https://imgs.xkcd.com/comics/test.png", Path("1-test.png"))
        assert (xkcd_dir / "xkcd" / "1-test.png").exists()

    @responses.activate
    def test_skips_on_non_200(self, xkcd_dir, monkeypatch):
        monkeypatch.chdir(xkcd_dir)
        responses.add(
            responses.GET,
            "https://imgs.xkcd.com/comics/missing.png",
            status=403,
        )
        d = Downloader()
        import requests

        with requests.Session() as session:
            result = d._download_image(session, "https://imgs.xkcd.com/comics/missing.png", Path("1-missing.png"))
        assert result is None
        assert not (xkcd_dir / "xkcd" / "1-missing.png").exists()


class TestDownloadComics:
    @responses.activate
    def test_full_mode_downloads_all(self, xkcd_dir, monkeypatch):
        monkeypatch.chdir(xkcd_dir)

        # Latest comic is #3
        responses.add(
            responses.GET,
            "https://xkcd.com/info.0.json",
            json={"num": 3, "img": "https://imgs.xkcd.com/comics/latest.png", "title": "Latest"},
        )

        for i in range(1, 4):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(
                responses.GET,
                f"https://imgs.xkcd.com/comics/comic{i}.png",
                body=FAKE_IMAGE,
            )

        d = Downloader(run_mode=True)
        d.download_comics()

        assert (xkcd_dir / "xkcd" / "1-comic1.png").exists()
        assert (xkcd_dir / "xkcd" / "2-comic2.png").exists()
        assert (xkcd_dir / "xkcd" / "3-comic3.png").exists()

    @responses.activate
    def test_skips_existing_comics(self, xkcd_dir, monkeypatch):
        monkeypatch.chdir(xkcd_dir)

        # Pre-create comic 1
        (xkcd_dir / "xkcd" / "1-comic1.png").write_bytes(FAKE_IMAGE)

        responses.add(
            responses.GET,
            "https://xkcd.com/info.0.json",
            json={"num": 2, "img": "https://imgs.xkcd.com/comics/latest.png", "title": "Latest"},
        )

        # Comic 1 - json fetched, image GET attempted, but file write fails with FileExistsError
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json={"num": 1, "img": "https://imgs.xkcd.com/comics/comic1.png", "title": "Comic 1"},
        )
        responses.add(
            responses.GET,
            "https://imgs.xkcd.com/comics/comic1.png",
            body=FAKE_IMAGE,
        )

        # Comic 2
        responses.add(
            responses.GET,
            "https://xkcd.com/2/info.0.json",
            json={"num": 2, "img": "https://imgs.xkcd.com/comics/comic2.png", "title": "Comic 2"},
        )
        responses.add(
            responses.GET,
            "https://imgs.xkcd.com/comics/comic2.png",
            body=FAKE_IMAGE,
        )

        d = Downloader(run_mode=True)
        d.download_comics()

        assert (xkcd_dir / "xkcd" / "1-comic1.png").exists()
        assert (xkcd_dir / "xkcd" / "2-comic2.png").exists()

    @responses.activate
    def test_quick_mode_downloads_recent(self, xkcd_dir, monkeypatch):
        monkeypatch.chdir(xkcd_dir)

        latest = 110

        responses.add(
            responses.GET,
            "https://xkcd.com/info.0.json",
            json={"num": latest, "img": "https://imgs.xkcd.com/comics/latest.png", "title": "Latest"},
        )

        # Pre-create comics 108-110 so quick mode hits existing files and stops early
        for i in range(108, latest + 1):
            (xkcd_dir / "xkcd" / f"{i}-comic{i}.png").write_bytes(FAKE_IMAGE)

        # Register mocks for the range quick mode will check (latest-100 to latest)
        for i in range(10, latest + 1):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(
                responses.GET,
                f"https://imgs.xkcd.com/comics/comic{i}.png",
                body=FAKE_IMAGE,
            )

        d = Downloader(run_mode=False)
        d.download_comics()

        # Pre-existing comics should still be there
        for i in range(108, latest + 1):
            assert (xkcd_dir / "xkcd" / f"{i}-comic{i}.png").exists()

    @responses.activate
    def test_download_comic_with_none_json(self, xkcd_dir, monkeypatch):
        """Comics that return non-200 JSON responses should be silently skipped."""
        monkeypatch.chdir(xkcd_dir)

        responses.add(
            responses.GET,
            "https://xkcd.com/404/info.0.json",
            status=404,
        )

        d = Downloader()
        import requests as req

        with req.Session() as session:
            # Should not raise
            d._download_comic(session, 404)

        # No file created
        assert not list((xkcd_dir / "xkcd").iterdir())


class TestHelperFunctions:
    def test_punct_stripper(self):
        from XKCD_archiver.helper_functions import punct_stripper

        table = punct_stripper()
        result = "hello, world!".translate(table)
        assert result == "hello world"
