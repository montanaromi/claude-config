#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SKILLS_DIR="$CLAUDE_DIR/skills"

# --- Pre-flight checks ---

if [ ! -d "$CLAUDE_DIR" ]; then
    echo "Error: $CLAUDE_DIR does not exist."
    echo "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
    exit 1
fi

# --- Create skills directory if needed ---

mkdir -p "$SKILLS_DIR"

# --- Symlink each skill ---

SKILLS=("onboard" "readme" "commit" "blitzy-pr" "test" "aap" "dev-doc" "z" "tech-spec" "chuck" "logger" "use-case" "kurt" "aditya" "next" "retrigger" "skill-writer" "techdocs-organize" "trace" "archie-bootstrap")
LINKED=()

for skill in "${SKILLS[@]}"; do
    src="$SCRIPT_DIR/skills/$skill"
    dest="$SKILLS_DIR/$skill"

    if [ ! -d "$src" ]; then
        echo "Warning: $src not found, skipping"
        continue
    fi

    # Remove existing directory or symlink
    if [ -L "$dest" ]; then
        rm "$dest"
    elif [ -d "$dest" ]; then
        echo "Replacing directory $dest with symlink"
        rm -rf "$dest"
    fi

    ln -sfn "$src" "$dest"
    LINKED+=("$skill")
done

# --- Install Python dependencies ---

echo ""
echo "Installing Python dependencies..."
if command -v pip3 &>/dev/null; then
    pip3 install -r "$SCRIPT_DIR/requirements.txt" --quiet
elif command -v pip &>/dev/null; then
    pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
else
    echo "Warning: pip not found. Install dependencies manually:"
    echo "  pip install -r $SCRIPT_DIR/requirements.txt"
fi

# --- Verify tree-sitter installation ---

if python3 -c "import tree_sitter" 2>/dev/null; then
    echo "  tree-sitter core: OK"
else
    echo "Warning: tree-sitter not importable. The /onboard and /aap skills require it."
    echo "  Try: pip3 install -r $SCRIPT_DIR/requirements.txt"
fi

# --- Summary ---

echo ""
echo "=== claude-config installed ==="
echo ""
for skill in "${LINKED[@]}"; do
    echo "  /$skill -> $SCRIPT_DIR/skills/$skill"
done
echo ""
echo "Skills are ready. Start a new Claude Code session to use them."
