"""Textual TUI for XKCD archiver — download and browse comics."""

import platform
import re
import subprocess
import time
from pathlib import Path

from PIL import Image as PILImage
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from XKCD_archiver.cache import ComicCache
from XKCD_archiver.downloader import Downloader


def _comic_number(filepath: Path) -> int:
    """Extract comic number from filename like '123-comic_name.png'."""
    match = re.match(r"(\d+)-", filepath.name)
    return int(match.group(1)) if match else 0


def _read_metadata(filepath: Path) -> dict:
    """Read embedded metadata from a comic image file."""
    try:
        img = PILImage.open(filepath)
        suffix = filepath.suffix.lower()
        if suffix == ".png":
            return {
                "title": img.info.get("Title", ""),
                "alt": img.info.get("Description", ""),
                "source": img.info.get("Source", ""),
                "date": img.info.get("Creation Time", ""),
                "transcript": img.info.get("Comment", ""),
            }
        elif suffix in (".jpg", ".jpeg"):
            exif = img.getexif()
            date_raw = exif.get(0x9003, "")
            date = date_raw.replace(":", "-", 2).split(" ")[0] if date_raw else ""
            return {
                "title": "",
                "alt": exif.get(0x010E, ""),
                "source": "",
                "date": date,
                "transcript": "",
            }
        elif suffix == ".gif":
            comment = img.info.get("comment", b"")
            if isinstance(comment, bytes):
                comment = comment.decode("utf-8", errors="replace")
            return {"title": "", "alt": comment, "source": "", "date": "", "transcript": ""}
    except Exception:
        pass
    return {"title": "", "alt": "", "source": "", "date": "", "transcript": ""}


class XKCDArchiverApp(App):
    """XKCD comic archiver and viewer TUI."""

    TITLE = "XKCD Archiver"
    CSS = """
    #controls {
        height: auto;
        padding: 1 2;
    }
    #mode-select {
        width: 20;
    }
    #workers-input {
        width: 12;
    }
    #output-input {
        width: 30;
    }
    #start-btn {
        margin-left: 2;
    }
    #progress-area {
        height: auto;
        padding: 0 2;
    }
    #stats {
        height: auto;
        padding: 0 2;
        color: $text-muted;
    }
    #log {
        height: 1fr;
        margin: 1 2;
    }
    #viewer-layout {
        height: 1fr;
    }
    #comic-list {
        width: 1fr;
        height: 1fr;
    }
    #detail-panel {
        width: 2fr;
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    #image-viewer {
        height: 15;
    }
    #info-panel {
        padding: 1 2;
        overflow-y: auto;
    }
    #comic-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #comic-alt {
        margin-bottom: 1;
    }
    #comic-meta {
        color: $text-muted;
        margin-bottom: 1;
    }
    #comic-transcript {
        color: $text-muted;
    }
    #viewer-nav {
        height: auto;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("left", "previous", "Prev comic", show=True),
        Binding("right", "next", "Next comic", show=True),
        Binding("o", "open_external", "Open in viewer", show=True),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._downloaded = 0
        self._skipped = 0
        self._failed = 0
        self._total = 0
        self._downloader: Downloader | None = None
        self._downloading = False
        self._image_widget_loaded = False
        self._comics: list[Path] = []
        self._viewer_index = 0
        self._last_rowid = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Download", id="download-tab"):
                with Horizontal(id="controls"):
                    yield Label("Mode: ")
                    yield Select(
                        [("Full", "full"), ("Quick", "quick")],
                        value="full",
                        id="mode-select",
                        allow_blank=False,
                    )
                    yield Label(" Workers: ")
                    yield Input(value="10", id="workers-input", type="integer", max_length=3)
                    yield Label(" Output: ")
                    yield Input(value="xkcd", id="output-input")
                    yield Button("Start", id="start-btn", variant="primary")
                with Vertical(id="progress-area"):
                    yield ProgressBar(id="progress", total=100, show_eta=True)
                yield Label("", id="stats")
                yield RichLog(id="log", highlight=True, markup=True)
            with TabPane("Viewer", id="viewer-tab"):
                with Horizontal(id="viewer-layout"):
                    yield ListView(id="comic-list")
                    with Vertical(id="detail-panel"):
                        yield Static("", id="image-placeholder")
                        yield Label("", id="comic-title")
                        yield Label("", id="comic-alt")
                        yield Label("", id="comic-meta")
                        yield Label("", id="comic-transcript")
                        yield Label("[dim]Press 'o' to open in system viewer[/]", id="open-hint")
                with Horizontal(id="viewer-nav"):
                    yield Button("Open", id="open-btn", variant="primary")
                    yield Label("  Search: ")
                    yield Input(id="search-input", placeholder="title, alt text, transcript...")
                    yield Label("", id="nav-status")
        yield Footer()

    # --- Download tab ---

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            if self._downloading:
                self._cancel_download()
            else:
                self._start_download()
        elif event.button.id == "open-btn":
            self.action_open_external()

    def _start_download(self) -> None:
        mode_select = self.query_one("#mode-select", Select)
        workers_input = self.query_one("#workers-input", Input)
        output_input = self.query_one("#output-input", Input)
        start_btn = self.query_one("#start-btn", Button)

        mode = str(mode_select.value)
        output_dir = Path(output_input.value.strip() or "xkcd")
        try:
            workers = int(workers_input.value)
            workers = max(1, min(workers, 50))
        except ValueError:
            workers = 10

        self._downloading = True
        start_btn.label = "Cancel"
        start_btn.variant = "error"

        self._downloaded = 0
        self._skipped = 0
        self._failed = 0
        self._total = 0

        log = self.query_one("#log", RichLog)
        log.clear()
        log.write(f"Starting {mode} mode with {workers} workers, output: {output_dir}")

        self._run_download(mode, workers, output_dir)

    def action_quit(self) -> None:
        self._stop_polling()
        if self._downloader:
            self._downloader.cancel()
        self.exit()

    def _cancel_download(self) -> None:
        if self._downloader:
            self._downloader.cancel()
        log = self.query_one("#log", RichLog)
        log.write("[yellow]Cancelling...[/]")

    @work(thread=True)
    def _run_download(self, mode: str, workers: int, output_dir: Path) -> None:
        self._last_rowid = 0
        self._downloader = Downloader(
            max_workers=workers,
            output_dir=output_dir,
        )

        import requests

        session = requests.Session()
        latest = self._downloader._get_latest_comic(session)
        session.close()

        self._total = min(100, latest) if mode == "quick" else latest
        self.call_from_thread(self._start_polling)

        start = time.time()
        self._downloader.download_comics(mode=mode)
        elapsed = time.time() - start

        self.call_from_thread(self._stop_polling)
        self.call_from_thread(self._download_complete, elapsed)

    def _init_progress(self) -> None:
        self.query_one("#progress", ProgressBar).update(total=self._total, progress=0)

    def _start_polling(self) -> None:
        self._init_progress()
        self._poll_timer = self.set_interval(0.2, self._poll_progress)

    def _stop_polling(self) -> None:
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()

    def _poll_progress(self) -> None:
        if not self._downloader:
            return
        output_input = self.query_one("#output-input", Input)
        comic_dir = Path(output_input.value.strip() or "xkcd")
        cache = ComicCache(comic_dir)
        done = cache.count()

        self.query_one("#progress", ProgressBar).update(total=self._total, progress=done)
        self.query_one("#stats", Label).update(f"Cached: {done}/{self._total}")

        # Show recently downloaded comics
        new_comics, self._last_rowid = cache.recent(self._last_rowid)
        if new_comics:
            log = self.query_one("#log", RichLog)
            for c in new_comics:
                log.write(f"[green]Downloaded[/] #{c['num']}: {c['title']}")

    def _download_complete(self, elapsed: float) -> None:
        # Final progress update
        output_input = self.query_one("#output-input", Input)
        comic_dir = Path(output_input.value.strip() or "xkcd")
        cache = ComicCache(comic_dir)
        done = cache.count()
        self.query_one("#progress", ProgressBar).update(total=self._total, progress=self._total)
        self.query_one("#stats", Label).update(f"Cached: {done}/{self._total}")

        log = self.query_one("#log", RichLog)
        log.write("")
        if elapsed > 60:
            mins = elapsed // 60
            sec = elapsed - mins * 60
            runtime = f"{mins:.0f}m {sec:.1f}s"
        else:
            runtime = f"{elapsed:.1f}s"

        was_cancelled = self._downloader and self._downloader._cancel_event.is_set()
        status = "[yellow]Cancelled[/]" if was_cancelled else "[bold]Done![/]"

        log.write(f"{status} {done} comics cached in {runtime}")

        self._downloading = False
        self._downloader = None
        start_btn = self.query_one("#start-btn", Button)
        start_btn.label = "Start"
        start_btn.variant = "primary"

    # --- Viewer tab ---

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id == "viewer-tab":
            if not self._image_widget_loaded:
                self._load_image_widget()
            # Only reload if comic count changed
            output_input = self.query_one("#output-input", Input)
            comic_dir = Path(output_input.value.strip() or "xkcd")
            cache = ComicCache(comic_dir)
            current_count = cache.count()
            if current_count != len(self._comics):
                self._load_comics()
            if self._comics and self._viewer_index == 0:
                self._show_comic(0)

    def _load_image_widget(self) -> None:
        """Lazy-load textual-image widget to avoid terminal detection at startup."""
        from textual_image.widget import Image

        placeholder = self.query_one("#image-placeholder", Static)
        placeholder.display = False
        image = Image("", id="image-viewer")
        self.query_one("#detail-panel").mount(image, before=0)
        self._image_widget_loaded = True

    def _load_comics(self) -> None:
        output_input = self.query_one("#output-input", Input)
        comic_dir = Path(output_input.value.strip() or "xkcd")

        cache = ComicCache(comic_dir)
        all_comics = cache.list_all()

        list_view = self.query_one("#comic-list", ListView)
        list_view.clear()

        if not all_comics:
            self.query_one("#comic-title", Label).update(f"No comics found in {comic_dir}")
            self._comics = []
            return

        self._comics = [comic_dir / c["filename"] for c in all_comics]
        for c in all_comics:
            title = c["title"] or c["filename"]
            list_view.append(ListItem(Label(f"#{c['num']}: {title}"), name=str(c["num"])))

    def on_key(self, event) -> None:
        """Type-to-search: when list is focused, printable keys filter the list."""
        list_view = self.query_one("#comic-list", ListView)
        if not list_view.has_focus:
            return
        search_input = self.query_one("#search-input", Input)
        if event.key == "escape":
            search_input.value = ""
            self._search_comics("")
            event.prevent_default()
        elif event.key == "backspace":
            search_input.value = search_input.value[:-1]
            self._search_comics(search_input.value)
            event.prevent_default()
        elif event.is_printable and event.character:
            search_input.value += event.character
            self._search_comics(search_input.value)
            event.prevent_default()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "comic-list":
            index = event.list_view.index
            if index is not None:
                self._show_comic(index)

    def _show_comic(self, index: int) -> None:
        if not self._comics:
            return

        self._viewer_index = index % len(self._comics)
        filepath = self._comics[self._viewer_index]
        num = _comic_number(filepath)

        # Try cache first, fall back to reading file metadata
        output_input = self.query_one("#output-input", Input)
        comic_dir = Path(output_input.value.strip() or "xkcd")
        cache = ComicCache(comic_dir)
        cached = cache.get(num)

        if cached:
            title = cached.get("title", "")
            alt = cached.get("alt", "")
            date = f"{cached.get('year', '')}-{cached.get('month', '').zfill(2)}-{cached.get('day', '').zfill(2)}"
            source = f"https://xkcd.com/{num}/"
            transcript = cached.get("transcript", "")
        else:
            meta = _read_metadata(filepath)
            title = meta["title"]
            alt = meta["alt"]
            date = meta["date"]
            source = meta["source"]
            transcript = meta["transcript"]

        if self._image_widget_loaded:
            from textual_image.widget import Image

            self.query_one("#image-viewer", Image).image = str(filepath)

        self.query_one("#comic-title", Label).update(f"#{num}: {title or filepath.name}")
        self.query_one("#comic-alt", Label).update(f"Alt: {alt}" if alt else "")
        meta_parts = []
        if date and date != "--":
            meta_parts.append(f"Date: {date}")
        if source:
            meta_parts.append(source)
        self.query_one("#comic-meta", Label).update("  ".join(meta_parts))
        self.query_one("#comic-transcript", Label).update(f"Transcript: {transcript}" if transcript else "")
        self.query_one("#nav-status", Label).update(f"  Comic {self._viewer_index + 1} of {len(self._comics)}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._search_comics(event.value)
        elif event.input.id in ("workers-input", "output-input", "mode-select") and not self._downloading:
            self._start_download()

    def _search_comics(self, query: str) -> None:
        output_input = self.query_one("#output-input", Input)
        comic_dir = Path(output_input.value.strip() or "xkcd")
        list_view = self.query_one("#comic-list", ListView)
        list_view.clear()

        if not query.strip():
            # Empty search — reload full list
            self._load_comics()
            return

        cache = ComicCache(comic_dir)
        results = cache.search(query)

        self._comics = [comic_dir / r["filename"] for r in results]
        for r in results:
            list_view.append(ListItem(Label(f"#{r['num']}: {r['title']}"), name=str(r["num"])))

        status = self.query_one("#nav-status", Label)
        status.update(f"  {len(results)} results for '{query}'")

    def action_previous(self) -> None:
        if self._comics:
            self._show_comic(self._viewer_index - 1)
            self.query_one("#comic-list", ListView).index = self._viewer_index

    def action_next(self) -> None:
        if self._comics:
            self._show_comic(self._viewer_index + 1)
            self.query_one("#comic-list", ListView).index = self._viewer_index

    def action_open_external(self) -> None:
        if not self._comics:
            return
        filepath = self._comics[self._viewer_index]
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", str(filepath)])
        elif system == "Windows":
            subprocess.Popen(["start", str(filepath)], shell=True)  # noqa: S603
        else:
            subprocess.Popen(["xdg-open", str(filepath)])


def main() -> None:
    import contextlib

    app = XKCDArchiverApp()
    with contextlib.suppress(TimeoutError, OSError, KeyboardInterrupt):
        app.run()


if __name__ == "__main__":
    main()
