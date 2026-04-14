"""Tests for the SQLite metadata cache."""

from XKCD_archiver.cache import ComicCache

COMIC_1 = {
    "num": 1,
    "title": "Barrel - Part 1",
    "alt": "Don't we all.",
    "img": "https://imgs.xkcd.com/comics/barrel.png",
    "year": "2006",
    "month": "1",
    "day": "1",
    "transcript": "A boy sits in a barrel.",
}

COMIC_327 = {
    "num": 327,
    "title": "Exploits of a Mom",
    "alt": "Her daughter is named Help I'm trapped in a driver's license factory.",
    "img": "https://imgs.xkcd.com/comics/exploits_of_a_mom.png",
    "year": "2007",
    "month": "10",
    "day": "10",
    "transcript": "Bobby Tables",
}

COMIC_100 = {
    "num": 100,
    "title": "Family Circus",
    "alt": "This was my first hit.",
    "img": "https://imgs.xkcd.com/comics/family_circus.jpg",
    "year": "2006",
    "month": "5",
    "day": "10",
    "transcript": "",
}


class TestStore:
    def test_store_and_get(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        result = cache.get(1)
        assert result is not None
        assert result["title"] == "Barrel - Part 1"
        assert result["alt"] == "Don't we all."
        assert result["filename"] == "1-barrel.png"

    def test_store_replaces_existing(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        updated = {**COMIC_1, "title": "Updated Title"}
        cache.store(updated, "1-barrel.png")
        result = cache.get(1)
        assert result["title"] == "Updated Title"

    def test_get_missing_returns_none(self, tmp_path):
        cache = ComicCache(tmp_path)
        assert cache.get(999) is None


class TestCount:
    def test_empty(self, tmp_path):
        cache = ComicCache(tmp_path)
        assert cache.count() == 0

    def test_after_stores(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")
        assert cache.count() == 2


class TestListAll:
    def test_empty(self, tmp_path):
        cache = ComicCache(tmp_path)
        assert cache.list_all() == []

    def test_returns_ordered_by_num(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")
        cache.store(COMIC_1, "1-barrel.png")
        cache.store(COMIC_100, "100-family_circus.jpg")

        result = cache.list_all()
        assert len(result) == 3
        assert [r["num"] for r in result] == [1, 100, 327]
        assert result[0]["title"] == "Barrel - Part 1"
        assert result[0]["filename"] == "1-barrel.png"


class TestRecent:
    def test_returns_new_entries(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        comics, rowid = cache.recent(0)
        assert len(comics) == 1
        assert comics[0]["num"] == 1

    def test_returns_only_after_rowid(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        _, rowid = cache.recent(0)

        cache.store(COMIC_327, "327-exploits_of_a_mom.png")
        comics, new_rowid = cache.recent(rowid)
        assert len(comics) == 1
        assert comics[0]["num"] == 327
        assert new_rowid > rowid

    def test_returns_empty_when_nothing_new(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        _, rowid = cache.recent(0)
        comics, same_rowid = cache.recent(rowid)
        assert comics == []
        assert same_rowid == rowid


class TestSearch:
    def test_search_by_title(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")

        results = cache.search("Barrel")
        assert len(results) == 1
        assert results[0]["num"] == 1

    def test_search_by_alt_text(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")

        results = cache.search("trapped")
        assert len(results) == 1
        assert results[0]["num"] == 327

    def test_search_by_transcript(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")

        results = cache.search("Bobby")
        assert len(results) == 1
        assert results[0]["num"] == 327

    def test_search_case_insensitive(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")

        results = cache.search("barrel")
        assert len(results) == 1

    def test_search_no_results(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_1, "1-barrel.png")

        results = cache.search("nonexistent")
        assert results == []

    def test_search_returns_filename(self, tmp_path):
        cache = ComicCache(tmp_path)
        cache.store(COMIC_327, "327-exploits_of_a_mom.png")

        results = cache.search("Exploits")
        assert results[0]["filename"] == "327-exploits_of_a_mom.png"


class TestThreadSafety:
    def test_concurrent_stores(self, tmp_path):
        """Multiple threads storing simultaneously shouldn't corrupt."""
        import threading

        cache = ComicCache(tmp_path)
        errors = []

        def store_comic(num):
            try:
                comic = {**COMIC_1, "num": num, "title": f"Comic {num}"}
                cache.store(comic, f"{num}-comic.png")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=store_comic, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert cache.count() == 50
