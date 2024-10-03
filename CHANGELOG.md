# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
