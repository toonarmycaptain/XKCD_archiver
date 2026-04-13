# XKCD_archiver

Downloads every single XKCD comic.

Uses `ThreadPoolExecutor` with per-thread connection pooling for fast concurrent downloads. Checks if each comic already exists before downloading.

## Installation

```bash
uv sync
```

## Usage

### CLI
```bash
uv run xkcd-archiver                              # interactive mode selector
uv run xkcd-archiver --mode full                   # skip interactive prompt
uv run xkcd-archiver --mode quick --output ~/comics --workers 20
```

### TUI
```bash
uv run xkcd-tui
# or
uv run python -m XKCD_archiver --tui
```

The TUI provides a progress bar, live download log, configurable worker count, output path, and a cancel button.

## Features

- Alt text, title, source URL, and date embedded into downloaded images
- Configurable output directory (`--output` / `-o`)
- Configurable concurrency (`--workers` / `-w`)

## Run modes

- **Full mode**: Checks every comic, downloads any missing.
- **Quick mode**: Checks the latest 100 comics, downloads any missing.

## Development

```bash
uv sync                        # install deps
uv run pytest                  # run tests
uv run ruff check .            # lint
uv run ruff format --check .   # format check
```

Requires Python 3.13+.

Derived from original project: https://automatetheboringstuff.com/chapter11/
