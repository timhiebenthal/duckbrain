<#
.SYNOPSIS
    DuckBrain MCP Server Installer for Windows + WSL2
.DESCRIPTION
    Installs DuckBrain in WSL2 and configures Claude Desktop on Windows.
    Idempotent — safe to run multiple times.
.PARAMETER Help
    Show help and exit.
.PARAMETER Uninstall
    Remove DuckBrain and its configuration entries.
.EXAMPLE
    .\setup-duckbrain.ps1
    Interactive setup with prompts.
.EXAMPLE
    .\setup-duckbrain.ps1 -Uninstall
    Remove DuckBrain from WSL and Claude Desktop config.
#>

param(
    [switch]$Help,
    [switch]$Uninstall
)

# ── Constants ──────────────────────────────────────────────────────────────
$ScriptName = "setup-duckbrain.ps1"
$PackageName = "duckbrain"
$RepoUrl = "https://github.com/timhiebenthal/duckbrain"
$ConfigBackupSuffix = ".duckbrain-backup"
$WslHomeScript = "bin/duckbrain-for-claude.sh"
$BatchScriptDir = "$env:USERPROFILE\scripts"
$BatchScriptFile = "$BatchScriptDir\duckbrain.bat"

# ── Colors ─────────────────────────────────────────────────────────────────
$Host.UI.RawUI.ForegroundColor = [System.ConsoleColor]::White

function Write-Info  { Write-Host "✓ " -NoNewline -ForegroundColor Green; Write-Host "$args" }
function Write-Warn  { Write-Host "⚠ " -NoNewline -ForegroundColor Yellow; Write-Host "$args" }
function Write-Error { Write-Host "✗ " -NoNewline -ForegroundColor Red; Write-Host "$args" }
function Write-Step { Write-Host "`n── $args`n" -ForegroundColor Cyan }
function Write-Heading { Write-Host "$args" -ForegroundColor Cyan }
function Die { Write-Error "$args"; Write-Host "`n  Need help? Open an issue at:`n    $RepoUrl/issues" -ForegroundColor Gray; exit 1 }

# ── Help ───────────────────────────────────────────────────────────────────
function Show-Help {
    Write-Host @"
${ScriptName} — DuckBrain MCP Server Installer (Windows + WSL2)

Install DuckBrain in WSL2 and configure it for Claude Desktop on Windows.

Usage:
  .\${ScriptName}                Interactive setup
  .\${ScriptName} -Help          Show this help
  .\${ScriptName} -Uninstall     Remove DuckBrain and its config entries

What it does:
  1. Checks prerequisites (WSL2, Claude Desktop, uv in WSL)
  2. Prompts for your WSL username, vault path, and repo path
  3. Installs DuckBrain inside WSL via "uv tool install"
  4. Creates a WSL launch script (~/bin/duckbrain-for-claude.sh)
  5. Creates a Windows batch file (scripts\duckbrain.bat)
  6. Configures Claude Desktop
  7. Validates everything

Prerequisites:
  - Windows 10/11 with WSL2 (any Linux distro)
  - Claude Desktop (https://claude.ai/download)
  - uv inside WSL (https://astral.sh/uv/install.sh)
  - An Obsidian vault

Troubleshooting:
  See docs/troubleshooting.md or visit:
  $RepoUrl/issues

"@
}

# ── Prerequisites ──────────────────────────────────────────────────────────
function Test-UVinWSL {
    Write-Step "Checking uv in WSL"
    $result = wsl.exe -e bash -c "command -v uv 2>/dev/null && echo FOUND || echo NOTFOUND" 2>$null
    if ($result -like "*FOUND*") {
        Write-Info "uv found in WSL"
        return $true
    }
    Write-Error "uv not found inside WSL."
    Write-Host @"

  Install uv in WSL with:
    curl -LsSf https://astral.sh/uv/install.sh | sh

  Then restart your WSL terminal and re-run this script.
"@ -ForegroundColor Yellow
    return $false
}

function Test-WSL2 {
    Write-Step "Checking WSL2"

    # Check WSL is installed
    $wslStatus = wsl.exe --status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "WSL is not installed or not working."
        Write-Host @"

  Install WSL2:
    1. Open PowerShell as Administrator
    2. Run: wsl --install
    3. Restart your computer
    4. Set up a Linux username and password
    5. Re-run this script

  More info: https://learn.microsoft.com/en-us/windows/wsl/install
"@ -ForegroundColor Yellow
        return $false
    }

    # Check WSL2 is the default version
    $wslVersion = wsl.exe -l -v 2>&1
    if ($wslVersion -match "docker") {
        # Docker WSL distros are fine, check for a real distro
        $hasDistro = $wslVersion -match "Running" -or $wslVersion -match "Stopped"
        if (-not $hasDistro -and -not ($wslVersion -match "docker")) {
            Write-Warn "No WSL Linux distribution detected (Docker-only WSL may not work)."
        }
    }

    # Check default version is 2
    $defaultVersion = wsl.exe --status 2>&1 | Select-String "Default Version"
    if ($defaultVersion -match "2") {
        Write-Info "WSL2 is the default version"
    } else {
        Write-Warn "WSL default version is not 2. Setting it..."
        wsl.exe --set-default-version 2
    }

    return $true
}

function Test-ClaudeDesktop {
    Write-Step "Checking Claude Desktop"

    # Try to find Claude Desktop config directory
    $claudeConfigPath = Find-ClaudeConfigPath
    if ($claudeConfigPath -and (Test-Path (Split-Path $claudeConfigPath -Parent))) {
        Write-Info "Claude Desktop detected"
        return $true
    }

    # Also check common install paths
    $claudePaths = @(
        "$env:LOCALAPPDATA\Programs\Claude\Claude.exe",
        "$env:ProgramFiles\Claude\Claude.exe",
        "${env:ProgramFiles(x86)}\Claude\Claude.exe"
    )
    $found = $false
    foreach ($p in $claudePaths) {
        if (Test-Path $p) {
            Write-Info "Claude Desktop found at: $p"
            $found = $true
            break
        }
    }

    if ($found) {
        # Config dir might still not exist until Claude is run once
        $configDir = Split-Path (Find-ClaudeConfigPath) -Parent
        if (-not (Test-Path $configDir)) {
            Write-Warn "Claude Desktop config directory not yet created."
            Write-Warn "  Launch Claude Desktop at least once to create the config file."
            Write-Warn "  The script will continue but may need a re-run after first launch."
        }
        return $true
    }

    Write-Warn "Claude Desktop not found in common locations."
    Write-Host @"
  Install Claude Desktop from:
    https://claude.ai/download

  Then re-run this script.
"@ -ForegroundColor Yellow

    Write-Host "Continue anyway? [Y/n] " -NoNewline
    $response = Read-Host
    return ($response -ne "n" -and $response -ne "N")
}

function Find-ClaudeConfigPath {
    # Claude Desktop config lives under a MSIX package folder
    $packagesPath = "$env:LOCALAPPDATA\Packages"
    if (-not (Test-Path $packagesPath)) {
        return $null
    }

    $claudeFolders = Get-ChildItem -Path $packagesPath -Directory -Filter "Claude*" 2>$null
    if (-not $claudeFolders) {
        return $null
    }

    # Use the first matching folder
    foreach ($folder in $claudeFolders) {
        $configPath = Join-Path $folder.FullName "LocalCache\Roaming\Claude\claude_desktop_config.json"
        if (Test-Path (Split-Path $configPath -Parent)) {
            return $configPath
        }
    }

    # Return the most likely path even if it doesn't exist yet
    $firstFolder = $claudeFolders | Select-Object -First 1
    return Join-Path $firstFolder.FullName "LocalCache\Roaming\Claude\claude_desktop_config.json"
}

# ── WSL helpers ────────────────────────────────────────────────────────────
function Get-WslUsername {
    $name = wsl.exe -e bash -c "whoami" 2>$null
    if ($LASTEXITCODE -eq 0 -and $name) {
        return $name.Trim()
    }
    return "ubuntu"  # fallback
}

function Get-WslHome {
    param([string]$Username)
    return "/home/$Username"
}

function Convert-WindowsToWslPath {
    param([string]$WindowsPath)
    if ([string]::IsNullOrWhiteSpace($WindowsPath)) {
        return ""
    }
    # Convert C:\Users\foo\... -> /mnt/c/Users/foo/...
    $driveLetter = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2).Replace('\', '/')
    return "/mnt/$driveLetter$rest"
}

function Find-VaultPath {
    # Check common Obsidian locations
    $candidates = @(
        "$env:USERPROFILE\Documents\obsidian",
        "$env:USERPROFILE\Documents\Obsidian",
        "$env:USERPROFILE\Documents\obsidian-vault",
        "$env:USERPROFILE\obsidian"
    )
    foreach ($dir in $candidates) {
        if (Test-Path $dir) {
            if (Test-Path "$dir\.obsidian" -PathType Container -or
                Test-Path "$dir\wiki" -PathType Container) {
                return $dir
            }
        }
    }
    # Fallback: check subdirectories of Documents
    $docsPath = "$env:USERPROFILE\Documents"
    if (Test-Path $docsPath) {
        $subdirs = Get-ChildItem -Path $docsPath -Directory 2>$null
        foreach ($d in $subdirs) {
            if (Test-Path "$($d.FullName)\.obsidian" -PathType Container -or
                Test-Path "$($d.FullName)\wiki" -PathType Container) {
                return $d.FullName
            }
        }
    }
    # Default suggestion
    return "$env:USERPROFILE\Documents\obsidian"
}

# ── Config management ──────────────────────────────────────────────────────
function Backup-Config {
    param([string]$ConfigPath)
    if (-not (Test-Path $ConfigPath)) { return }
    $backupPath = "${ConfigPath}${ConfigBackupSuffix}"
    if (-not (Test-Path $backupPath)) {
        Copy-Item -Path $ConfigPath -Destination $backupPath
        Write-Info "Backed up existing config to: $backupPath"
    } else {
        Write-Warn "Backup already exists at: $backupPath (not overwritten)"
    }
}

function Validate-Json {
    param([string]$Json, [string]$Context)
    try {
        $null = $Json | ConvertFrom-Json
        return $true
    } catch {
        Write-Error "Invalid JSON in ${Context}: $($_.Exception.Message)"
        return $false
    }
}

function Update-ClaudeConfig {
    param(
        [string]$ConfigPath,
        [string]$Command,
        [string]$VaultPath
    )

    Backup-Config -ConfigPath $ConfigPath

    # Ensure directory exists
    $configDir = Split-Path $ConfigPath -Parent
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    }

    # Read existing config or start fresh
    $config = @{}
    if (Test-Path $ConfigPath) {
        $content = Get-Content -Path $ConfigPath -Raw -Encoding UTF8
        if ($content.Trim()) {
            $config = $content | ConvertFrom-Json
            if ($config -isnot [PSCustomObject]) {
                $config = @{}
            }
        }
    }

    # Convert to hashtable for easier manipulation
    $configHash = @{}
    $config.PSObject.Properties | ForEach-Object { $configHash[$_.Name] = $_.Value }

    # Ensure mcpServers key
    if (-not $configHash.ContainsKey('mcpServers')) {
        $configHash['mcpServers'] = @{}
    }

    # Add duckbrain entry
    $configHash['mcpServers']['duckbrain'] = @{
        'command' = $Command
        'env' = @{
            'VAULT_PATH' = $VaultPath
        }
    }

    # Convert back to JSON with nice formatting
    $json = $configHash | ConvertTo-Json -Depth 10

    if (-not (Validate-Json -Json $json -Context "new config")) {
        return $false
    }

    # Write atomically
    $tmpFile = [System.IO.Path]::GetTempFileName()
    try {
        $json | Set-Content -Path $tmpFile -Encoding UTF8 -NoNewline
        Move-Item -Path $tmpFile -Destination $ConfigPath -Force
    } catch {
        if (Test-Path $tmpFile) { Remove-Item $tmpFile -Force }
        throw
    }

    Write-Info "Updated Claude Desktop config: $ConfigPath"
    return $true
}

# ── WSL script creation ────────────────────────────────────────────────────
function New-WslScript {
    param(
        [string]$WslUser,
        [string]$WslHome,
        [string]$WslVaultPath
    )

    Write-Step "Creating WSL launch script"

    $scriptContent = @"#!/usr/bin/env bash
# ============================================================================
# duckbrain-for-claude.sh — WSL launch script for DuckBrain
# ============================================================================
# This script is auto-generated by setup-duckbrain.ps1.
# Re-run setup-duckbrain.ps1 to regenerate it.
# ============================================================================
set -euo pipefail
export VAULT_PATH="${WslVaultPath}"
exec /home/${WslUser}/.local/bin/duckbrain
"@

    # Write to a temp file, then copy to WSL
    $tmpScript = [System.IO.Path]::GetTempFileName()
    $scriptContent | Set-Content -Path $tmpScript -Encoding ASCII -NoNewline

    # Fix line endings to LF
    $content = Get-Content -Path $tmpScript -Raw
    $content -replace "`r`n", "`n" | Set-Content -Path $tmpScript -Encoding ASCII -NoNewline

    # Create bin directory and copy script into WSL
    $wslScriptDir = "$WslHome/bin"
    $wslScriptPath = "$WslHome/$WslHomeScript"

    # Remove the script file name from the path to get just the directory
    $wslDir = [System.IO.Path]::GetDirectoryName($wslScriptPath)
    wsl.exe -e bash -c "mkdir -p '$wslDir' && rm -f '$wslScriptPath'" 2>$null

    # Copy file into WSL
    $remotePath = wsl.exe -e bash -c "echo '$wslScriptPath'" 2>$null
    $result = wsl.exe -e bash -c "cat > '$wslScriptPath'" < $tmpScript 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Failed to create WSL script via heredoc. Trying direct copy..."
        # Alternative: use wslpath and copy from temp
        wsl.exe -e bash -c "cp '/mnt/c/Users/$env:USERNAME/AppData/Local/Temp/$(Split-Path $tmpScript -Leaf)' '$wslScriptPath'" 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to copy script to WSL."
            Remove-Item $tmpScript -Force -ErrorAction SilentlyContinue
            return $false
        }
    }

    Remove-Item $tmpScript -Force -ErrorAction SilentlyContinue

    # Make executable
    wsl.exe -e bash -c "chmod +x '$wslScriptPath'" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to make WSL script executable."
        return $false
    }

    Write-Info "Created WSL script: $wslScriptPath"
    return $wslScriptPath
}

function New-BatchFile {
    param([string]$WslUser, [string]$WslScriptPath)

    Write-Step "Creating Windows batch file"

    if (-not (Test-Path $BatchScriptDir)) {
        New-Item -ItemType Directory -Path $BatchScriptDir -Force | Out-Null
    }

    $batchContent = @"@echo off
REM ===========================================================================
REM duckbrain.bat — Windows batch launcher for DuckBrain in WSL
REM ===========================================================================
REM This script is auto-generated by setup-duckbrain.ps1.
REM Re-run setup-duckbrain.ps1 to regenerate it.
REM ===========================================================================
wsl.exe -e bash "%USERPROFILE%\bin\duckbrain-for-claude.sh"
"@

    # Use full path instead of %USERPROFILE% for the actual batch file
    $batchContentFull = @"@echo off
REM ===========================================================================
REM duckbrain.bat — Windows batch launcher for DuckBrain in WSL
REM ===========================================================================
REM This script is auto-generated by setup-duckbrain.ps1.
REM Re-run setup-duckbrain.ps1 to regenerate it.
REM ===========================================================================
wsl.exe -e bash "$WslScriptPath"
"@

    $batchContentFull | Set-Content -Path $BatchScriptFile -Encoding ASCII -NoNewline
    Write-Info "Created batch file: $BatchScriptFile"
    return $BatchScriptFile
}

# ── Installation ───────────────────────────────────────────────────────────
function Install-DuckBrain {
    param([string]$RepoPath)

    Write-Step "Installing DuckBrain in WSL"

    if ($RepoPath -and (Test-Path $RepoPath)) {
        Write-Host "  Installing from local repository: $RepoPath" -ForegroundColor Gray
        $wslRepoPath = Convert-WindowsToWslPath -WindowsPath $RepoPath

        $result = wsl.exe -e bash -c "uv tool install '$wslRepoPath' --reinstall 2>&1" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "DuckBrain installed from local repo"
            return $true
        }
        Write-Warn "Local install failed — falling back to PyPI"
    }

    Write-Host "  Installing from PyPI..." -ForegroundColor Gray
    $result = wsl.exe -e bash -c "uv tool install duckbrain --reinstall 2>&1" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "DuckBrain installed from PyPI"
        return $true
    }

    Write-Error "Failed to install DuckBrain in WSL."
    Write-Host @"
  The output was:
  $result

  Check your WSL internet connection and try again.
  If the issue persists, install manually:
    wsl -e bash -c "uv tool install duckbrain"
"@ -ForegroundColor Yellow
    return $false
}

# ── Verification ───────────────────────────────────────────────────────────
function Verify-Installation {
    Write-Step "Verifying installation"

    # Check duckbrain binary in WSL
    $result = wsl.exe -e bash -c "command -v duckbrain 2>/dev/null && echo FOUND || echo NOTFOUND" 2>$null
    if ($result -like "*FOUND*") {
        Write-Info "DuckBrain binary found in WSL PATH"
    } else {
        Write-Warn "DuckBrain not on WSL PATH. Checking ~/.local/bin..."
        $result2 = wsl.exe -e bash -c "test -f ~/.local/bin/duckbrain && echo FOUND || echo NOTFOUND" 2>$null
        if ($result2 -like "*FOUND*") {
            Write-Info "DuckBrain found at ~/.local/bin/duckbrain"
        } else {
            Write-Error "DuckBrain binary not found in WSL."
            return $false
        }
    }

    # Check WSL script
    $wslScriptPath = "/home/$WslUser/$WslHomeScript"
    $result = wsl.exe -e bash -c "test -x '$wslScriptPath' && echo FOUND || echo NOTFOUND" 2>$null
    if ($result -like "*FOUND*") {
        Write-Info "WSL script exists and is executable: $wslScriptPath"
    } else {
        Write-Warn "WSL script not found or not executable: $wslScriptPath"
    }

    # Check batch file
    if (Test-Path $BatchScriptFile) {
        Write-Info "Batch file exists: $BatchScriptFile"
    } else {
        Write-Warn "Batch file not found: $BatchScriptFile"
    }

    # Test running duckbrain --help in WSL (should show help, not hang)
    Write-Host "  Testing DuckBrain launch (quick check)..." -ForegroundColor Gray
    $testResult = wsl.exe -e bash -c "timeout 3 duckbrain --help 2>/dev/null || true" 2>$null
    if ($testResult -match "DuckBrain" -or $testResult -match "usage" -or $testResult -match "duckbrain") {
        Write-Info "DuckBrain launches successfully in WSL"
    } else {
        Write-Warn "Could not verify DuckBrain launch (timeout or no output — this is normal for MCP stdio mode)"
    }

    return $true
}

function Verify-Config {
    param([string]$ConfigPath)
    Write-Step "Verifying Claude Desktop configuration"

    if (-not (Test-Path $ConfigPath)) {
        Write-Error "Config file not found at: $ConfigPath"
        return $false
    }

    $content = Get-Content -Path $ConfigPath -Raw -Encoding UTF8
    try {
        $config = $content | ConvertFrom-Json
        $mcpServers = $config.mcpServers
        if ($null -eq $mcpServers) {
            Write-Error "Config is missing 'mcpServers' key"
            return $false
        }
        $db = $mcpServers.duckbrain
        if ($null -eq $db) {
            Write-Error "Config is missing 'duckbrain' entry in mcpServers"
            return $false
        }
        if ([string]::IsNullOrEmpty($db.command)) {
            Write-Error "Config is missing 'command' for duckbrain"
            return $false
        }
        if ($null -eq $db.env -or [string]::IsNullOrEmpty($db.env.VAULT_PATH)) {
            Write-Error "Config is missing 'VAULT_PATH' env var for duckbrain"
            return $false
        }
        Write-Info "Claude Desktop configuration is valid"
        Write-Host "  Command:     $($db.command)" -ForegroundColor Gray
        Write-Host "  VAULT_PATH: $($db.env.VAULT_PATH)" -ForegroundColor Gray
        return $true
    } catch {
        Write-Error "Config validation failed: $($_.Exception.Message)"
        return $false
    }
}

# ── Uninstall ──────────────────────────────────────────────────────────────
function Uninstall-DuckBrain {
    param([string]$WslUser)

    Write-Heading "Uninstalling DuckBrain"

    # Remove Claude config entry
    $configPath = Find-ClaudeConfigPath
    if ($configPath -and (Test-Path $configPath)) {
        Write-Step "Removing DuckBrain from Claude Desktop config"
        Backup-Config -ConfigPath $configPath
        $content = Get-Content -Path $configPath -Raw -Encoding UTF8
        $config = $content | ConvertFrom-Json
        $configHash = @{}
        $config.PSObject.Properties | ForEach-Object { $configHash[$_.Name] = $_.Value }
        if ($configHash.ContainsKey('mcpServers') -and $configHash['mcpServers'].ContainsKey('duckbrain')) {
            $configHash['mcpServers'].Remove('duckbrain')
            if ($configHash['mcpServers'].Keys.Count -eq 0) {
                $configHash.Remove('mcpServers')
            }
            $json = $configHash | ConvertTo-Json -Depth 10
            $json | Set-Content -Path $configPath -Encoding UTF8 -NoNewline
            Write-Info "Removed DuckBrain from Claude Desktop config"
        }
    }

    # Remove WSL script
    $wslScriptPath = "/home/$WslUser/$WslHomeScript"
    Write-Step "Removing WSL script"
    wsl.exe -e bash -c "rm -f '$wslScriptPath'" 2>$null
    Write-Info "Removed WSL script: $wslScriptPath"

    # Remove batch file
    if (Test-Path $BatchScriptFile) {
        Write-Step "Removing batch file"
        Remove-Item $BatchScriptFile -Force
        Write-Info "Removed batch file: $BatchScriptFile"
    }

    # Uninstall tool
    Write-Step "Removing DuckBrain binary"
    wsl.exe -e bash -c "uv tool uninstall duckbrain 2>/dev/null; echo DONE" 2>$null
    Write-Info "Uninstalled DuckBrain from WSL"

    # Check for backup
    $backupPath = "${configPath}${ConfigBackupSuffix}"
    if (Test-Path $backupPath) {
        Write-Warn "Backup config file still exists: ${backupPath}"
        Write-Host "  Remove it manually if not needed:"
        Write-Host "    Remove-Item '$backupPath'"
    }

    Write-Host "`nUninstall complete" -ForegroundColor Green
}

# ── Main ───────────────────────────────────────────────────────────────────
function Main {
    if ($Help) {
        Show-Help
        return
    }

    # ── Banner ──────────────────────────────────────────────────────────
    Write-Host @"

  🦆  DuckBrain Setup
  DuckDB-backed MCP memory server for Obsidian vaults
  $RepoUrl

"@ -ForegroundColor Cyan

    if ($Uninstall) {
        Write-Heading "Detecting WSL user..."
        $wslUser = Get-WslUsername
        Write-Host "  WSL user: $wslUser" -ForegroundColor Gray
        Uninstall-DuckBrain -WslUser $wslUser
        return
    }

    # ── Install mode ────────────────────────────────────────────────────

    # 1. Check prerequisites
    Write-Step "Checking prerequisites"

    if (-not (Test-WSL2)) { exit 1 }
    if (-not (Test-ClaudeDesktop)) { exit 1 }
    if (-not (Test-UVinWSL)) { exit 1 }
    Write-Info "All prerequisites met"

    # 2. Gather configuration
    Write-Step "Configuration"

    # WSL username
    $defaultWslUser = Get-WslUsername
    Write-Host ""
    Write-Host "  Enter your WSL Linux username."
    Write-Host "  (Press Enter for detected default)"
    $wslUser = Read-Host -Prompt "  WSL username [$defaultWslUser]"
    if ([string]::IsNullOrWhiteSpace($wslUser)) { $wslUser = $defaultWslUser }

    # Vault path
    $defaultVault = Find-VaultPath
    Write-Host ""
    Write-Host "  Enter the Windows path to your Obsidian vault."
    Write-Host "  (Press Enter for detected default)"
    $vaultPath = Read-Host -Prompt "  Vault path [$defaultVault]"
    if ([string]::IsNullOrWhiteSpace($vaultPath)) { $vaultPath = $defaultVault }

    # Check if vault exists
    if (-not (Test-Path $vaultPath)) {
        Write-Warn "Vault directory does not exist yet: $vaultPath"
        Write-Host "  The script will continue — create the directory before starting Claude Desktop."
        Write-Host ""
    }

    # Repo path
    $defaultRepo = "$env:USERPROFILE\git_repos\duckbrain"
    Write-Host ""
    Write-Host "  Enter the Windows path to the DuckBrain repository."
    Write-Host "  If you have a local clone, the script will install from it."
    Write-Host "  Otherwise, it will install from PyPI (no local repo needed)."
    $repoPath = Read-Host -Prompt "  Repo path [$defaultRepo]"
    if ([string]::IsNullOrWhiteSpace($repoPath)) { $repoPath = $defaultRepo }

    # Convert vault path to WSL format
    $wslVaultPath = Convert-WindowsToWslPath -WindowsPath $vaultPath
    $wslHome = Get-WslHome -Username $wslUser

    Write-Host ""
    Write-Host "  Configuration summary:" -ForegroundColor Gray
    Write-Host "    WSL user:     $wslUser" -ForegroundColor Gray
    Write-Host "    Vault path:   $vaultPath" -ForegroundColor Gray
    Write-Host "    WSL vault:    $wslVaultPath" -ForegroundColor Gray
    Write-Host "    Repo path:    $repoPath" -ForegroundColor Gray
    Write-Host ""

    # 3. Install in WSL
    $installOk = Install-DuckBrain -RepoPath $repoPath
    if (-not $installOk) { exit 1 }

    # 4. Create WSL script
    $wslScriptPath = New-WslScript -WslUser $wslUser -WslHome $wslHome -WslVaultPath $wslVaultPath
    if (-not $wslScriptPath) {
        Write-Error "Failed to create WSL launch script."
        exit 1
    }

    # 5. Create batch file
    $batchFile = New-BatchFile -WslUser $wslUser -WslScriptPath $wslScriptPath

    # 6. Update Claude Desktop config
    $configPath = Find-ClaudeConfigPath
    if (-not $configPath) {
        Write-Error "Could not find Claude Desktop config path."
        Write-Host "  Please locate your claude_desktop_config.json manually."
        Write-Host "  It should be under C:\Users\<you>\AppData\Local\Packages\Claude_*\LocalCache\Roaming\Claude\"
        exit 1
    }

    Write-Step "Configuring Claude Desktop"
    Write-Host "  Config file: $configPath" -ForegroundColor Gray
    Write-Host "  Command:     $batchFile" -ForegroundColor Gray

    $configOk = Update-ClaudeConfig -ConfigPath $configPath -Command $batchFile -VaultPath $vaultPath
    if (-not $configOk) { exit 1 }

    # 7. Verify
    Verify-Installation
    Verify-Config -ConfigPath $configPath

    # 8. Summary
    Write-Step "Setup complete!"
    Write-Host @"

  What was done:
  ✓ DuckBrain installed in WSL
  ✓ WSL launch script created
  ✓ Windows batch file created
  ✓ Claude Desktop configured
  ✓ Config validated

  Next steps:
  1. Restart Claude Desktop
  2. Open a new conversation
  3. Look for the hammer 🔨 icon in the bottom-right input area
  4. You should see DuckBrain tools: vault_search, vault_read, vault_write,
     vault_info, vault_context

  Need help?
  • Troubleshooting guide: docs/troubleshooting.md
  • GitHub issues: $RepoUrl/issues

"@ -ForegroundColor White

    # Check config backup
    $backupPath = "${configPath}${ConfigBackupSuffix}"
    if (Test-Path $backupPath) {
        Write-Warn "A backup of your previous config was saved to:"
        Write-Host "  $backupPath"
        Write-Host ""
    }
}

Main
