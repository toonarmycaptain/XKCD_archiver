"""Textual TUI for XKCD archiver."""

import time

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, ProgressBar, RichLog, Select

from XKCD_archiver.downloader import Downloader, DownloadProgress


class XKCDArchiverApp(App):
    """XKCD comic archiver TUI."""

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
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._downloaded = 0
        self._skipped = 0
        self._failed = 0
        self._total = 0
        self._downloader: Downloader | None = None
        self._running = False

    def compose(self) -> ComposeResult:
        yield Header()
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
            yield Button("Start", id="start-btn", variant="primary")
        with Vertical(id="progress-area"):
            yield ProgressBar(id="progress", total=100, show_eta=True)
        yield Label("", id="stats")
        yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-btn":
            if self._running:
                self._cancel_download()
            else:
                self._start_download()

    def _start_download(self) -> None:
        mode_select = self.query_one("#mode-select", Select)
        workers_input = self.query_one("#workers-input", Input)
        start_btn = self.query_one("#start-btn", Button)

        mode = str(mode_select.value)
        try:
            workers = int(workers_input.value)
            workers = max(1, min(workers, 50))
        except ValueError:
            workers = 10

        self._running = True
        start_btn.label = "Cancel"
        start_btn.variant = "error"

        self._downloaded = 0
        self._skipped = 0
        self._failed = 0
        self._total = 0

        log = self.query_one("#log", RichLog)
        log.clear()
        log.write(f"Starting {mode} mode with {workers} workers...")

        self._run_download(mode, workers)

    def _cancel_download(self) -> None:
        if self._downloader:
            self._downloader.cancel()
        log = self.query_one("#log", RichLog)
        log.write("[yellow]Cancelling...[/]")

    @work(thread=True)
    def _run_download(self, mode: str, workers: int) -> None:
        def on_progress(p: DownloadProgress) -> None:
            self.call_from_thread(self._update_progress, p)

        self._downloader = Downloader(
            max_workers=workers,
            progress_callback=on_progress,
        )

        import requests

        session = requests.Session()
        latest = self._downloader._get_latest_comic(session)
        session.close()

        total = min(100, latest) if mode == "quick" else latest

        self.call_from_thread(self._set_total, total)

        start = time.time()
        self._downloader.download_comics(mode=mode)
        elapsed = time.time() - start

        self.call_from_thread(self._download_complete, elapsed)

    def _set_total(self, total: int) -> None:
        self._total = total
        progress = self.query_one("#progress", ProgressBar)
        progress.update(total=total, progress=0)

    def _update_progress(self, p: DownloadProgress) -> None:
        progress = self.query_one("#progress", ProgressBar)
        log = self.query_one("#log", RichLog)

        if p.status == "downloaded":
            self._downloaded += 1
            log.write(f"[green]Downloaded[/] comic {p.comic_number}")
        elif p.status == "skipped":
            self._skipped += 1
        elif p.status == "failed":
            self._failed += 1
            log.write(f"[red]Failed[/] comic {p.comic_number}: {p.error}")

        progress.advance(1)
        self._update_stats()

    def _update_stats(self) -> None:
        stats = self.query_one("#stats", Label)
        done = self._downloaded + self._skipped + self._failed
        stats.update(
            f"Downloaded: {self._downloaded}  Skipped: {self._skipped}  "
            f"Failed: {self._failed}  Progress: {done}/{self._total}"
        )

    def _download_complete(self, elapsed: float) -> None:
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

        log.write(
            f"{status} Downloaded: {self._downloaded}, Skipped: {self._skipped}, Failed: {self._failed} in {runtime}"
        )

        self._running = False
        self._downloader = None
        start_btn = self.query_one("#start-btn", Button)
        start_btn.label = "Start"
        start_btn.variant = "primary"


def main() -> None:
    app = XKCDArchiverApp()
    app.run()


if __name__ == "__main__":
    main()
