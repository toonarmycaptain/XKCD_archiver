"""Tests for image metadata embedding."""

from pathlib import Path

from PIL import Image

from XKCD_archiver.metadata import embed_metadata

COMIC = {
    "num": 1,
    "title": "Barrel - Part 1",
    "alt": "Don't we all.",
    "img": "https://imgs.xkcd.com/comics/barrel.png",
    "year": "2006",
    "month": "1",
    "day": "1",
    "transcript": "A boy in a barrel.",
}


def _create_png(path: Path, width: int = 10, height: int = 10) -> Path:
    img = Image.new("RGB", (width, height), color="red")
    img.save(path, format="PNG")
    return path


def _create_jpeg(path: Path, width: int = 10, height: int = 10) -> Path:
    img = Image.new("RGB", (width, height), color="blue")
    img.save(path, format="JPEG")
    return path


def _create_gif(path: Path, width: int = 10, height: int = 10) -> Path:
    img = Image.new("RGB", (width, height), color="green")
    img.save(path, format="GIF")
    return path


class TestPngMetadata:
    def test_embeds_alt_text(self, tmp_path):
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("Description") == "Don't we all."

    def test_embeds_title(self, tmp_path):
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("Title") == "Barrel - Part 1"

    def test_embeds_source(self, tmp_path):
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("Source") == "https://xkcd.com/1/"

    def test_embeds_date(self, tmp_path):
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("Creation Time") == "2006-01-01"

    def test_embeds_transcript(self, tmp_path):
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("Comment") == "A boy in a barrel."

    def test_no_transcript_when_missing(self, tmp_path):
        comic = {**COMIC, "transcript": ""}
        filepath = _create_png(tmp_path / "1-barrel.png")
        embed_metadata(filepath, comic)

        img = Image.open(filepath)
        assert "Comment" not in img.info


class TestJpegMetadata:
    def test_embeds_alt_text(self, tmp_path):
        filepath = _create_jpeg(tmp_path / "1-barrel.jpg")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        exif = img.getexif()
        assert exif.get(0x010E) == "Don't we all."

    def test_embeds_date(self, tmp_path):
        filepath = _create_jpeg(tmp_path / "1-barrel.jpg")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        exif = img.getexif()
        assert exif.get(0x9003) == "2006:01:01 00:00:00"


class TestGifMetadata:
    def test_embeds_comment(self, tmp_path):
        filepath = _create_gif(tmp_path / "1-barrel.gif")
        embed_metadata(filepath, COMIC)

        img = Image.open(filepath)
        assert img.info.get("comment") == b"Don't we all."

    def test_skips_animated_gif(self, tmp_path):
        # Create a simple 2-frame GIF
        filepath = tmp_path / "1-animated.gif"
        frames = [
            Image.new("RGB", (10, 10), color="red"),
            Image.new("RGB", (10, 10), color="blue"),
        ]
        frames[0].save(filepath, format="GIF", save_all=True, append_images=frames[1:])

        embed_metadata(filepath, COMIC)

        # Should not have modified — no comment added
        img = Image.open(filepath)
        assert img.info.get("comment") is None


class TestErrorHandling:
    def test_does_not_raise_on_bad_file(self, tmp_path):
        filepath = tmp_path / "1-broken.png"
        filepath.write_bytes(b"not an image")
        # Should not raise
        embed_metadata(filepath, COMIC)

    def test_does_not_raise_on_unknown_extension(self, tmp_path):
        filepath = tmp_path / "1-comic.webp"
        filepath.write_bytes(b"fake")
        embed_metadata(filepath, COMIC)
