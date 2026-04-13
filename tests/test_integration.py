"""Integration tests that hit the real xkcd.com API."""

import pytest
from PIL import Image

from XKCD_archiver.downloader import Downloader


@pytest.mark.integration
class TestRealDownload:
    def test_downloads_comic_with_metadata(self, tmp_path):
        """Download recent comics and verify a PNG has metadata."""
        d = Downloader(output_dir=tmp_path, max_workers=1)
        d.download_comics(mode="quick")

        pngs = list(tmp_path.glob("*.png"))
        assert len(pngs) > 0, "Expected at least one PNG downloaded"

        img = Image.open(pngs[0])
        assert img.info.get("Description"), "Expected alt text in Description metadata"
        assert img.info.get("Title"), "Expected title in Title metadata"
        assert img.info.get("Source", "").startswith("https://xkcd.com/")

    def test_downloads_comic_1_jpeg_with_metadata(self, tmp_path):
        """Download comic #1 (a JPEG) and verify EXIF metadata."""
        d = Downloader(output_dir=tmp_path, max_workers=1)

        result = d._download_one(1, 1)
        assert result.status == "downloaded"

        filepath = list(tmp_path.glob("1-*"))[0]
        assert filepath.exists()

        img = Image.open(filepath)
        exif = img.getexif()
        assert exif.get(0x010E) == "Don't we all."  # ImageDescription
        assert exif.get(0x9003) == "2006:01:01 00:00:00"  # DateTimeOriginal
