"""Embed XKCD comic metadata into downloaded image files."""

import logging
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

logger = logging.getLogger(__name__)


def embed_metadata(filepath: Path, comic: dict) -> None:
    """Embed comic metadata into an image file in-place.

    Best-effort: logs warnings on failure but does not raise.

    Args:
        filepath: Path to the saved image file.
        comic: The XKCD API JSON dict (title, alt, num, year, month, day, transcript, img).
    """
    try:
        suffix = filepath.suffix.lower()
        if suffix == ".png":
            _embed_png(filepath, comic)
        elif suffix in (".jpg", ".jpeg"):
            _embed_jpeg(filepath, comic)
        elif suffix == ".gif":
            _embed_gif(filepath, comic)
    except Exception:
        logger.warning("Failed to embed metadata for comic %s", comic.get("num"), exc_info=True)


def _comic_date(comic: dict) -> str:
    year = comic.get("year", "")
    month = comic.get("month", "1").zfill(2)
    day = comic.get("day", "1").zfill(2)
    return f"{year}-{month}-{day}"


def _embed_png(filepath: Path, comic: dict) -> None:
    img = Image.open(filepath)
    meta = PngInfo()
    meta.add_text("Title", comic.get("title", ""))
    meta.add_text("Description", comic.get("alt", ""))
    meta.add_text("Source", f"https://xkcd.com/{comic['num']}/")
    meta.add_text("Creation Time", _comic_date(comic))
    if comic.get("transcript"):
        meta.add_text("Comment", comic["transcript"])
    img.save(filepath, pnginfo=meta)


def _embed_jpeg(filepath: Path, comic: dict) -> None:
    img = Image.open(filepath)
    exif = img.getexif()
    exif[0x010E] = comic.get("alt", "")  # ImageDescription
    year = comic.get("year", "")
    month = comic.get("month", "1").zfill(2)
    day = comic.get("day", "1").zfill(2)
    exif[0x9003] = f"{year}:{month}:{day} 00:00:00"  # DateTimeOriginal
    img.save(filepath, exif=exif.tobytes())


def _embed_gif(filepath: Path, comic: dict) -> None:
    img = Image.open(filepath)
    if getattr(img, "n_frames", 1) > 1:
        return  # Skip animated GIFs to avoid frame loss
    comment = comic.get("alt", "").encode("utf-8")
    img.save(filepath, comment=comment)
