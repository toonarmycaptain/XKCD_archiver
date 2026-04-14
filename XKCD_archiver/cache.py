"""SQLite cache for comic metadata."""

import sqlite3
import threading
from pathlib import Path


class ComicCache:
    """Store and retrieve comic metadata in a SQLite database.

    Uses a single shared connection with a lock for thread safety.
    """

    DB_NAME = ".xkcd_cache.db"

    def __init__(self, output_dir: Path) -> None:
        self._db_path = output_dir / self.DB_NAME
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS comics (
                    num INTEGER PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    alt TEXT NOT NULL DEFAULT '',
                    img TEXT NOT NULL DEFAULT '',
                    year TEXT NOT NULL DEFAULT '',
                    month TEXT NOT NULL DEFAULT '',
                    day TEXT NOT NULL DEFAULT '',
                    transcript TEXT NOT NULL DEFAULT '',
                    filename TEXT NOT NULL DEFAULT ''
                )
            """)
            self._conn.commit()
        return self._conn

    def store(self, comic: dict, filename: str) -> None:
        """Store a single comic's metadata. Thread-safe."""
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                """INSERT OR REPLACE INTO comics
                   (num, title, alt, img, year, month, day, transcript, filename)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    comic["num"],
                    comic.get("title", ""),
                    comic.get("alt", ""),
                    comic.get("img", ""),
                    comic.get("year", ""),
                    comic.get("month", ""),
                    comic.get("day", ""),
                    comic.get("transcript", ""),
                    filename,
                ),
            )
            conn.commit()

    def count(self) -> int:
        """Return total number of cached comics."""
        with self._lock:
            conn = self._get_conn()
            return conn.execute("SELECT COUNT(*) FROM comics").fetchone()[0]

    def get(self, num: int) -> dict | None:
        """Retrieve metadata for a single comic by number."""
        with self._lock:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM comics WHERE num = ?", (num,)).fetchone()
            conn.row_factory = None
            return dict(row) if row else None

    def list_all(self) -> list[dict]:
        """Return all comics ordered by number."""
        with self._lock:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT num, title, filename FROM comics ORDER BY num").fetchall()
            conn.row_factory = None
            return [dict(r) for r in rows]

    def recent(self, after_rowid: int = 0) -> tuple[list[dict], int]:
        """Return comics inserted after the given rowid. Returns (comics, new_max_rowid)."""
        with self._lock:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT rowid, num, title FROM comics WHERE rowid > ? ORDER BY rowid",
                (after_rowid,),
            ).fetchall()
            if rows:
                comics = [{"num": r[1], "title": r[2]} for r in rows]
                return comics, rows[-1][0]
            return [], after_rowid

    def search(self, query: str) -> list[dict]:
        """Search across title, alt text, and transcript."""
        with self._lock:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            like = f"%{query}%"
            rows = conn.execute(
                """SELECT num, title, filename FROM comics
                   WHERE title LIKE ? OR alt LIKE ? OR transcript LIKE ?
                   ORDER BY num""",
                (like, like, like),
            ).fetchall()
            conn.row_factory = None
            return [dict(r) for r in rows]
