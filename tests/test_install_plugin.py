"""Tests for duckbrain install-plugin bundling and install logic."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

import pytest

from duckbrain import install_plugin
from duckbrain.install_plugin import (
    detect_installed_editors,
    get_post_install_step,
    install_to_editor,
)


def test_bundled_plugin_files_exist() -> None:
    plugin_dir = files("duckbrain").joinpath("plugin/claude")
    assert (plugin_dir / ".claude-plugin" / "plugin.json").is_file()
    assert (plugin_dir / "hooks" / "hooks.json").is_file()


def test_detect_installed_editors_finds_claude_code(tmp_path: Path) -> None:
    fake_plugin_dir = tmp_path / "duckbrain-local"
    fake_plugin_dir.mkdir()
    (fake_plugin_dir / ".claude-plugin").mkdir()
    (fake_plugin_dir / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")

    with patch.dict(
        install_plugin.EDITOR_REGISTRY,
        {
            "claude-code": install_plugin.EditorTarget(
                default_path=fake_plugin_dir,
                post_install_step="claude plugin update duckbrain@duckbrain-local",
                status="supported",
                bundle_name="claude",
            )
        },
    ):
        found = detect_installed_editors()
    assert found == [("claude-code", fake_plugin_dir)]


def test_install_to_editor_copies_files(tmp_path: Path) -> None:
    dest = tmp_path / "claude-plugins" / "duckbrain-local"
    install_to_editor("claude-code", dest)
    assert (dest / ".claude-plugin" / "plugin.json").exists()
    assert (dest / "hooks" / "hooks.json").exists()


def test_install_to_editor_is_idempotent(tmp_path: Path) -> None:
    dest = tmp_path / "claude-plugins" / "duckbrain-local"
    install_to_editor("claude-code", dest)
    install_to_editor("claude-code", dest)
    assert (dest / "hooks" / "hooks.json").exists()


def test_install_to_editor_returns_post_install_step() -> None:
    step = get_post_install_step("claude-code")
    assert "claude plugin update" in step


def test_install_to_unknown_editor_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported editor"):
        install_to_editor("notepad", tmp_path / "nowhere")


def test_full_install_flow_claude_code(tmp_path: Path) -> None:
    """Install to a temp dir, verify all expected files are present and non-empty."""
    import json

    dest = tmp_path / "duckbrain-local"
    install_to_editor("claude-code", dest)
    assert (dest / ".claude-plugin" / "plugin.json").stat().st_size > 0
    assert (dest / "hooks" / "hooks.json").stat().st_size > 0
    data = json.loads((dest / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert "version" in data
    assert data["version"] != "unknown"
