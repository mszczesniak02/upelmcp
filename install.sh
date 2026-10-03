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

## 3. Helper function to register MCP config
set_mcp_config() {
    local config_file="$1"
    mkdir -p "$(dirname "$config_file")"
    "$PY" -c "
import json
from pathlib import Path
p = Path('$config_file')
data = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {'mcpServers': {}}
data.setdefault('mcpServers', {})['upel'] = {'command': '$PY', 'args': ['$REPO_DIR/server.py']}
p.write_text(json.dumps(data, indent=2))
"
    echo "   Configured MCP server in: $config_file"
}

register_antigravity() {
    local target_dir="$HOME/.gemini/config"
    echo "-> Installing for Antigravity / Gemini CLI in $target_dir..."
    mkdir -p "$target_dir/skills/upel"
    cp "$REPO_DIR/skills/upel/SKILL.md" "$target_dir/skills/upel/SKILL.md"
    set_mcp_config "$target_dir/mcp_config.json"
    echo "   Installed skill to: $target_dir/skills/upel/SKILL.md"
}

register_claude_desktop() {
    local claude_dir="$HOME/.config/Claude"
    [ "$(uname)" = "Darwin" ] && claude_dir="$HOME/Library/Application Support/Claude"
    echo "-> Installing for Claude Desktop..."
    set_mcp_config "$claude_dir/claude_desktop_config.json"
}

register_cursor() {
    echo "-> Installing for Cursor..."
    set_mcp_config "$HOME/.cursor/mcp.json"
}

register_kiro() {
    local kiro_dir="$HOME/.kiro"
    echo "-> Installing for Kiro / kiro-chat..."
    set_mcp_config "$kiro_dir/settings/mcp.json"

    local agent_path="$kiro_dir/agents/upel.json"
    mkdir -p "$kiro_dir/agents"
    "$PY" -c "
import json
from pathlib import Path
agent_cfg = {
    'name': 'upel',
    'description': 'AGH UPeL assistant',
    'mcpServers': {'upel': {'command': '$PY', 'args': ['$REPO_DIR/server.py']}},
    'tools': ['read', 'write', 'shell', '@upel']
}
Path('$agent_path').write_text(json.dumps(agent_cfg, indent=2))
"
    echo "   Created Kiro agent in: $agent_path"
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
    echo "  4) Kiro / kiro-chat"
    echo "  5) Workspace local (.agent/)"
    echo "  6) All supported agents detected"
    read -rp "Enter choice [1-6]: " AGENT_CHOICE
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
    4|kiro|kiro-chat)
        register_kiro
        ;;
    5|workspace|local)
        register_workspace
        ;;
    6|all)
        register_antigravity
        register_claude_desktop
        register_cursor
        register_kiro
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
echo "=========================================================="
echo ""
echo " What this does:"
echo "   Connects your AI agent to AGH UPeL (Moodle) with read-only access"
echo "   to list courses, inspect exercises, and download task instructions"
echo "   into clean, space-free .md files with diagrams."
echo ""
echo " How to use it with your agent:"
echo "   1. Restart or reload your AI agent / IDE (Antigravity, Claude, Cursor, or Kiro)"
echo "      so it picks up the newly configured tools and skill."
echo ""
echo "   2. Ask your agent in chat using natural language:"
echo "      - 'List my courses on UPeL'"
echo "      - 'Show me exercises in course 1060'"
echo "      - 'Download all tasks for Operating Systems into markdown'"
echo ""
echo "   3. Automatic Authentication:"
echo "      On your first request, the agent will automatically detect if"
echo "      you are not logged in and open an AGH SSO login browser window."
echo "      (You can also log in manually right now by running:"
echo "       $PY $REPO_DIR/auth.py)"
echo "=========================================================="
