"""Tests for the Downloader class."""

from pathlib import Path

import responses

from XKCD_archiver.downloader import Downloader, DownloadProgress

FAKE_IMAGE = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _register_latest(num):
    responses.add(
        responses.GET,
        "https://xkcd.com/info.0.json",
        json={"num": num, "img": f"https://imgs.xkcd.com/comics/comic{num}.png", "title": f"Comic {num}"},
    )


class TestDownloaderInit:
    def test_defaults(self):
        d = Downloader()
        assert d.max_workers == 10
        assert d.output_dir == Path("xkcd")
        assert d.max_retries == 3
        assert d.progress_callback is None

    def test_custom_params(self, tmp_path):
        cb = lambda p: None  # noqa: E731
        d = Downloader(max_workers=5, output_dir=tmp_path / "comics", max_retries=1, progress_callback=cb)
        assert d.max_workers == 5
        assert d.output_dir == tmp_path / "comics"
        assert d.max_retries == 1
        assert d.progress_callback is cb


class TestSetComicFilename:
    def test_simple_filename(self):
        d = Downloader()
        comic = {"num": 1, "img": "https://imgs.xkcd.com/comics/barrel.jpg"}
        assert d._set_comic_filename(comic) == Path("1-barrel.jpg")

    def test_filename_with_special_chars(self):
        d = Downloader()
        comic = {"num": 1, "img": "https://imgs.xkcd.com/comics/barrel_cropped_(1).jpg"}
        assert d._set_comic_filename(comic) == Path("1-barrel_cropped_(1).jpg")

    def test_png_extension(self):
        d = Downloader()
        comic = {"num": 100, "img": "https://imgs.xkcd.com/comics/test.png"}
        assert d._set_comic_filename(comic) == Path("100-test.png")


class TestGetLatestComic:
    @responses.activate
    def test_returns_latest_number(self):
        _register_latest(50)
        d = Downloader()
        session = d._get_session()
        assert d._get_latest_comic(session) == 50

    @responses.activate
    def test_makes_correct_request(self):
        _register_latest(50)
        d = Downloader()
        session = d._get_session()
        d._get_latest_comic(session)
        assert responses.calls[0].request.url == "https://xkcd.com/info.0.json"


class TestGetComicJson:
    @responses.activate
    def test_returns_json(self):
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json={"num": 1, "img": "https://imgs.xkcd.com/comics/barrel.jpg", "title": "Barrel"},
        )
        d = Downloader()
        session = d._get_session()
        result = d._get_comic_json(session, 1)
        assert result["num"] == 1

    @responses.activate
    def test_returns_none_on_404(self):
        responses.add(responses.GET, "https://xkcd.com/404/info.0.json", status=404)
        d = Downloader()
        session = d._get_session()
        assert d._get_comic_json(session, 404) is None


class TestDownloadImage:
    @responses.activate
    def test_downloads_image(self, tmp_path):
        responses.add(responses.GET, "https://imgs.xkcd.com/comics/test.png", body=FAKE_IMAGE)
        d = Downloader(output_dir=tmp_path)
        session = d._get_session()
        filepath = tmp_path / "1-test.png"
        result = d._download_image(session, "https://imgs.xkcd.com/comics/test.png", filepath)
        assert result is True
        assert filepath.exists()
        assert filepath.read_bytes() == FAKE_IMAGE

    @responses.activate
    def test_skips_on_non_200(self, tmp_path):
        responses.add(responses.GET, "https://imgs.xkcd.com/comics/missing.png", status=403)
        d = Downloader(output_dir=tmp_path)
        session = d._get_session()
        filepath = tmp_path / "1-missing.png"
        result = d._download_image(session, "https://imgs.xkcd.com/comics/missing.png", filepath)
        assert result is False
        assert not filepath.exists()


class TestDownloadOne:
    @responses.activate
    def test_downloads_comic(self, tmp_path):
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json={"num": 1, "img": "https://imgs.xkcd.com/comics/barrel.png", "title": "Barrel"},
        )
        responses.add(responses.GET, "https://imgs.xkcd.com/comics/barrel.png", body=FAKE_IMAGE)

        d = Downloader(output_dir=tmp_path)
        result = d._download_one(1, 10)

        assert result.status == "downloaded"
        assert result.comic_number == 1
        assert (tmp_path / "1-barrel.png").exists()

    @responses.activate
    def test_skips_existing(self, tmp_path):
        (tmp_path / "1-barrel.png").write_bytes(FAKE_IMAGE)
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json={"num": 1, "img": "https://imgs.xkcd.com/comics/barrel.png", "title": "Barrel"},
        )

        d = Downloader(output_dir=tmp_path)
        result = d._download_one(1, 10)
        assert result.status == "skipped"

    @responses.activate
    def test_skips_on_404_json(self, tmp_path):
        responses.add(responses.GET, "https://xkcd.com/404/info.0.json", status=404)

        d = Downloader(output_dir=tmp_path)
        result = d._download_one(404, 10)
        assert result.status == "skipped"

    @responses.activate
    def test_reports_mismatched_num(self, tmp_path):
        responses.add(
            responses.GET,
            "https://xkcd.com/1/info.0.json",
            json={"num": 999, "img": "https://imgs.xkcd.com/comics/wrong.png", "title": "Wrong"},
        )

        d = Downloader(output_dir=tmp_path)
        result = d._download_one(1, 10)
        assert result.status == "failed"
        assert "999" in result.error


class TestDownloadComics:
    @responses.activate
    def test_full_mode_downloads_all(self, tmp_path):
        _register_latest(3)
        for i in range(1, 4):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(responses.GET, f"https://imgs.xkcd.com/comics/comic{i}.png", body=FAKE_IMAGE)

        d = Downloader(output_dir=tmp_path)
        results = d.download_comics(mode="full")

        assert len(results) == 3
        for i in range(1, 4):
            assert (tmp_path / f"{i}-comic{i}.png").exists()

    @responses.activate
    def test_skips_existing_comics(self, tmp_path):
        (tmp_path / "1-comic1.png").write_bytes(FAKE_IMAGE)

        _register_latest(2)
        for i in range(1, 3):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(responses.GET, f"https://imgs.xkcd.com/comics/comic{i}.png", body=FAKE_IMAGE)

        d = Downloader(output_dir=tmp_path)
        results = d.download_comics(mode="full")

        skipped = [r for r in results if r.status == "skipped"]
        downloaded = [r for r in results if r.status == "downloaded"]
        assert len(skipped) == 1
        assert len(downloaded) == 1

    @responses.activate
    def test_quick_mode_only_checks_last_100(self, tmp_path):
        _register_latest(150)
        for i in range(51, 151):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(responses.GET, f"https://imgs.xkcd.com/comics/comic{i}.png", body=FAKE_IMAGE)

        d = Downloader(output_dir=tmp_path)
        results = d.download_comics(mode="quick")

        assert len(results) == 100
        assert not any(r.comic_number < 51 for r in results)

    @responses.activate
    def test_progress_callback_called(self, tmp_path):
        _register_latest(2)
        for i in range(1, 3):
            responses.add(
                responses.GET,
                f"https://xkcd.com/{i}/info.0.json",
                json={"num": i, "img": f"https://imgs.xkcd.com/comics/comic{i}.png", "title": f"Comic {i}"},
            )
            responses.add(responses.GET, f"https://imgs.xkcd.com/comics/comic{i}.png", body=FAKE_IMAGE)

        progress_reports = []
        d = Downloader(output_dir=tmp_path, progress_callback=progress_reports.append)
        d.download_comics(mode="full")

        assert len(progress_reports) == 2
        assert all(isinstance(p, DownloadProgress) for p in progress_reports)


class TestHelperFunctions:
    def test_punct_stripper(self):
        from XKCD_archiver.helper_functions import punct_stripper

        table = punct_stripper()
        result = "hello, world!".translate(table)
        assert result == "hello world"
