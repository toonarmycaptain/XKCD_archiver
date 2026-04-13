"""Tests for the CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from XKCD_archiver.downloadXKCD import (
    env_indicator,
    is_venv,
    parse_args,
    run_mode_selector,
    script_tagline,
    timed_run,
)


class TestIsVenv:
    def test_detects_real_prefix(self, monkeypatch):
        monkeypatch.setattr(sys, "real_prefix", "/usr", raising=False)
        assert is_venv() is True

    def test_detects_base_prefix_mismatch(self, monkeypatch):
        monkeypatch.delattr(sys, "real_prefix", raising=False)
        monkeypatch.setattr(sys, "base_prefix", "/usr")
        monkeypatch.setattr(sys, "prefix", "/home/user/.venv")
        assert is_venv() is True

    def test_not_in_venv(self, monkeypatch):
        monkeypatch.delattr(sys, "real_prefix", raising=False)
        monkeypatch.setattr(sys, "base_prefix", "/usr")
        monkeypatch.setattr(sys, "prefix", "/usr")
        assert is_venv() is False


class TestRunModeSelector:
    def test_full_mode(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        assert run_mode_selector() == "full"

    def test_quick_mode(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "0")
        assert run_mode_selector() == "quick"

    def test_quit(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "q")
        with pytest.raises(SystemExit):
            run_mode_selector()

    def test_quit_uppercase(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "Q")
        with pytest.raises(SystemExit):
            run_mode_selector()


class TestTimedRun:
    def test_prints_seconds(self, capsys):
        mock_downloader = MagicMock()
        with patch("XKCD_archiver.downloadXKCD.time") as mock_time:
            mock_time.time.side_effect = [0.0, 5.5]
            timed_run(mock_downloader, "full")
        mock_downloader.download_comics.assert_called_once_with(mode="full")
        output = capsys.readouterr().out
        assert "5.50 seconds" in output

    def test_prints_minutes_when_over_60(self, capsys):
        mock_downloader = MagicMock()
        with patch("XKCD_archiver.downloadXKCD.time") as mock_time:
            mock_time.time.side_effect = [0.0, 125.0]
            timed_run(mock_downloader, "quick")
        output = capsys.readouterr().out
        assert "2 minutes" in output


class TestScriptTagline:
    def test_prints_tagline(self, capsys):
        script_tagline()
        output = capsys.readouterr().out
        assert "xkcd.com" in output


class TestParseArgs:
    def test_defaults(self):
        args = parse_args([])
        assert args.mode is None
        assert args.output == Path("xkcd")
        assert args.workers == 10

    def test_mode_quick(self):
        args = parse_args(["--mode", "quick"])
        assert args.mode == "quick"

    def test_mode_full(self):
        args = parse_args(["-m", "full"])
        assert args.mode == "full"

    def test_output(self, tmp_path):
        args = parse_args(["--output", str(tmp_path / "comics")])
        assert args.output == tmp_path / "comics"

    def test_output_short(self, tmp_path):
        args = parse_args(["-o", str(tmp_path / "comics")])
        assert args.output == tmp_path / "comics"

    def test_workers(self):
        args = parse_args(["--workers", "5"])
        assert args.workers == 5

    def test_all_flags(self, tmp_path):
        args = parse_args(["-m", "quick", "-o", str(tmp_path), "-w", "20"])
        assert args.mode == "quick"
        assert args.output == tmp_path
        assert args.workers == 20


class TestEnvIndicator:
    def test_in_venv(self, capsys, monkeypatch):
        monkeypatch.setattr("XKCD_archiver.downloadXKCD.is_venv", lambda: True)
        env_indicator()
        assert "virtualenv" in capsys.readouterr().out

    def test_not_in_venv(self, capsys, monkeypatch):
        monkeypatch.setattr("XKCD_archiver.downloadXKCD.is_venv", lambda: False)
        env_indicator()
        assert "outside" in capsys.readouterr().out
