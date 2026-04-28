#!/bin/bash
# Install FileSqueeze pre-commit hooks

set -e

echo "🔧 Installing FileSqueeze pre-commit hooks..."

# Copy the pre-commit hook to .git/hooks/
cp .githooks/pre-commit .git/hooks/pre-commit

# Make it executable
chmod +x .git/hooks/pre-commit

echo "✅ Pre-commit hooks installed successfully"
echo ""
echo "Smoke tests will now run automatically before each commit."
echo "To test manually: pytest tests/smoke/ -v"