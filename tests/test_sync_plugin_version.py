"""Tests for scripts/sync-plugin-version.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync-plugin-version.py"


def _run_sync(pyproject: Path, plugin_json: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SYNC_SCRIPT),
            "--pyproject",
            str(pyproject),
            "--plugin-json",
            str(plugin_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_sync_sets_version_in_plugin_json(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")

    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    plugin_json = plugin_dir / "plugin.json"
    plugin_json.write_text(
        json.dumps({"name": "duckbrain", "displayName": "DuckBrain"}),
        encoding="utf-8",
    )

    result = _run_sync(pyproject, plugin_json)
    assert result.returncode == 0, result.stderr

    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "1.2.3"
    assert data["name"] == "duckbrain"
