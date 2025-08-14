#!/bin/bash
# Setup pre-commit hooks for the project

set -e

echo "🔧 Setting up pre-commit hooks..."

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

# Sync development dependencies (includes pre-commit)
echo "📦 Installing dependencies with uv..."
uv sync --dev

# Activate virtual environment for subsequent commands
source .venv/bin/activate

# Verify pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "❌ Error: pre-commit not found after uv sync. Please check your pyproject.toml"
    exit 1
fi

# Install git hooks
echo "🪝 Installing git hooks..."
pre-commit install

# Install commit-msg hook for conventional commits (optional)
pre-commit install --hook-type commit-msg 2>/dev/null || true

# Run pre-commit on all files to download dependencies
echo "📥 Downloading pre-commit dependencies (this may take a few minutes)..."
pre-commit run --all-files || true

echo "✅ Pre-commit setup complete!"
echo ""
echo "📝 Usage:"
echo "   - Hooks will run automatically on 'git commit'"
echo "   - Run manually: 'pre-commit run --all-files'"
echo "   - Update hooks: 'pre-commit autoupdate'"
echo ""
echo "💡 Tip: If a commit fails, fix the issues and run 'git add' before committing again"