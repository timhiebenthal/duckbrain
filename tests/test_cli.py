"""Tests for duckbrain CLI dispatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from duckbrain import cli


def test_no_args_starts_mcp_server(monkeypatch: pytest.MonkeyPatch) -> None:
    server_main = MagicMock()
    monkeypatch.setattr(cli.server, "main", server_main)
    cli.main([])
    server_main.assert_called_once()


def test_serve_subcommand_starts_mcp_server(monkeypatch: pytest.MonkeyPatch) -> None:
    server_main = MagicMock()
    monkeypatch.setattr(cli.server, "main", server_main)
    cli.main(["serve"])
    server_main.assert_called_once()


def test_install_plugin_subcommand_calls_run(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock()
    monkeypatch.setattr(cli.install_plugin, "run", run)
    argv = ["install-plugin", "--editor", "claude-code"]
    cli.main(argv)
    run.assert_called_once_with(argv)
