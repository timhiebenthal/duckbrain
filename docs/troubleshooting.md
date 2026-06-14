# DuckBrain Troubleshooting Guide

Having trouble with DuckBrain? This guide covers common issues by platform.

---

## Windows + WSL Issues

### "WSL is not installed"

**Symptom:** The setup script reports that WSL is not found.

**Fix:**
1. Open PowerShell **as Administrator**
2. Run: `wsl --install`
3. Restart your computer
4. Set up a Linux username and password when prompted
5. Re-run the DuckBrain setup script

> **Need more help?** See Microsoft's [official WSL install guide](https://learn.microsoft.com/en-us/windows/wsl/install).

---

### "uv not found in WSL"

**Symptom:** The setup script or manual test shows that `uv` is not available
inside WSL.

**Fix:**
1. Open your WSL terminal (type `wsl` in PowerShell or CMD)
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Restart your WSL terminal or run: `source ~/.bashrc`
4. Verify: `uv --version` should show a version number
5. Re-run the DuckBrain setup script

> **Why inside WSL?** DuckBrain runs inside WSL, so `uv` needs to be installed
> there (not on Windows).

---

### "duckbrain: command not found"

**Symptom:** The WSL script or terminal can't find the `duckbrain` command.

**Fixes:**

**Check the installation:**
```bash
wsl -e bash -c "uv tool install duckbrain --reinstall"
```

**Check PATH:**
```bash
wsl -e bash -c 'echo $PATH'
```
If `~/.local/bin` is not in the PATH, add it to your `~/.bashrc`:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

**Verify the binary exists:**
```bash
wsl -e bash -c "ls -la ~/.local/bin/duckbrain"
```

---

### "Permission denied"

**Symptom:** The WSL script `~/bin/duckbrain-for-claude.sh` fails with
"Permission denied."

**Fix:**
```bash
wsl -e bash -c "chmod +x ~/bin/duckbrain-for-claude.sh"
```

If the file doesn't exist, re-run the setup script:
```powershell
.\setup-duckbrain.ps1
```

---

### "Claude Desktop doesn't see DuckBrain tools"

**Symptom:** After restarting Claude Desktop, the tools list doesn't include
vault_search, vault_read, etc.

**Check these in order:**

**1. Config file location**

Verify the config was created in the right place:
```powershell
# Find the config file
Get-ChildItem -Path "$env:LOCALAPPDATA\Packages" -Recurse -Filter "claude_desktop_config.json" -ErrorAction SilentlyContinue
```

The correct path should look like:
```
C:\Users\<you>\AppData\Local\Packages\Claude_<random>\LocalCache\Roaming\Claude\claude_desktop_config.json
```

**2. Config file content**

Open the config file and check that the duckbrain entry exists:
```json
{
  "mcpServers": {
    "duckbrain": {
      "command": "C:\\Users\\<you>\\scripts\\duckbrain.bat",
      "env": {
        "VAULT_PATH": "C:\\Users\\<you>\\Documents\\obsidian\\your-vault"
      }
    }
  }
}
```

**3. Test the batch file directly**

Open Command Prompt and run:
```cmd
C:\Users\<you>\scripts\duckbrain.bat
```

It should hang (waiting for MCP input) — that's normal. Press Ctrl+C to stop.
If it shows an error, check the WSL issue sections above.

**4. Restart properly**

Close Claude Desktop completely (right-click the system tray icon → Quit),
then launch it again. A simple window close may not fully restart the MCP
server.

---

### "Connection refused" or "Could not connect"

**Symptom:** Claude Desktop shows a "connection refused" error for DuckBrain.

**Likely causes:**

- **DuckBrain is not running.** Check the WSL script:
  ```bash
  wsl -e bash -c "cat ~/bin/duckbrain-for-claude.sh"
  ```
  The script should set `VAULT_PATH` and run the `duckbrain` command.

- **The WSL distribution is stopped.** Run:
  ```powershell
  wsl --list --verbose
  ```
  If your distro shows as "Stopped," start it with: `wsl`

- **Vault path doesn't exist in WSL.** The vault path in the script uses
  `/mnt/c/...` format. Verify the path:
  ```bash
  wsl -e bash -c "ls '/mnt/c/Users/<you>/Documents/obsidian/your-vault/'"
  ```

---

### "VAULT_PATH not set"

**Symptom:** DuckBrain starts but complains that `VAULT_PATH` is not set.

**Fix:** Check the WSL launch script:
```bash
wsl -e bash -c "cat ~/bin/duckbrain-for-claude.sh"
```

It should contain a line like:
```bash
export VAULT_PATH="/mnt/c/Users/<you>/Documents/obsidian/your-vault"
```

If it's missing or wrong, re-run the setup script.

---

### How to view Claude Desktop logs (Windows)

Claude Desktop writes logs to:
```
C:\Users\<you>\AppData\Local\Packages\Claude_<random>\LocalCache\Roaming\Claude\logs\
```

To view the latest DuckBrain-related log:
```powershell
Get-ChildItem "$env:LOCALAPPDATA\Packages\Claude_*\LocalCache\Roaming\Claude\logs\" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```

---

### How to view WSL logs

Run DuckBrain from the terminal to see real-time output:
```bash
wsl -e bash -c "export VAULT_PATH='/mnt/c/path/to/vault' && ~/.local/bin/duckbrain"
```

Press `Ctrl+C` to stop. Any error messages will appear in the terminal.

---

## Mac / Linux Issues

### "duckbrain: command not found"

**Symptom:** The terminal says `duckbrain: command not found`.

**Check if it was installed:**
```bash
uv tool list
# Should show: duckbrain v0.X.X
```

**Check PATH:**
```bash
echo $PATH
```

If `~/.local/bin` is not in your PATH, add it:
- **macOS/Linux (bash):** Add to `~/.bashrc`:
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```
- **macOS (zsh):** Add to `~/.zshrc`:
  ```zsh
  export PATH="$HOME/.local/bin:$PATH"
  ```

Then restart your terminal or run `source ~/.bashrc` (or `source ~/.zshrc`).

**Reinstall:**
```bash
uv tool install duckbrain --reinstall
```

---

### "Config file not found"

**Symptom:** The setup script reports that the Claude Desktop config file
couldn't be found.

**Check if Claude Desktop is installed:**

- **macOS:** Check `/Applications/Claude.app` or `~/Applications/Claude.app`
- **Linux:** Check `~/.config/Claude/`

**First launch:** The config file is created when you first launch Claude
Desktop. Open the app, sign in, then close it — the config file should now exist.

**Manual path check:**
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

---

### "Permission denied"

**Symptom:** DuckBrain or a script fails with "Permission denied."

**Fixes:**

- **DuckBrain binary:** Reinstall with: `uv tool install duckbrain --reinstall`
- **Script files:** Make executable with: `chmod +x <filename>`
- **Config file:** The setup script sets correct permissions. If you edited it
  manually: `chmod 644 ~/Library/Application\ Support/Claude/claude_desktop_config.json`

---

### How to view Claude Desktop logs (Mac)

```bash
# Show the most recent log entries
ls -lt ~/Library/Logs/Claude/ | head -5
cat ~/Library/Logs/Claude/mcp-server-duckbrain.log 2>/dev/null || echo "No logs yet"
```

> If the log doesn't exist, it means Claude Desktop hasn't started DuckBrain yet.
> Open a new conversation and check again.

---

## General Issues

### How to enable debug logging

Set the `VAULT_PATH` environment variable and run DuckBrain directly:

**macOS / Linux:**
```bash
VAULT_PATH=/path/to/vault duckbrain 2>&1
```

**Windows (in WSL):**
```bash
wsl -e bash -c "export VAULT_PATH='/mnt/c/path/to/vault' && ~/.local/bin/duckbrain 2>&1"
```

This runs DuckBrain in the foreground and shows all output, including errors
that Claude Desktop might hide.

---

### How to check if DuckBrain is running

**macOS / Linux:**
```bash
ps aux | grep duckbrain
```

**Windows:**
```powershell
wsl ps aux | grep duckbrain
```

Or check the batch file directly:
```cmd
tasklist | findstr wsl
```

---

### How to report a bug

When reporting a bug, please include:

1. **Your platform:** Windows + WSL2, macOS, or Linux
2. **Your OS version:** e.g., Windows 11, macOS 14.5, Ubuntu 24.04
3. **DuckBrain version:** Run `uv tool list` or check the installed version
4. **Claude Desktop version:** Found in Claude → Settings → About
5. **What you were doing:** Steps to reproduce
6. **What happened:** Error message, screenshot, or log output
7. **What you expected to happen**

Report bugs at: [https://github.com/timhiebenthal/duckbrain/issues](https://github.com/timhiebenthal/duckbrain/issues)

---

### FAQ

**Q: Does DuckBrain modify my Obsidian vault files?**

A: Yes — DuckBrain writes to your vault when you use `vault_write`. It creates
new pages with YAML frontmatter and updates the index. It treats your vault as
the source of truth. All writes are standard markdown files.

**Q: Will this break my existing Claude Desktop config?**

A: No. The script creates a backup before modifying the config (appends
`.duckbrain-backup` to the filename). If something goes wrong, restore from
that backup.

**Q: Do I need admin/sudo rights?**

A: No. DuckBrain installs entirely in your user space — no system-wide
packages, no registry changes, no admin password needed.

**Q: Can I use DuckBrain with other AI tools besides Claude Desktop?**

A: Yes! DuckBrain is a standard MCP server. It works with any MCP-compatible
client including:
- **OpenCode** — Recommended (has dedicated plugins for vault awareness)
- **Claude Code** — Works via MCP server config
- **Cursor** — Works via `.cursor/mcp.json`
- **Hermes Agent** — Works via `mcp.json`
- **Any MCP client** — Just point it at `command: "duckbrain"` with `VAULT_PATH`

See the [main README](../README.md) for agent-specific setup.

**Q: How do I point DuckBrain at a different vault?**

A: Re-run the setup script — it will ask for the vault path again. Or manually
update the `VAULT_PATH` in your Claude Desktop config file.

**Q: Can I have multiple vaults?**

A: DuckBrain supports one vault at a time per server instance. For multiple
vaults, you can configure multiple MCP server entries with different names.

**Q: The setup script says "continue anyway" — is that safe?**

A: Yes. The "continue anyway" prompts appear when the script can't detect a
prerequisite but your setup might still work. For example, if Claude Desktop is
installed in a non-standard location, the script can still update the config
once you locate it.

---

## Getting Help

If this guide didn't solve your problem:

1. **Search existing issues** — Your problem may already be reported:
   [GitHub Issues](https://github.com/timhiebenthal/duckbrain/issues)

2. **Open a new issue** — Include the information from the "How to report a bug"
   section above.

3. **Check for updates** — A newer version may have fixed your issue:
   ```bash
   uv tool install duckbrain --reinstall
   ```
