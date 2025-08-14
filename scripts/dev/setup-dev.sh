#!/bin/bash
# Setup development environment using uv

set -e

echo "🚀 Setting up development environment..."

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Install uv if not available
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    uv venv
fi

# Install all dependencies (including dev dependencies)
echo "📦 Installing project dependencies..."
uv sync --dev

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Install frontend dependencies
if [ -d "apps/frontend" ]; then
    echo "📦 Installing frontend dependencies..."
    pnpm install
fi

echo "✅ Development environment setup complete!"
echo ""
echo "📝 Quick start:"
echo "   1. Activate Python environment: source .venv/bin/activate"
echo "   2. Start infrastructure: pnpm infra:up"
echo "   3. Run tests: pnpm test"
echo "   4. Start development: pnpm dev"
echo ""
echo "💡 Pre-commit hooks are now active. They will run automatically on git commit."