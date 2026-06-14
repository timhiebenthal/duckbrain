#!/usr/bin/env bash
# ============================================================================
# setup-duckbrain.sh — DuckBrain MCP Server Installer (macOS / Linux)
# ============================================================================
# Usage:
#   ./setup-duckbrain.sh              # Interactive setup
#   ./setup-duckbrain.sh --help       # Show help
#   ./setup-duckbrain.sh --uninstall  # Remove DuckBrain + config entries
#
# This script installs DuckBrain and configures it for Claude Desktop.
# It is idempotent — safe to run multiple times.
# ============================================================================

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly DUCKBRAIN_PACKAGE="duckbrain"
readonly REPO_URL="https://github.com/timhiebenthal/duckbrain"
readonly CONFIG_BACKUP_SUFFIX=".duckbrain-backup"

# ── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    readonly BOLD='\033[1m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly RED='\033[0;31m'
    readonly CYAN='\033[0;36m'
    readonly NC='\033[0m' # No Color
else
    readonly BOLD=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly RED=''
    readonly CYAN=''
    readonly NC=''
fi

# ── Helpers ──────────────────────────────────────────────────────────────────

info()    { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()    { printf "${YELLOW}⚠${NC}  %s\n" "$*"; }
error()   { printf "${RED}✗${NC} %s\n" "$*" >&2; }
step()    { printf "\n${BOLD}── %s${NC}\n" "$*"; }
heading() { printf "\n${CYAN}%s${NC}\n" "$*"; }

die() {
    error "$*"
    echo ""
    echo "  Need help? Open an issue at:"
    echo "    ${REPO_URL}/issues"
    exit 1
}

# ── Detect platform ──────────────────────────────────────────────────────────

detect_os() {
    case "$(uname -s)" in
        Darwin*)  echo "macos" ;;
        Linux*)   echo "linux" ;;
        *)        echo "unknown" ;;
    esac
}

detect_config_path() {
    local os="$1"
    case "$os" in
        macos) echo "${HOME}/Library/Application Support/Claude/claude_desktop_config.json" ;;
        linux) echo "${HOME}/.config/Claude/claude_desktop_config.json" ;;
        *)     echo "" ;;
    esac
}

# ── Prerequisite checks ──────────────────────────────────────────────────────

check_uv() {
    if ! command -v uv &>/dev/null; then
        heading "UV not found"
        echo "DuckBrain is installed via 'uv', which is not on your PATH."
        echo ""
        echo "  Install with one command:"
        echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "  Then restart your terminal and re-run this script."
        return 1
    fi
    info "uv found at $(command -v uv)"
    return 0
}

check_claude_desktop() {
    local os="$1"
    local config_path
    config_path="$(detect_config_path "$os")"

    if [[ "$os" == "macos" ]]; then
        if [[ -d "/Applications/Claude.app" ]] || [[ -d "${HOME}/Applications/Claude.app" ]]; then
            info "Claude Desktop found in Applications"
            return 0
        fi
        # Fallback: check if config dir exists
        if [[ -d "$(dirname "$config_path")" ]]; then
            info "Claude Desktop config directory found"
            return 0
        fi
        warn "Claude Desktop not detected in /Applications"
        echo "  DuckBrain configures Claude Desktop to make its tools available."
        echo "  If Claude Desktop is installed elsewhere, the script will still work"
        echo "  but you may need to adjust paths. Continue anyway? [Y/n]"
        read -r -n1 response
        echo ""
        if [[ "$response" =~ ^[Nn]$ ]]; then
            return 1
        fi
        return 0
    else
        # Linux
        if [[ -d "$(dirname "$config_path")" ]]; then
            info "Claude Desktop config directory found"
            return 0
        fi
        # Check common snap/flatpak paths
        if [[ -d "${HOME}/snap/claude" ]] || [[ -d "${HOME}/.local/share/flatpak/app/Claude" ]]; then
            warn "Claude Desktop found via snap/flatpak — config path may differ."
            echo "  The script will use: ${config_path}"
            echo "  You may need to locate the actual config file manually."
            return 0
        fi
        warn "Claude Desktop config directory not found at: ${config_path}"
        echo "  DuckBrain configures Claude Desktop to make its tools available."
        echo "  If Claude Desktop is not installed, install it from:"
        echo "    https://claude.ai/download"
        echo ""
        echo "Continue anyway? [Y/n]"
        read -r -n1 response
        echo ""
        if [[ "$response" =~ ^[Nn]$ ]]; then
            return 1
        fi
        return 0
    fi
}

# ── Vault path detection ─────────────────────────────────────────────────────

find_vault_path() {
    # Try common Obsidian vault locations
    local candidates=(
        "${HOME}/Documents/obsidian"
        "${HOME}/Documents/Obsidian"
        "${HOME}/Documents/obsidian-vault"
        "${HOME}/obsidian"
        "${HOME}/vault"
    )
    for dir in "${candidates[@]}"; do
        if [[ -d "$dir" ]]; then
            # Check if it looks like an Obsidian vault (has .obsidian or wiki/daily)
            if [[ -d "${dir}/.obsidian" ]] || [[ -d "${dir}/wiki" ]]; then
                echo "$dir"
                return 0
            fi
        fi
    done

    # Fallback: just check ~/Documents/ for any vault-like directory
    if [[ -d "${HOME}/Documents" ]]; then
        for d in "${HOME}/Documents"/*/; do
            if [[ -d "${d}.obsidian" ]] || [[ -d "${d}wiki" ]]; then
                echo "${d%/}"
                return 0
            fi
        done
    fi

    # No vault found — return default suggestion
    echo "${HOME}/Documents/obsidian"
}

# ── Claude Desktop config management ─────────────────────────────────────────

read_config() {
    local config_path="$1"
    if [[ -f "$config_path" ]]; then
        cat "$config_path"
    else
        echo '{}'
    fi
}

backup_config() {
    local config_path="$1"
    if [[ -f "$config_path" ]]; then
        local backup_path="${config_path}${CONFIG_BACKUP_SUFFIX}"
        if [[ ! -f "$backup_path" ]]; then
            cp "$config_path" "$backup_path"
            info "Backed up existing config to: ${backup_path}"
        else
            warn "Backup already exists at: ${backup_path} (not overwritten)"
        fi
    fi
}

validate_json() {
    local json="$1"
    local context="$2"
    if ! echo "$json" | python3 -m json.tool > /dev/null 2>&1; then
        error "Invalid JSON in ${context}:"
        echo "$json" | python3 -m json.tool 2>&1 || echo "$json"
        return 1
    fi
    return 0
}

update_claude_config() {
    local config_path="$1"
    local vault_path="$2"
    local os="$3"

    backup_config "$config_path"

    # Ensure parent directory exists
    mkdir -p "$(dirname "$config_path")"

    local current_config
    current_config="$(read_config "$config_path")"
    validate_json "$current_config" "existing config at ${config_path}" || return 1

    # Write a temporary Python script to manipulate JSON (avoids escaping issues)
    local py_script
    py_script="$(mktemp)"
    cat > "$py_script" << 'PYEOF'
import json
import sys

config_path = sys.argv[1]
vault_path = sys.argv[2]

# Read existing config
with open(config_path) as f:
    try:
        config = json.load(f)
    except json.JSONDecodeError:
        config = {}

# Ensure mcpServers key exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add/update duckbrain entry
config['mcpServers']['duckbrain'] = {
    'command': 'duckbrain',
    'env': {
        'VAULT_PATH': vault_path
    }
}

# Write back atomically via temp file
tmp = config_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
import os
os.replace(tmp, config_path)
PYEOF

    python3 "$py_script" "$config_path" "$vault_path"
    local py_exit=$?
    rm -f "$py_script"

    if [[ $py_exit -ne 0 ]]; then
        error "Failed to update Claude Desktop config."
        return 1
    fi

    # Validate result
    local new_config
    new_config="$(cat "$config_path")"
    validate_json "$new_config" "updated config at ${config_path}" || return 1

    chmod 644 "$config_path" 2>/dev/null || true
    info "Updated Claude Desktop config: ${config_path}"
    return 0
}

# ── Installation ──────────────────────────────────────────────────────────────

install_duckbrain() {
    local repo_path="$1"

    if [[ -n "$repo_path" && -d "$repo_path" ]]; then
        step "Installing DuckBrain from local repository: ${repo_path}"
        if [[ -f "${repo_path}/pyproject.toml" ]]; then
            uv tool install "$repo_path" --reinstall 2>&1 | while IFS= read -r line; do
                echo "  ${line}"
            done
            if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
                info "DuckBrain installed from local repo"
                return 0
            fi
            warn "Local install failed — falling back to PyPI"
        else
            warn "No pyproject.toml found at ${repo_path}, not a valid Python project."
        fi
    fi

    step "Installing DuckBrain from PyPI"
    uv tool install "$DUCKBRAIN_PACKAGE" --reinstall 2>&1 | while IFS= read -r line; do
        echo "  ${line}"
    done

    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        die "Failed to install DuckBrain. Check your internet connection and try again."
    fi
    info "DuckBrain installed from PyPI"
    return 0
}

# ── Verification ──────────────────────────────────────────────────────────────

verify_installation() {
    step "Verifying installation"

    local duckbrain_path
    if duckbrain_path="$(command -v duckbrain 2>/dev/null)"; then
        info "duckbrain binary found at: ${duckbrain_path}"
    else
        warn "duckbrain not on PATH. Checking uv tool locations..."
        if [[ -f "${HOME}/.local/bin/duckbrain" ]]; then
            info "duckbrain found at: ${HOME}/.local/bin/duckbrain"
            duckbrain_path="${HOME}/.local/bin/duckbrain"
        else
            error "duckbrain binary not found after installation."
            echo "  Try adding ~/.local/bin to your PATH, or re-run the installer."
            return 1
        fi
    fi

    # Try to get version
    local version
    version="$("$duckbrain_path" --version 2>/dev/null || true)"
    if [[ -n "$version" ]]; then
        info "DuckBrain version: ${version}"
    else
        warn "Could not determine DuckBrain version (--version not available in MCP mode)."
        info "duckbrain binary is executable and appears correct."
    fi

    return 0
}

verify_config() {
    local config_path="$1"
    step "Verifying Claude Desktop configuration"

    if [[ ! -f "$config_path" ]]; then
        error "Config file not found at: ${config_path}"
        return 1
    fi

    if ! python3 -c "
import json, sys

config_path = sys.argv[1]
with open(config_path) as f:
    c = json.load(f)
db = c.get('mcpServers', {}).get('duckbrain', {})
assert 'command' in db, 'Missing command'
assert 'env' in db, 'Missing env'
assert 'VAULT_PATH' in db['env'], 'Missing VAULT_PATH env var'
print('Config structure valid')
" "$config_path" 2>&1; then
        return 1
    fi

    info "Claude Desktop configuration is valid"
    return 0
}

# ── Uninstall ─────────────────────────────────────────────────────────────────

do_uninstall() {
    local os="$1"
    local config_path
    config_path="$(detect_config_path "$os")"

    heading "Uninstalling DuckBrain"
    echo ""

    # Remove from Claude config
    if [[ -f "$config_path" ]]; then
        step "Removing DuckBrain from Claude Desktop config"
        backup_config "$config_path"

        local py_script
        py_script="$(mktemp)"
        cat > "$py_script" << 'PYEOF'
import json
import sys

config_path = sys.argv[1]

with open(config_path) as f:
    config = json.load(f)

config.get('mcpServers', {}).pop('duckbrain', None)

# Clean up empty mcpServers
if not config.get('mcpServers'):
    config.pop('mcpServers', None)

tmp = config_path + '.tmp'
with open(tmp, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
import os
os.replace(tmp, config_path)
PYEOF

        python3 "$py_script" "$config_path"
        local py_exit=$?
        rm -f "$py_script"

        if [[ $py_exit -eq 0 ]]; then
            info "Removed DuckBrain from Claude Desktop config"
        else
            warn "Failed to cleanly remove DuckBrain from config"
        fi
    fi

    # Uninstall tool
    step "Removing DuckBrain binary"
    if uv tool uninstall "$DUCKBRAIN_PACKAGE" 2>/dev/null; then
        info "DuckBrain uninstalled via uv"
    else
        warn "DuckBrain was not installed via uv, or already removed."
    fi

    # Remove backup if it exists
    local backup_path="${config_path}${CONFIG_BACKUP_SUFFIX}"
    if [[ -f "$backup_path" ]]; then
        echo ""
        warn "Backup config file still exists: ${backup_path}"
        echo "  Remove it manually if you don't need it:"
        echo "    rm \"${backup_path}\""
    fi

    echo ""
    info "Uninstall complete"
}

# ── Help ──────────────────────────────────────────────────────────────────────

show_help() {
    cat <<EOF
${BOLD}${SCRIPT_NAME} — DuckBrain MCP Server Installer (macOS / Linux)${NC}

Install DuckBrain and configure it for Claude Desktop in one command.

${BOLD}Usage:${NC}
  ./${SCRIPT_NAME}               Interactive setup
  ./${SCRIPT_NAME} --help        Show this help
  ./${SCRIPT_NAME} --uninstall   Remove DuckBrain and its config entries

${BOLD}What it does:${NC}
  1. Checks prerequisites (uv, Claude Desktop)
  2. Prompts for your Obsidian vault path and DuckBrain repo path
  3. Installs DuckBrain via "uv tool install"
  4. Configures Claude Desktop to use DuckBrain as an MCP server
  5. Validates the configuration
  6. Prints next steps

${BOLD}Platforms:${NC}
  macOS 12+  •  Linux (Ubuntu 20+, Fedora, etc.)

${BOLD}Prerequisites:${NC}
  - uv (https://astral.sh/uv/install.sh)
  - Claude Desktop (https://claude.ai/download)
  - An Obsidian vault

${BOLD}Environment variables:${NC}
  VAULT_PATH    Set this to skip the vault path prompt
  REPO_PATH     Set this to skip the repo path prompt

${BOLD}Troubleshooting:${NC}
  See docs/troubleshooting.md or visit:
  ${REPO_URL}/issues

EOF
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
    # Parse flags
    local mode="install"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --uninstall)
                mode="uninstall"
                shift
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # ── Banner ─────────────────────────────────────────────────────────────
    echo ""
    echo "${BOLD}  🦆  DuckBrain Setup${NC}"
    echo "  DuckDB-backed MCP memory server for Obsidian vaults"
    echo "  ${REPO_URL}"
    echo ""

    local os
    os="$(detect_os)"

    if [[ "$os" == "unknown" ]]; then
        die "Unsupported operating system: $(uname -s). This script supports macOS and Linux."
    fi

    # ── Uninstall mode ─────────────────────────────────────────────────────
    if [[ "$mode" == "uninstall" ]]; then
        do_uninstall "$os"
        exit 0
    fi

    # ── Install mode ───────────────────────────────────────────────────────

    # 1. Check prerequisites
    step "Checking prerequisites"
    check_uv || exit 1
    check_claude_desktop "$os" || exit 1
    info "All prerequisites met"

    # 2. Gather configuration
    step "Configuration"

    # Vault path
    local vault_path="${VAULT_PATH:-}"
    if [[ -z "$vault_path" ]]; then
        local default_vault
        default_vault="$(find_vault_path)"
        echo ""
        echo "  Enter the path to your Obsidian vault."
        echo "  (Press Enter for default, or type a custom path)"
        read -r -p "  Vault path [${default_vault}]: " vault_path
        vault_path="${vault_path:-$default_vault}"
        # Expand tilde
        vault_path="${vault_path/#\~/${HOME}}"
    fi

    if [[ ! -d "$vault_path" ]]; then
        warn "Vault directory does not exist yet: ${vault_path}"
        echo "  The script will continue — create the directory before starting Claude Desktop."
        echo ""
    fi

    # Repo path
    local repo_path="${REPO_PATH:-}"
    if [[ -z "$repo_path" ]]; then
        local default_repo="${HOME}/git_repos/duckbrain"
        echo ""
        echo "  Enter the path to the DuckBrain repository."
        echo "  If you have a local clone, the script will install from it."
        echo "  Otherwise, it will install from PyPI (no local repo needed)."
        read -r -p "  Repo path [${default_repo}]: " repo_path
        repo_path="${repo_path:-$default_repo}"
        repo_path="${repo_path/#\~/${HOME}}"
    fi

    echo ""
    echo "  Configuration summary:"
    echo "    OS:          ${os}"
    echo "    Vault path:  ${vault_path}"
    echo "    Repo path:   ${repo_path}"
    echo ""

    # 3. Install
    install_duckbrain "$repo_path"

    # 4. Configure Claude Desktop
    local config_path
    config_path="$(detect_config_path "$os")"

    step "Configuring Claude Desktop"
    echo "  Config file: ${config_path}"
    update_claude_config "$config_path" "$vault_path" "$os"

    # 5. Verify
    step "Verification"
    verify_installation
    verify_config "$config_path"

    # 6. Summary
    step "Setup complete!"
    echo ""
    echo "  ${BOLD}What was done:${NC}"
    echo "  ✓ DuckBrain installed"
    echo "  ✓ Claude Desktop configured"
    echo "  ✓ Config validated"
    echo ""
    echo "  ${BOLD}Next steps:${NC}"
    echo "  1. Restart Claude Desktop"
    echo "  2. Open a new conversation"
    echo "  3. Look for the hammer 🔨 icon in the bottom-right input area"
    echo "  4. You should see DuckBrain tools: vault_search, vault_read, vault_write,"
    echo "     vault_info, vault_context"
    echo ""
    echo "  ${BOLD}Need help?${NC}"
    echo "  • Troubleshooting guide: docs/troubleshooting.md"
    echo "  • GitHub issues: ${REPO_URL}/issues"
    echo ""

    # Check config backup
    local backup_path="${config_path}${CONFIG_BACKUP_SUFFIX}"
    if [[ -f "$backup_path" ]]; then
        echo "  ${YELLOW}ℹ A backup of your previous config was saved to:${NC}"
        echo "    ${backup_path}"
        echo ""
    fi
}

main "$@"
