"""Embed XKCD comic metadata into downloaded image files."""

import logging
import struct
import zlib
from pathlib import Path

logger = logging.getLogger(__name__)

# PNG signature: first 8 bytes of any PNG file
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def build_png_metadata_chunks(comic: dict) -> bytes:
    """Build PNG tEXt chunks as raw bytes, ready to inject after the IHDR chunk.

    Returns empty bytes if comic dict is empty/invalid.
    """
    chunks = []
    chunks.append(_make_png_text_chunk("Title", comic.get("title", "")))
    chunks.append(_make_png_text_chunk("Description", comic.get("alt", "")))
    chunks.append(_make_png_text_chunk("Source", f"https://xkcd.com/{comic['num']}/"))
    chunks.append(_make_png_text_chunk("Creation Time", _comic_date(comic)))
    if comic.get("transcript"):
        chunks.append(_make_png_text_chunk("Comment", comic["transcript"]))
    return b"".join(chunks)


def embed_metadata(filepath: Path, comic: dict) -> None:
    """Embed comic metadata into an image file in-place.

    Best-effort: logs warnings on failure but does not raise.
    For PNGs, prefer using build_png_metadata_chunks() during initial write
    to avoid the read-back overhead. This function is for JPEGs/GIFs or
    retroactively adding metadata to existing PNGs.

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


def _make_png_text_chunk(keyword: str, text: str) -> bytes:
    """Create a PNG tEXt chunk with the given keyword and text."""
    data = keyword.encode("latin-1") + b"\x00" + text.encode("latin-1", errors="replace")
    length = struct.pack(">I", len(data))
    chunk_type = b"tEXt"
    crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    return length + chunk_type + data + crc


def _embed_png(filepath: Path, comic: dict) -> None:
    """Inject tEXt chunks directly into PNG bytes — no Pillow decode/encode."""
    raw = filepath.read_bytes()
    if not raw.startswith(_PNG_SIGNATURE):
        return

    chunks = []
    chunks.append(_make_png_text_chunk("Title", comic.get("title", "")))
    chunks.append(_make_png_text_chunk("Description", comic.get("alt", "")))
    chunks.append(_make_png_text_chunk("Source", f"https://xkcd.com/{comic['num']}/"))
    chunks.append(_make_png_text_chunk("Creation Time", _comic_date(comic)))
    if comic.get("transcript"):
        chunks.append(_make_png_text_chunk("Comment", comic["transcript"]))

    text_data = b"".join(chunks)

    # Insert tEXt chunks after the IHDR chunk (first chunk after 8-byte signature).
    # IHDR is always first: 4 bytes length + 4 bytes type + data + 4 bytes CRC
    ihdr_length = struct.unpack(">I", raw[8:12])[0]
    insert_pos = 8 + 4 + 4 + ihdr_length + 4  # sig + length + type + data + crc

    filepath.write_bytes(raw[:insert_pos] + text_data + raw[insert_pos:])


def _embed_jpeg(filepath: Path, comic: dict) -> None:
    from PIL import Image

    img = Image.open(filepath)
    exif = img.getexif()
    exif[0x010E] = comic.get("alt", "")  # ImageDescription
    year = comic.get("year", "")
    month = comic.get("month", "1").zfill(2)
    day = comic.get("day", "1").zfill(2)
    exif[0x9003] = f"{year}:{month}:{day} 00:00:00"  # DateTimeOriginal
    img.save(filepath, exif=exif.tobytes())


def _embed_gif(filepath: Path, comic: dict) -> None:
    from PIL import Image

    img = Image.open(filepath)
    if getattr(img, "n_frames", 1) > 1:
        return  # Skip animated GIFs to avoid frame loss
    comment = comic.get("alt", "").encode("utf-8")
    img.save(filepath, comment=comment)
