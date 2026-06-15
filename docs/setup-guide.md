# DuckBrain Setup Guide

> **DuckBrain** is a DuckDB-backed MCP memory server that gives AI coding agents
> read/write access to your Obsidian vault — structured pages, full-text search,
> and automatic indexing.

This guide walks you through setting up DuckBrain for **Claude Desktop** on any
platform. A setup script handles the details — you just need to answer a few
questions.

---

## Prerequisites

Before you start, make sure you have:

| Requirement | macOS | Linux | Windows |
|---|---|---|---|
| **Claude Desktop** | [Download](https://claude.ai/download) | [Download](https://claude.ai/download) | [Download](https://claude.ai/download) |
| **uv** (package manager) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Same | Same (inside WSL) |
| **WSL2** | — | — | [Install WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) |
| **Obsidian vault** | Any vault on your machine | Any vault | Any vault (on Windows filesystem) |

> **New to uv?** It's a fast Python package manager. The one-liner above installs
> it. No admin rights needed.

## Which Script Do I Need?

| Platform | Script | Notes |
|----------|--------|-------|
| macOS (any version) | `setup-duckbrain.sh` | Native Unix, no WSL |
| Native Linux (Ubuntu, Fedora, etc.) | `setup-duckbrain.sh` | Running Linux as your main OS |
| Windows 10/11 with WSL2 | `setup-duckbrain.ps1` | **Not the bash script!** |
| Windows (no WSL) | Not supported | Install WSL2 first |

---

## Quick Start

> **⚠️ If you're on Windows with WSL2, use the PowerShell script — NOT the bash script.**
>
> The bash script is for **native Linux** only. WSL2 users should download
> and run `setup-duckbrain.ps1` instead.
>
> **How to tell:**
> - **WSL2:** You're on Windows but using a Linux terminal inside WSL
> - **Native Linux:** You're running Linux as your main OS (Ubuntu, Fedora, etc.)
> - **macOS:** You're on a Mac

### macOS

```bash
# 1. Download the setup script
curl -O https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/setup-duckbrain.sh

# 2. Run it
bash setup-duckbrain.sh
```

That's it. The script will:

1. Check that `uv` and Claude Desktop are installed
2. Ask for your vault path (it guesses based on common locations)
3. Install DuckBrain
4. Configure Claude Desktop
5. Validate everything

**Done in ~2 minutes.**

---

### Linux

```bash
# 1. Download the setup script
curl -O https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/setup-duckbrain.sh

# 2. Run it
bash setup-duckbrain.sh
```

Same as macOS. Works on Ubuntu 20+, Fedora, and most modern distros.

---

### Windows (with WSL2)

```powershell
# 1. Download the setup script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/timhiebenthal/duckbrain/main/setup-duckbrain.ps1" -OutFile "setup-duckbrain.ps1"

# 2. Run it
.\setup-duckbrain.ps1
```

> **Note:** Run this in PowerShell (not CMD). You don't need admin rights —
> everything is installed in your user space.

**What happens step by step:**

1. Checks that WSL2 is installed and working
2. Checks that Claude Desktop is installed
3. Checks that `uv` is available inside WSL
4. Asks for your WSL username, vault path, and repo path
5. Installs DuckBrain inside WSL
6. Creates a WSL launch script (`~/bin/duckbrain-for-claude.sh`)
7. Creates a Windows batch file (`C:\Users\<you>\scripts\duckbrain.bat`)
8. Updates the Claude Desktop config file
9. Validates everything

**Done in ~5 minutes.**

---

## What the Script Does (Detailed)

The setup script does four main things:

### 1. Install DuckBrain

DuckBrain is installed via `uv tool install`, which puts the `duckbrain` command
in `~/.local/bin/duckbrain`. This keeps it isolated from other Python projects.

If you have a local clone of the DuckBrain repository (e.g., from `git clone`),
the script installs from that local copy. Otherwise, it downloads the latest
version from PyPI (the Python Package Index).

### 2. Create Launch Scripts (Windows only)

On Windows, DuckBrain runs inside WSL (Windows Subsystem for Linux). The script
creates two files to bridge the gap:

- **WSL script** (`~/bin/duckbrain-for-claude.sh`): Sets the `VAULT_PATH`
  environment variable (converted from Windows path to WSL path) and launches
  DuckBrain.

- **Batch file** (`C:\Users\<you>\scripts\duckbrain.bat`): A simple batch file
  that runs the WSL script. Claude Desktop calls this batch file.

### 3. Configure Claude Desktop

Claude Desktop reads an `mcpServers` configuration from its config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`
- **Windows:** `C:\Users\<you>\AppData\Local\Packages\Claude_*\LocalCache\Roaming\Claude\claude_desktop_config.json`

The script adds a `duckbrain` entry under `mcpServers`. If you already have
other MCP servers configured, they are preserved.

**Before modifying the config, the script backs it up** by appending
`.duckbrain-backup` to the filename. If something goes wrong, you can restore
from this backup.

### 4. Validate

The script checks that:

- The `duckbrain` command is available
- The config file has valid JSON syntax
- The `duckbrain` entry has the required fields
- The `VAULT_PATH` is set correctly

---

## How to Verify It Works

After running the setup script and restarting Claude Desktop:

1. Open a new conversation in Claude Desktop
2. Look for the **hammer 🔨 icon** in the bottom-right corner of the input area
3. Click it — you should see a list of tools including:
   - `vault_search` — Full-text search over your vault pages
   - `vault_read` — Read a page by title or filepath
   - `vault_write` — Create a page or append to today's daily note
   - `vault_context` — Load daily notes + keyword search in one call
   - `vault_info` — Vault stats: page counts, tags, last modified

You can also test from the terminal:

```bash
# Check that the binary is installed
duckbrain --help

# On Windows, test the batch file (from Command Prompt or PowerShell)
C:\Users\<you>\scripts\duckbrain.bat
# Press Ctrl+C to exit (it will hang waiting for MCP input — that's normal)
```

---

## How to Update DuckBrain

When a new version of DuckBrain is released, update it with:

**macOS / Linux:**
```bash
uv tool install duckbrain --reinstall
```

**Windows (run in PowerShell):**
```powershell
wsl -e bash -c "uv tool install duckbrain --reinstall"
```

Then restart Claude Desktop.

If you installed from a local repository, re-run the setup script instead:
```bash
bash setup-duckbrain.sh
```

---

## How to Uninstall

Run the setup script with the `--uninstall` flag:

**macOS / Linux:**
```bash
bash setup-duckbrain.sh --uninstall
```

**Windows (PowerShell):**
```powershell
.\setup-duckbrain.ps1 -Uninstall
```

This will:

- Remove the DuckBrain entry from Claude Desktop config
- Uninstall the `duckbrain` binary
- On Windows: remove the WSL launch script and batch file
- **Not** remove your Obsidian vault or its contents

> Your original Claude Desktop config is backed up (with `.duckbrain-backup`
> suffix) before any changes. You can restore it manually if needed.

---

## Next Steps

Once DuckBrain is working, check out the full documentation:

- **[Troubleshooting Guide](troubleshooting.md)** — If something isn't working
- **[README](../README.md)** — Full feature documentation
- **GitHub Issues** — [Report bugs or request features](https://github.com/timhiebenthal/duckbrain/issues)

For **AI coding agents** like Cursor, OpenCode, or Claude Code, see the
agent-specific setup instructions in the [main README](../README.md).
