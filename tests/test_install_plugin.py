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
        clear=True,
    ):
        found = detect_installed_editors()
    assert found == [("claude-code", fake_plugin_dir)]


def test_detect_installed_editors_requires_marker(tmp_path: Path) -> None:
    """An existing OpenCode plugins dir without the plugin file is not a hit."""
    plugins_dir = tmp_path / "opencode-plugins"
    plugins_dir.mkdir()
    target = install_plugin.EditorTarget(
        default_path=plugins_dir,
        post_install_step="cd x && bun install",
        status="supported",
        bundle_name="opencode",
        marker="vault-context.ts",
    )
    with patch.dict(install_plugin.EDITOR_REGISTRY, {"opencode": target}, clear=True):
        assert detect_installed_editors() == []
        (plugins_dir / "vault-context.ts").write_text("// plugin", encoding="utf-8")
        assert detect_installed_editors() == [("opencode", plugins_dir)]


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


# ─── OpenCode bundle ─────────────────────────────────────────────────────────

# Files copied verbatim from opencode/plugins/ into the package bundle.
OPENCODE_BUNDLE_FILES = ("vault-context.ts", "vault-context-helpers.ts", "package.json")


def test_bundled_opencode_files_exist() -> None:
    plugin_dir = files("duckbrain").joinpath("plugin/opencode")
    for name in OPENCODE_BUNDLE_FILES:
        assert (plugin_dir / name).is_file(), f"missing bundled file: {name}"


def test_bundled_opencode_matches_canonical_source() -> None:
    """Guard against the bundled copy drifting from opencode/plugins/."""
    repo_root = Path(__file__).resolve().parents[1]
    canonical = repo_root / "opencode" / "plugins"
    bundled = files("duckbrain").joinpath("plugin/opencode")
    for name in OPENCODE_BUNDLE_FILES:
        assert bundled.joinpath(name).read_bytes() == (canonical / name).read_bytes(), (
            f"{name} drifted between opencode/plugins/ and the bundled copy"
        )


def test_install_to_editor_opencode_copies_files(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-plugins"
    install_to_editor("opencode", dest)
    for name in OPENCODE_BUNDLE_FILES:
        assert (dest / name).exists(), f"missing installed file: {name}"


def test_install_to_editor_opencode_is_idempotent(tmp_path: Path) -> None:
    dest = tmp_path / "opencode-plugins"
    install_to_editor("opencode", dest)
    install_to_editor("opencode", dest)
    assert (dest / "vault-context.ts").exists()


def test_opencode_post_install_step_mentions_bun_install() -> None:
    assert "bun install" in get_post_install_step("opencode")


def test_opencode_registry_is_supported() -> None:
    target = install_plugin.EDITOR_REGISTRY["opencode"]
    assert target.status == "supported"
    assert target.default_path == Path.home() / ".config/opencode/plugins"
