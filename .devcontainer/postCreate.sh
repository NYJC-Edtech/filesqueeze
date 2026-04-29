#!/bin/bash
set -e

echo "📦 Installing Poetry..."
pip install poetry

echo "🔧 Installing Python dependencies..."
poetry install --with dev --with ocr

echo "🔧 Configuring GitHub..."
if [ -n "$GH_USERNAME" ] && [ -n "$GH_EMAIL" ]; then
    echo "Setting up GitHub for $GH_USERNAME"
    gh auth setup-git
    git config --global user.name "$GH_USERNAME"
    git config --global user.email "$GH_EMAIL"
    echo "✅ GitHub configured successfully"
else
    echo "⚠️  GH_USERNAME and GH_EMAIL not set - skipping GitHub configuration"
fi

echo "🎉 Development environment setup complete!"
