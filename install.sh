#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

echo "=========================================================="
echo " UPeL AGH MCP Server & Skill Installer"
echo " Repo directory: $REPO_DIR"
echo "=========================================================="

# 1. Check Python
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    echo "Error: Python 3 not found. Please install python3." >&2
    exit 1
fi

# 2. Setup isolated virtualenv inside repo directory
if [ ! -d "$REPO_DIR/pyenv" ]; then
    echo "Creating virtual environment in $REPO_DIR/pyenv..."
    "$PYTHON_BIN" -m venv "$REPO_DIR/pyenv"
fi

PY="$REPO_DIR/pyenv/bin/python"
PIP="$REPO_DIR/pyenv/bin/pip"

echo "Installing / verifying dependencies..."
"$PIP" install --upgrade pip --quiet
"$PIP" install -r "$REPO_DIR/requirements.txt" --quiet

echo "Ensuring Playwright Chromium is installed..."
"$PY" -m playwright install chromium

# 3. Helper functions to register agent skills & MCP
register_antigravity() {
    local target_dir="$HOME/.gemini/config"
    echo "-> Installing for Antigravity / Gemini CLI in $target_dir..."
    mkdir -p "$target_dir/skills/upel"
    cp "$REPO_DIR/skills/upel/SKILL.md" "$target_dir/skills/upel/SKILL.md"

    local mcp_config="$target_dir/mcp_config.json"
    if [ ! -f "$mcp_config" ]; then
        echo '{"mcpServers":{}}' > "$mcp_config"
    fi

    "$PY" -c "
import json
from pathlib import Path
p = Path('$mcp_config')
data = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {'mcpServers': {}}
data.setdefault('mcpServers', {})['upel'] = {
    'command': '$PY',
    'args': ['$REPO_DIR/server.py']
}
p.write_text(json.dumps(data, indent=2))
"
    echo "   Installed skill to: $target_dir/skills/upel/SKILL.md"
    echo "   Configured MCP server in: $mcp_config"
}

register_claude_desktop() {
    local claude_dir=""
    if [ "$(uname)" = "Darwin" ]; then
        claude_dir="$HOME/Library/Application Support/Claude"
    else
        claude_dir="$HOME/.config/Claude"
    fi
    mkdir -p "$claude_dir"
    local config_file="$claude_dir/claude_desktop_config.json"
    echo "-> Installing for Claude Desktop in $config_file..."

    "$PY" -c "
import json
from pathlib import Path
p = Path('$config_file')
data = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {'mcpServers': {}}
data.setdefault('mcpServers', {})['upel'] = {
    'command': '$PY',
    'args': ['$REPO_DIR/server.py']
}
p.write_text(json.dumps(data, indent=2))
"
    echo "   Configured MCP server in: $config_file"
}

register_cursor() {
    local cursor_dir="$HOME/.cursor"
    mkdir -p "$cursor_dir"
    local config_file="$cursor_dir/mcp.json"
    echo "-> Installing for Cursor in $config_file..."

    "$PY" -c "
import json
from pathlib import Path
p = Path('$config_file')
data = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {'mcpServers': {}}
data.setdefault('mcpServers', {})['mcpServers'] = data.get('mcpServers', {})
data['mcpServers']['upel'] = {
    'command': '$PY',
    'args': ['$REPO_DIR/server.py']
}
p.write_text(json.dumps(data, indent=2))
"
    echo "   Configured MCP server in: $config_file"
}

register_workspace() {
    echo "-> Installing workspace skill in current directory (.agent/)..."
    mkdir -p "$PWD/.agent/skills/upel"
    cp "$REPO_DIR/skills/upel/SKILL.md" "$PWD/.agent/skills/upel/SKILL.md"
    echo "   Installed skill to: $PWD/.agent/skills/upel/SKILL.md"
}

# 4. Prompt user for target agent
AGENT_CHOICE="${1:-}"

if [ -z "$AGENT_CHOICE" ]; then
    echo ""
    echo "Which AI agent / environment do you want to configure?"
    echo "  1) Antigravity / Gemini CLI"
    echo "  2) Claude Desktop"
    echo "  3) Cursor"
    echo "  4) Workspace local (.agent/)"
    echo "  5) All supported agents detected"
    read -rp "Enter choice [1-5]: " AGENT_CHOICE
fi

case "$AGENT_CHOICE" in
    1|antigravity|gemini)
        register_antigravity
        ;;
    2|claude|claude-desktop)
        register_claude_desktop
        ;;
    3|cursor)
        register_cursor
        ;;
    4|workspace|local)
        register_workspace
        ;;
    5|all)
        register_antigravity
        register_claude_desktop
        register_cursor
        register_workspace
        ;;
    *)
        echo "Unknown choice: $AGENT_CHOICE. Installing to Antigravity as default..."
        register_antigravity
        ;;
esac

echo ""
echo "=========================================================="
echo " Installation Complete!"
echo " Python environment & MCP server live in: $REPO_DIR"
echo " Initial auth: $PY $REPO_DIR/auth.py"
echo "=========================================================="
