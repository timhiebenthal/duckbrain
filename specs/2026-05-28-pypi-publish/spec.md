# PyPI Publishing & Repository Readiness

## Overview

Prepare `duckbrain` for public distribution on PyPI. This covers package metadata, code quality tooling, CI/CD workflows, and repository standards so the project is trustworthy, discoverable, and maintainable by others.

**Current state**: pyproject.toml has placeholder description, overly strict Python version (`>=3.14`), no license/classifiers/keywords/urls. No CI, no linting, no pre-commit hooks, no CHANGELOG.

**Target state**: pip-installable package (`pip install duckbrain`), green CI on every push, linted and type-checked code, semantic versioning with changelog.

**Borrowed from [trellis-datamodel](https://github.com/timhiebenthal/trellis-datamodel)**: pyproject.toml metadata patterns (classifiers, urls, keywords), release workflow pattern (auto-detect version bump from pyproject.toml diff, auto-skip if unchanged), trusted PyPI publishing. Duckbrain is simpler — no frontend, no dbt, no CLA, **MIT license** (trellis is AGPL-3.0).

## Requirements

### Functional Requirements

#### Package Metadata (pyproject.toml)

- **FR-PKG1**: Real description. "DuckDB-backed MCP memory server for Obsidian vaults — structured search, read, and write access for AI coding agents."
- **FR-PKG2**: License field — `license = "MIT"` or `license = { text = "MIT" }`. Also create a `LICENSE` file with MIT license text.
- **FR-PKG3**: PyPI classifiers. At minimum: `License :: OSI Approved :: MIT License`, `Programming Language :: Python :: 3`, `Programming Language :: Python :: 3.10` through `3.13`, `Topic :: Software Development :: Libraries :: Python Modules`, `Intended Audience :: Developers`, `Framework :: MCP`.
- **FR-PKG4**: Keywords — `["mcp", "obsidian", "memory", "knowledge-base", "duckdb", "ai-agent"]`.
- **FR-PKG5**: Repository URLs — `[project.urls]` table with `Repository`, `Issues`, `Homepage`.
- **FR-PKG6**: Lower `requires-python` from `>=3.14` to `>=3.10`. The codebase uses only `str | None` syntax (3.10+). No 3.14-specific features are used.

#### Code Quality

- **FR-CQ1**: ruff for linting + formatting. Add as dev dependency. Configure in `pyproject.toml` under `[tool.ruff]`. Target Python 3.10. Enable pyflakes, pycodestyle, isort.
- **FR-CQ2**: ruff format as the single formatter (no black, no isort — ruff handles both).
- **FR-CQ3**: mypy for static type checking. Add as dev dependency. Configure `[tool.mypy]` with `strict = false`, `check_untyped_defs = true`. Run on `src/duckbrain/` only.
- **FR-CQ4**: pre-commit hooks — ruff check, ruff format, mypy. `.pre-commit-config.yaml` at repo root.
- **FR-CQ5**: All existing code passes ruff check, ruff format, and mypy with zero errors.

#### CI/CD (GitHub Actions)

- **FR-CI1**: Test workflow — `.github/workflows/test.yml`. Triggered on push to `main` and PRs. Matrix: Python 3.10, 3.11, 3.12, 3.13. Steps: checkout, setup uv, uv sync, uv run pytest.
- **FR-CI2**: Lint workflow — `.github/workflows/lint.yml`. Triggered same as test. Runs ruff check, ruff format --check, mypy. Fails on violations.
- **FR-CI3**: Publish workflow — `.github/workflows/publish.yml`. Triggered on push to `main` only when `pyproject.toml` version field differs from previous commit (detect auto-skip, same as trellis). Steps: resolve version, check for change, GitHub Release via `gh release create`, `uv build`, `pypa/gh-action-pypi-publish` with trusted publishing (OIDC).

#### Documentation

- **FR-DOC1**: CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format. Initial entry for v0.1.0.
- **FR-DOC2**: README already complete — no changes needed.
- **FR-DOC3**: CONTRIBUTING.md — dev setup, run tests, run linting, TDD requirement. Simplified vs trellis (no CLA, no frontend).
- **FR-DOC4**: AGENTS.md at repo root — coding conventions for AI agents contributing: TDD iron law, codebase pipeline (scanner→indexer→tools→server), testing conventions (`uv run pytest`), how to add new MCP tools. Ensures Claude Code, OpenCode, Cursor agents follow the same patterns.
- **FR-DOC5**: MIT LICENSE file.

#### Versioning

- **FR-VER1**: Semantic versioning — `0.1.0` is correct (pre-stable).
- **FR-VER2**: Tag format: `v0.1.0`. Pushing version bump commit to main triggers publish.

### Non-Functional Requirements

- **NFR-1**: CI must complete in <3 minutes.
- **NFR-2**: Zero warnings from ruff check and mypy on `src/duckbrain/`.
- **NFR-3**: ruff format produces deterministic output (line-length = 100).
- **NFR-4**: `uv build` produces `.tar.gz` (sdist) and `.whl`.

## Scope

### In Scope

- pyproject.toml metadata fixes (description, license, classifiers, keywords, urls, python version)
- ruff: linting + formatting + import sorting
- mypy: type checking on source
- pre-commit hooks: ruff + mypy
- GitHub Actions: test, lint, publish (PyPI trusted publishing)
- CHANGELOG.md, CONTRIBUTING.md, AGENTS.md, LICENSE
- Fix any code issues found by linting/type checking
- `.gitattributes` for line endings

### Out of Scope

- Coverage thresholds, Dependabot, Codecov, security scanning
- Documentation site (ReadTheDocs, mkdocs)
- Docker, Homebrew
- macOS/Windows CI runners
- CLA (not needed for MIT license)
- `requires-python <3.10`

## Approach

### Technical Approach

**Borrowed from trellis-datamodel (proven patterns):**

| Pattern | Source | Adaptation |
|---------|--------|------------|
| `pyproject.toml` metadata | `trellis-datamodel/pyproject.toml` | Same classifiers format, `[project.urls]` structure, keywords |
| Release workflow | `.github/workflows/release.yml` | Same version-diff logic, auto-skip if no bump. Simplified: no frontend build |
| Trusted publishing | `pypa/gh-action-pypi-publish@release/v1` | Identical — OIDC, no tokens |
| CHANGELOG format | `trellis-datamodel/CHANGELOG.md` | Same Keep a Changelog format |
| CONTRIBUTING.md | `trellis-datamodel/CONTRIBUTING.md` | Simplified — no CLA, no Node.js |

**Added beyond trellis (quality gates):**

| Pattern | Why |
|---------|-----|
| ruff lint + format | Not in trellis CI — duckbrain has this from day one |
| mypy type check | Zero tolerance for type errors |
| pre-commit hooks | Automates quality locally |
| Python version matrix | trellis tests 3.11 only; duckbrain tests 3.10-3.13 |
| AGENTS.md | Agent coding conventions — unique to AI-native projects |

**pyproject.toml changes** — minimal, file already well-formed.

**CI caching** — `astral-sh/setup-uv` action handles cache automatically.

**Trusted publishing** — no token. GitHub OIDC authenticates with PyPI. One-time setup in PyPI project settings.

## Dependencies

### New Dev Dependencies
- `ruff` — linting + formatting
- `mypy` — type checking
- `pre-commit` — git hooks

### External Services
- PyPI — trusted publisher setup
- GitHub Actions — CI/CD runner

### Files Created
- `.github/workflows/test.yml`, `lint.yml`, `publish.yml`
- `.pre-commit-config.yaml`
- `CHANGELOG.md`, `CONTRIBUTING.md`, `AGENTS.md`, `LICENSE`
- `.gitattributes`

### Files Modified
- `pyproject.toml` — metadata + ruff config + mypy config

## Success Criteria

1. **Builds**: `uv build` produces sdist and wheel.
2. **Lints clean**: `ruff check .` and `ruff format --check .` exit 0.
3. **Types check**: `mypy src/duckbrain/` exits 0.
4. **Tests pass**: `uv run pytest` — all 59 pass.
5. **CI green**: push to main triggers test + lint, both pass.
6. **Publish works**: version bump commit → auto-release to PyPI.
7. **Install works**: `pip install duckbrain` succeeds.
8. **pre-commit works**: `pre-commit run --all-files` passes.

## Notes

- **MIT license** — no CLA needed. MIT is permissive, compatible with all use cases.
- **AGENTS.md** — critical for AI-native projects. Without it, different AI agents may produce inconsistent code. This file ensures Claude Code, OpenCode, and Cursor all follow the same TDD pattern, file structure, and conventions.
- **Python 3.10 floor**: `str | None` (PEP 604) requires 3.10+. 3.9 would need `from __future__ import annotations`.
- **mypy**: `strict = false` because MCP library may lack complete type stubs.
- **ruff line length**: 100 chars.
- **No versioning automation**: Manual bumps (edit pyproject.toml, update CHANGELOG, commit). `bump-my-version` can be added later.
- **Trusted publisher setup**: One-time manual step in PyPI — add GitHub repo as trusted publisher.
