#!/bin/bash
# Install FileSqueeze git hooks

set -e

echo "🔧 Installing FileSqueeze git hooks..."

# Copy the hooks to .git/hooks/
cp .githooks/pre-commit .git/hooks/pre-commit
cp .githooks/post-edit .git/hooks/post-edit

# Make them executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/post-edit

echo "✅ Git hooks installed successfully"
echo ""
echo "📋 Installed hooks:"
echo "  • pre-commit: Ruff type checking + smoke tests"
echo "  • post-edit: Auto-format Python files with ruff"
echo ""
echo "To test manually:"
echo "  • pytest tests/smoke/ -v"
echo "  • ruff check . --select ANN"