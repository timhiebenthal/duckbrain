"""Install bundled editor plugin files to disk."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path


@dataclass(frozen=True)
class EditorTarget:
    default_path: Path
    post_install_step: str
    status: str
    bundle_name: str


EDITOR_REGISTRY: dict[str, EditorTarget] = {
    "claude-code": EditorTarget(
        default_path=Path.home() / ".local/share/claude-plugins/duckbrain-local",
        post_install_step="claude plugin update duckbrain@duckbrain-local",
        status="supported",
        bundle_name="claude",
    ),
    "opencode": EditorTarget(
        default_path=Path.home() / ".local/share/opencode/plugins/duckbrain",
        post_install_step="TBD",
        status="tbd",
        bundle_name="opencode",
    ),
    "cursor": EditorTarget(
        default_path=Path.home() / ".cursor/plugins/duckbrain",
        post_install_step="TBD",
        status="tbd",
        bundle_name="cursor",
    ),
}


def get_plugin_dir(editor_bundle: str) -> Path:
    ref = files("duckbrain").joinpath(f"plugin/{editor_bundle}")
    with as_file(ref) as path:
        return path


def detect_installed_editors() -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for slug, target in EDITOR_REGISTRY.items():
        if target.default_path.exists():
            found.append((slug, target.default_path))
    return found


def get_post_install_step(editor: str) -> str:
    target = EDITOR_REGISTRY.get(editor)
    if target is None or target.status != "supported":
        raise ValueError(f"Unsupported editor: {editor}")
    return target.post_install_step


def install_to_editor(editor: str, dest: Path, force: bool = False) -> None:
    del force  # reserved for future overwrite guard
    target = EDITOR_REGISTRY.get(editor)
    if target is None or target.status != "supported":
        raise ValueError(f"Unsupported editor: {editor}")

    src_ref = files("duckbrain").joinpath(f"plugin/{target.bundle_name}")
    dest.mkdir(parents=True, exist_ok=True)
    with as_file(src_ref) as src:
        shutil.copytree(src, dest, dirs_exist_ok=True)


def run(argv: list[str] | None = None) -> None:
    args_list = list(argv or sys.argv[1:])
    if args_list and args_list[0] == "install-plugin":
        args_list = args_list[1:]

    parser = argparse.ArgumentParser(prog="duckbrain install-plugin")
    parser.add_argument("--editor", help="Editor slug (e.g. claude-code)")
    parser.add_argument("--dest", type=Path, help="Destination directory")
    parser.add_argument("--force", action="store_true", help="Overwrite without prompting")
    args = parser.parse_args(args_list)

    if args.dest:
        if not args.editor:
            print("error: --dest requires --editor", file=sys.stderr)
            sys.exit(1)
        install_to_editor(args.editor, args.dest, force=args.force)
        print(f"✓ Copied plugin files to {args.dest}")
        print(f"  Next step: {get_post_install_step(args.editor)}")
        return

    if args.editor:
        target = EDITOR_REGISTRY.get(args.editor)
        if target is None:
            print(f"error: unknown editor {args.editor!r}", file=sys.stderr)
            sys.exit(1)
        if target.status != "supported":
            print(f"error: editor {args.editor!r} is not supported yet", file=sys.stderr)
            sys.exit(1)
        install_to_editor(args.editor, target.default_path, force=args.force)
        print(f"✓ Copied plugin files to {target.default_path}")
        print(f"  Next step: {target.post_install_step}")
        return

    detected = detect_installed_editors()
    if not detected:
        print("No duckbrain plugin installations detected.")
        print("Use: duckbrain install-plugin --editor claude-code")
        sys.exit(1)

    print("Detected duckbrain plugin installations:")
    for slug, path in detected:
        print(f"  {slug}  {path}")
    answer = input("Install? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        print("Aborted.")
        return

    for slug, path in detected:
        target = EDITOR_REGISTRY[slug]
        if target.status != "supported":
            print(f"  Skipping unsupported editor: {slug}")
            continue
        install_to_editor(slug, path, force=args.force)
        print(f"✓ Copied plugin files to {path}")
        print(f"  Next step: {target.post_install_step}")
