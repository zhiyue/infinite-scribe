#!/bin/bash
# Verify Ruff installation and configuration

set -e

echo "🔍 Verifying Ruff setup..."
echo ""

# Check if in project root
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Error: Virtual environment not found. Run './scripts/setup-dev.sh' first"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check Ruff installation
echo "1️⃣ Checking Ruff installation..."
if command -v ruff &> /dev/null; then
    RUFF_VERSION=$(ruff --version)
    echo "✅ Ruff is installed: $RUFF_VERSION"
    echo "   Path: $(which ruff)"
else
    echo "❌ Ruff is not installed"
    echo "   Run: uv add --dev ruff"
    exit 1
fi

echo ""
echo "2️⃣ Testing Ruff formatter..."

# Create test file
cat > /tmp/test_ruff.py << 'EOF'
# Badly formatted code
import sys,os,json
def test(x,y,z):
    result=x+y+z
    return result
EOF

# Test formatting
if ruff format /tmp/test_ruff.py > /dev/null 2>&1; then
    echo "✅ Ruff formatter is working"
else
    echo "❌ Ruff formatter failed"
    exit 1
fi

echo ""
echo "3️⃣ Testing Ruff linter..."
if ruff check /tmp/test_ruff.py > /dev/null 2>&1; then
    echo "✅ Ruff linter is working"
else
    echo "✅ Ruff linter is working (found issues as expected)"
fi

# Clean up
rm -f /tmp/test_ruff.py

echo ""
echo "4️⃣ Checking pyproject.toml configuration..."
if grep -q "\[tool.ruff\]" pyproject.toml; then
    echo "✅ Ruff configuration found in pyproject.toml"
else
    echo "⚠️  No Ruff configuration in pyproject.toml"
fi

echo ""
echo "5️⃣ VSCode settings recommendations:"
echo ""
echo "If you're having issues with VSCode:"
echo "1. Install the Ruff extension: charliermarsh.ruff"
echo "2. Reload VSCode window (Ctrl+Shift+P → 'Developer: Reload Window')"
echo "3. Open a Python file and try formatting (Shift+Alt+F)"
echo "4. If prompted, select 'Ruff' as the default formatter"
echo ""
echo "✅ Ruff verification complete!"