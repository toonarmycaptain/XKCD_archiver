# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-04-13
### Added
- Comic viewer tab in TUI with scrollable list, inline image preview, and metadata display
- SQLite metadata cache (`.xkcd_cache.db`) populated during downloads for fast browsing
- Search across comic titles, alt text, and transcripts
- Type-to-search: type while comic list is focused to filter
- Press `o` to open comic in system image viewer
- Progress polling from cache (decoupled from download threads)

### Changed
- Optimized PNG metadata embedding to single-pass raw byte injection (no Pillow re-encode)
- TUI lazy-loads image widget only when viewer tab is opened

## [3.1.0] - 2026-04-12
### Added
- Embed alt text, title, source URL, and date into downloaded images (PNG tEXt, JPEG EXIF, GIF comment)
- Configurable output directory via CLI `--output`/`-o` flag and TUI input field
- CLI flags: `--mode`/`-m`, `--workers`/`-w` via argparse
- Cancel button in TUI to stop downloads mid-run
- Integration tests against real xkcd.com API

### Fixed
- Image download failures (e.g. comics 1608, 1668) now correctly reported as skipped

## [3.0.0] - 2026-04-12
### Changed
- Replace raw `threading.Thread` with `ThreadPoolExecutor` and per-thread sessions
- Mode selection uses `"full"`/`"quick"` strings instead of booleans
- Add `DownloadProgress` dataclass and progress callback support
- Add retry with exponential backoff on request failures
- Add request timeouts
- Quick mode correctly handles archives with fewer than 100 comics
- Replace `setup.py` and `requirements.txt` with `pyproject.toml` and `uv`
- Add ruff linting and formatting
- Add pre-commit hooks
- Add GitHub Actions CI (lint + test on Python 3.13, 3.14, 3.14t)
- Add `__main__.py` and `xkcd-archiver` console entry point
- Require Python 3.13+

### Added
- Textual TUI (`xkcd-tui`) with progress bar, log, mode/worker selection
- Test suite for downloader and CLI modules
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`

### Fixed
- Image download failures (e.g. comics 1608, 1668) now correctly reported as skipped instead of downloaded

### Removed
- `setup.py` (replaced by `pyproject.toml`)
- `requirements.txt` (replaced by `uv.lock`)
- `.pyup.yml` and `.whitesource` (stale configs)

### Unreleased [2.0.0] - 2019-10-24
### Added
- README.md
- CHANGELOG.md - add changelog
- helper_functions.py
- downloader.py - `Downloader` class.
- Feature not downloading the image file if the filename already exists.
- Batch file to run via shortcut on Windows, second batch file to ensure dependencies are installed before run.
- Implement Pathlib
### Changed
- Moved informal changelog to CHANGELOG.md, reformat, from now on use to semver.
- Refactor core algorithm into class Downloader.
- Refactor CLI logic into functions. 
- Move `__version__` to canonical location in downloadXKCD.py
 
## [1.2.2]
### Changed
- Changed if/if not logic at start of threaded_download to if/else

## [1.2.1]
### Changed
- Refactored thread setup to separate quick/full modes
- Depreciate json title use in filename.
    revert to using file names from json as filename to save image
- Quick mode only downloads last 100 comics
- Modified run_mode to eliminate try/except necessity,
    added Q to quit option.
- Made default parameter download_comics: run_mode=True
    (for potential future use)
- Removed unused latest_comic param from comic_json

## [1.2.0]
### Changed
- Implement json
