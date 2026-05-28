# PyPI Publishing & Repository Readiness — Implementation Tasks

## Overview

Make duckbrain pip-installable with proper metadata, code quality tooling, CI/CD, and documentation. Borrows proven patterns from trellis-datamodel (release workflow, trusted publishing). MIT license.

**Goal**: `pip install duckbrain`, green CI, linted + type-checked code, semantic versioning.

---

## SPRINT 1: Metadata + Code Quality + Build Verification

All changes that touch `pyproject.toml` or require code fixes. Single stream (sequential) to avoid file conflicts.

### Task 1: pyproject.toml metadata

- [ ] **Update pyproject.toml metadata**
  - Change `description` to `"DuckDB-backed MCP memory server for Obsidian vaults — structured search, read, and write access for AI coding agents."`
  - Change `requires-python` from `">=3.14"` to `">=3.10"`
  - Add `license = "MIT"`
  - Add `classifiers` list (see FR-PKG3 in spec)
  - Add `keywords` list (see FR-PKG4 in spec)
  - Add `[project.urls]` table with Repository, Issues, Homepage (see FR-PKG5)
  - **Verify**: `uv run python -c "from duckbrain import PageMetadata; print('OK')"` — imports still work

### Task 2: LICENSE

- [ ] **Create MIT LICENSE file**
  - Copy from trellis or use standard MIT text. Replace copyright year/holder with `2026 Tim Hiebenthal`.
  - **Verify**: file exists, contains "MIT License" and "Permission is hereby granted"

### Task 3: Add ruff + mypy dev deps and config

- [ ] **Install dev deps and configure tools**
  - `uv add --dev ruff mypy`
  - Add `[tool.ruff]` section to pyproject.toml:
    - `target-version = "py310"`
    - `line-length = 100`
  - Add `[tool.ruff.lint]` with `select = ["E", "F", "I"]` (pycodestyle, pyflakes, isort)
  - Add `[tool.mypy]` with `python_version = "3.10"`, `strict = false`, `check_untyped_defs = true`, `files = ["src/duckbrain"]`
  - **Verify**: `uv run ruff check src/duckbrain/ 2>&1` runs (may show errors — those are for Task 4)

### Task 4: Fix all ruff + mypy violations

- [ ] **Fix lint and type errors**
  - `uv run ruff check src/duckbrain/` — fix all errors (import order, unused imports, line length, etc.)
  - `uv run ruff format src/duckbrain/` — auto-format all files
  - `uv run mypy src/duckbrain/` — fix all type errors
  - **Verify**:
    - `uv run ruff check src/duckbrain/` — exits 0, no output
    - `uv run ruff format --check src/duckbrain/` — exits 0, "1 file already formatted" × N
    - `uv run mypy src/duckbrain/` — exits 0, no errors
    - `uv run pytest` — all 59 tests still pass

### Task 5: pre-commit hooks

- [ ] **Create .pre-commit-config.yaml**
  - `uv add --dev pre-commit`
  - Create `.pre-commit-config.yaml` with three hooks: ruff check, ruff format, mypy (local repo hooks, not remote)
  - **Verify**: `uv run pre-commit run --all-files` passes all 3 hooks

### Task 6: Build verification

- [ ] **Verify package builds**
  - `uv build` — produces `dist/duckbrain-0.1.0.tar.gz` and `dist/duckbrain-0.1.0-py3-none-any.whl`
  - Add `dist/` to `.gitignore` if not already there
  - **Verify**: `uv run pytest` — all 59 tests pass (final check before SP1 commit)

---

## SPRINT 2: CI/CD Workflows + Documentation + AGENTS.md

All parallel — touch different files.

### Stream A: GitHub Actions workflows

⚠️ Independent of Streams B and C.

- [ ] **Create `.github/workflows/test.yml`**
  - Triggers: `push` to `main`, `pull_request`
  - Matrix: `python-version: ["3.10", "3.11", "3.12", "3.13"]`
  - Steps: checkout → `astral-sh/setup-uv` → `uv sync` → `uv run pytest`
  - **Verify**: file is valid YAML, workflow name is "Test"

- [ ] **Create `.github/workflows/lint.yml`**
  - Triggers: same as test
  - Single Python version (3.13)
  - Steps: checkout → `astral-sh/setup-uv` → `uv sync` → `uv run ruff check src/duckbrain/` → `uv run ruff format --check src/duckbrain/` → `uv run mypy src/duckbrain/`
  - **Verify**: file is valid YAML, workflow name is "Lint"

- [ ] **Create `.github/workflows/publish.yml`**
  - Borrow pattern from `trellis-datamodel/.github/workflows/release.yml`:
    - Trigger: `push` to `main` (no workflow_dispatch — simpler)
    - Version resolution: diff `pyproject.toml` between `HEAD~1` and `HEAD`, extract version, skip if unchanged
    - Skip if tag `v{version}` already exists
    - Run `scripts/check_version.py` to validate version matches tag (copied from trellis)
    - GitHub Release via `gh release create`
    - `uv build`
    - `pypa/gh-action-pypi-publish@release/v1` with trusted publishing
  - Adapt for duckbrain: no Node.js steps, no frontend build. Same OIDC trusted publishing.
  - **Verify**: file is valid YAML, workflow name is "Release & Publish"

- [ ] **Create `scripts/check_version.py`** (version-tag alignment check)
  - Copy from `trellis-datamodel/scripts/check_version.py` (71 lines, no trellis-specific code)
  - Reads version from `pyproject.toml`, compares against `RELEASE_TAG` env var
  - Used by publish workflow to prevent mismatched tags
  - **Verify**: `RELEASE_TAG=v0.1.0 uv run python scripts/check_version.py` → "Version check passed"

### Stream B: Documentation

⚠️ Independent of Streams A and C.

- [ ] **Create CHANGELOG.md**
  - Format: Keep a Changelog, semantic versioning
  - Initial entry for v0.1.0 listing all features: vault_info, vault_search, vault_read, vault_write (wiki + daily), DuckDB FTS, daily scanning, date fields, MCP stdio server, E2E tests
  - **Verify**: file exists, formatted correctly, no placeholder text

- [ ] **Create CONTRIBUTING.md**
  - Dev setup: `git clone`, `uv sync`, `uv run pytest`
  - TDD requirement: no production code without failing test
  - Run linting: `uv run ruff check .`, `uv run mypy src/duckbrain/`
  - Simplified vs trellis: no CLA, no Node.js/frontend
  - **Verify**: file exists, covers setup + testing + linting

- [ ] **Create .gitattributes**
  - `* text=auto` — normalize line endings
  - `*.py text eol=lf` — Python files always LF
  - `*.md text eol=lf` — Markdown files always LF
  - **Verify**: file exists with correct content

### Stream C: AGENTS.md

⚠️ Independent of Streams A and B.

- [ ] **Create AGENTS.md**
  - Pattern for AI agents contributing to duckbrain:
    - TDD iron law: no production code without failing test first
    - Codebase pipeline: `scanner → indexer → writer → tools → server`
    - How to add a new MCP tool: create `tools/vault_X.py` → implement `handle_vault_X()` → register in `server.py` with `@server.tool()` → write tests in `tests/test_vault_X.py`
    - Testing: `uv run pytest`, `uv run ruff check`, `uv run mypy src/duckbrain/`
    - Commit conventions: conventional commits
    - Never edit `.env` files
  - **Verify**: file exists, covers TDD, codebase structure, and contribution flow

---

## SPRINT 3: Final Verification

Single stream — everything depends on SPRINT 2 being complete.

### Task 7: Full verification

- [ ] **Run all quality checks**
  - `uv run ruff check src/duckbrain/` → 0 errors
  - `uv run ruff format --check src/duckbrain/` → all formatted
  - `uv run mypy src/duckbrain/` → 0 errors
  - `uv run pytest` → 59 passed
  - `uv run pre-commit run --all-files` → all hooks pass
  - `uv build` → produces sdist + wheel
  - `pip install dist/duckbrain-0.1.0-py3-none-any.whl` → `duckbrain` command available

- [ ] **Push to GitHub and verify CI**
  - Commit all changes, push to `main`
  - Verify test + lint workflows pass on GitHub Actions
  - Publish workflow should skip (version unchanged)

- [ ] **Update CHANGELOG with today's entry**
  - Add `## [0.1.0] - 2026-05-28` with all the metadata/quality/CI additions

---

## Summary

### Sprint Overview

| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| 1 | Metadata + Quality | 6 (T1-T6) | Single (sequential) |
| 2 | CI/CD + Docs + AGENTS | 3 streams | A (workflows), B (docs), C (AGENTS.md) |
| 3 | Final verification | 1 (T7) | Single |

### Total Effort
- **SPRINTS**: 3
- **TASKS**: 10 (6 + 3 streams + 1 verification)
- **Parallel streams**: Sprint 2 only (3 streams)

### Files Touched per Sprint

| Sprint | Files |
|--------|-------|
| 1 | `pyproject.toml`, `LICENSE`, `src/duckbrain/**/*.py` (lint fixes), `.pre-commit-config.yaml`, `.gitignore` |
| 2A | `.github/workflows/test.yml`, `lint.yml`, `publish.yml`, `scripts/check_version.py` |
| 2B | `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitattributes` |
| 2C | `AGENTS.md` |
| 3 | None (verification only) |

## Notes

- **TDD not applicable to most of this sprint** — these are config files and documentation, not production code. The "verify" step replaces "test" for each task.
- **Code fixes in Task 4 may be non-trivial** — mypy on the MCP library may produce type errors that require `# type: ignore` comments or `cast()` calls. Expect 5-15 violations to fix.
- **Trusted publisher setup** is a manual step after the first push — not in these tasks. Go to PyPI project settings → Publishing → add `github.com/timhiebenthal/duckbrain` as trusted publisher.
- **publish.yml** won't trigger until you bump the version and push. That's correct — it auto-detects version changes. First publish is manual: bump to `0.1.0` (already set), create `CHANGELOG.md` entry, commit, push, tag `v0.1.0`, or trigger manually.
