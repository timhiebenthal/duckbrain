#!/usr/bin/env python3
"""Sync package version from pyproject.toml into claude plugin.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


def read_package_version(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not version:
        raise ValueError(f"No [project].version in {pyproject_path}")
    return str(version)


def sync_plugin_version(pyproject_path: Path, plugin_json_path: Path) -> None:
    version = read_package_version(pyproject_path)
    plugin_data = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    plugin_data["version"] = version
    plugin_json_path.write_text(
        json.dumps(plugin_data, indent=2) + "\n",
        encoding="utf-8",
    )


def default_paths() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    return (
        repo_root / "pyproject.toml",
        repo_root / "claude" / ".claude-plugin" / "plugin.json",
    )


def main(argv: list[str] | None = None) -> None:
    default_pyproject, default_plugin_json = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pyproject",
        type=Path,
        default=default_pyproject,
        help="Path to pyproject.toml",
    )
    parser.add_argument(
        "--plugin-json",
        type=Path,
        default=default_plugin_json,
        help="Path to plugin.json to update",
    )
    args = parser.parse_args(argv)

    sync_plugin_version(args.pyproject, args.plugin_json)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
