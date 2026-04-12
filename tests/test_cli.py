"""Tests for the CLI module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from XKCD_archiver.downloadXKCD import (
    env_indicator,
    is_venv,
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
        assert run_mode_selector() is True

    def test_quick_mode(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "0")
        assert run_mode_selector() is False

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
            timed_run(mock_downloader)
        mock_downloader.download_comics.assert_called_once()
        output = capsys.readouterr().out
        assert "5.50 seconds" in output

    def test_prints_minutes_when_over_60(self, capsys):
        mock_downloader = MagicMock()
        with patch("XKCD_archiver.downloadXKCD.time") as mock_time:
            mock_time.time.side_effect = [0.0, 125.0]
            timed_run(mock_downloader)
        output = capsys.readouterr().out
        assert "2 minutes" in output


class TestScriptTagline:
    def test_prints_tagline(self, capsys):
        script_tagline()
        output = capsys.readouterr().out
        assert "xkcd.com" in output


class TestEnvIndicator:
    def test_in_venv(self, capsys, monkeypatch):
        monkeypatch.setattr("XKCD_archiver.downloadXKCD.is_venv", lambda: True)
        env_indicator()
        assert "virtualenv" in capsys.readouterr().out

    def test_not_in_venv(self, capsys, monkeypatch):
        monkeypatch.setattr("XKCD_archiver.downloadXKCD.is_venv", lambda: False)
        env_indicator()
        assert "outside" in capsys.readouterr().out
