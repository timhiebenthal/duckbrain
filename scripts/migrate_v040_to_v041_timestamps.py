#!/usr/bin/env python3
"""One-time migration: daily-note timestamp format v0.4.0 → v0.4.1.

Run once after upgrading to v0.4.1:

    uv run python scripts/migrate_v040_to_v041_timestamps.py /path/to/vault

What it does, for each ``daily/YYYY-MM-DD.md`` in the vault:

  1. Strips a leading ``# YYYY-MM-DD`` H1 (redundant with the file path)
  2. Rewrites ``## HH:MM — Topic`` → ``## YYYY-MM-DD HH:MM — Topic``
     (using the file path's date)

Idempotent: files already in v0.4.1 format are left untouched
(their headings already start with a full timestamp, so no rewrite
matches). Safe to re-run.

Not destructive: write happens only if the regex actually changed
something. Run with ``--dry-run`` to preview.

Not in the duckbrain test suite — one-time manual tool, verified by
inspection + the user's daily file.

v0.4.1 ships this script; v0.4.2 may delete it (or keep it for
historical reference). If the script is no longer in the repo, the
migration was already done.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Heading: ## <TIME> — <TOPIC> where <TIME> is HH:MM (bare, no date).
# Must NOT match the new full-timestamp format (## YYYY-MM-DD HH:MM —).
# Negative lookbehind via the pattern's structure: require the start of
# a heading line and digits that AREN'T preceded by a date.
_BARE_TIME_HEADING_RE = re.compile(
    r"^(## )(\d{1,2}:\d{2})( — )",
    flags=re.MULTILINE,
)

# Leading H1: # YYYY-MM-DD at the very start of the file (possibly with
# trailing whitespace). The date is captured so we can verify it matches
# the file's date.
_LEADING_DATE_H1_RE = re.compile(
    r"^# \d{4}-\d{2}-\d{2}\s*\n",
)


def migrate_daily_file(filepath: Path, dry_run: bool = False) -> str:
    """Migrate a single daily file. Returns one of: migrated, unchanged,
    empty, missing, skip, or non-matching-date.

    - migrated: content was rewritten and (unless dry_run) written back
    - unchanged: content is already in v0.4.1 format
    - empty: file exists but is empty or whitespace-only
    - missing: file does not exist
    - skip: filename is not a YYYY-MM-DD date
    - non-matching-date: H1's date does not match filename date (refuse
      to touch — likely a different file or pre-migration artifact)
    """
    if not filepath.exists():
        return "missing"
    content = filepath.read_text()
    if not content.strip():
        return "empty"

    # Date comes from the filename (the source of truth).
    match = re.match(r"(\d{4}-\d{2}-\d{2})", filepath.stem)
    if not match:
        return "skip"  # Filename doesn't start with a date
    file_date = match.group(1)

    original = content

    # 1. Strip leading `# YYYY-MM-DD` H1 if present at very start.
    #    Verify the H1's date matches the filename date — if not, the
    #    H1 belongs to a different file or is a pre-migration artifact.
    #    Refuse to touch in that case to avoid corrupting data.
    h1_match = _LEADING_DATE_H1_RE.match(content)
    if h1_match:
        h1_date_match = re.search(r"\d{4}-\d{2}-\d{2}", content)
        if h1_date_match and h1_date_match.group(0) != file_date:
            return "non-matching-date"
        content = _LEADING_DATE_H1_RE.sub("", content, count=1)

    # 2. Rewrite `## HH:MM —` → `## YYYY-MM-DD HH:MM —` for every heading.
    #    Does NOT match the new full-timestamp format because that has
    #    additional digits before the time.
    #
    #    Use `\g<1>` named backrefs — `\1` is ambiguous when followed
    #    by digits: `re.sub` parses `\1` + `2` greedily as `\12`
    #    (backref 12, which doesn't exist for a 3-group pattern),
    #    and the fallback behavior is surprising. `\g<1>` is
    #    unambiguous.
    content = _BARE_TIME_HEADING_RE.sub(
        rf"\g<1>{file_date} \g<2>\g<3>",
        content,
    )

    if content == original:
        return "unchanged"
    if not dry_run:
        filepath.write_text(content)
    return "migrated"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate daily-note timestamp format v0.4.0 → v0.4.1.",
    )
    parser.add_argument(
        "vault_path",
        help="Root path of the Obsidian vault (contains daily/ directory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk.",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path)
    daily_dir = vault / "daily"
    if not daily_dir.is_dir():
        print(f"No daily/ directory in {vault}", file=sys.stderr)
        return 1

    counts: dict[str, int] = {
        "migrated": 0,
        "unchanged": 0,
        "empty": 0,
        "skip": 0,
        "non-matching-date": 0,
    }

    for filepath in sorted(daily_dir.glob("*.md")):
        result = migrate_daily_file(filepath, dry_run=args.dry_run)
        if result in counts:
            counts[result] += 1
        rel = filepath.relative_to(vault)
        if result == "migrated":
            verb = "would migrate" if args.dry_run else "migrated"
            print(f"  {verb}: {rel}")
        elif result == "non-matching-date":
            print(
                f"  REFUSED: {rel} — leading H1's date does not match "
                f"filename. Inspect manually.",
                file=sys.stderr,
            )
        elif result == "skip":
            print(f"  skip:     {rel} (filename not a date)")

    print()
    print(
        f"Summary: {counts['migrated']} migrated, "
        f"{counts['unchanged']} unchanged, "
        f"{counts['empty']} empty, "
        f"{counts['skip']} skipped, "
        f"{counts['non-matching-date']} refused"
    )
    if args.dry_run:
        print("(dry run — no files were written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
