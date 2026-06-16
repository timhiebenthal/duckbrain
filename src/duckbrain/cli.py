"""DuckBrain CLI entry point — MCP server or install-plugin subcommand."""

from __future__ import annotations

import sys

from duckbrain import install_plugin, server


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] == "serve":
        server.main()
    elif args[0] == "install-plugin":
        install_plugin.run(args)
    else:
        print(f"Unknown subcommand: {args[0]}", file=sys.stderr)
        sys.exit(1)
