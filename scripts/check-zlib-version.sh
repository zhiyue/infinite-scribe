#!/bin/bash
# CVE-2023-45853 zlib Version Verification Script
# This script checks if the current environment has zlib >= 1.3.0 to mitigate CVE-2023-45853

set -e

echo "=== CVE-2023-45853 zlib Vulnerability Check ==="
echo ""

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "🐳 Running inside Docker container"
    CONTAINER="YES"
else
    echo "🖥️ Running on host system"
    CONTAINER="NO"
fi
echo ""

# Check system zlib1g package version
echo "📦 System zlib1g Package:"
if command -v dpkg-query &> /dev/null; then
    ZLIB_PKG_VERSION=$(dpkg-query -W -f='${Version}' zlib1g 2>/dev/null || echo "unknown")
    echo "  Version: $ZLIB_PKG_VERSION"
else
    echo "  dpkg not available (non-Debian system)"
    ZLIB_PKG_VERSION="unknown"
fi
echo ""

# Check Python zlib module version
echo "🐍 Python zlib Module:"
if command -v python3 &> /dev/null; then
    PYTHON_ZLIB=$(python3 -c "import zlib; print(zlib.ZLIB_VERSION)" 2>/dev/null || echo "unknown")
    echo "  Version: $PYTHON_ZLIB"
    
    # Parse version and check if >= 1.3.0
    if python3 -c "
import zlib
import sys
try:
    version_parts = tuple(map(int, zlib.ZLIB_VERSION.split('.')))
    if version_parts >= (1, 3, 0):
        print('  Status: ✅ SECURE (>= 1.3.0)')
        sys.exit(0)
    else:
        print('  Status: ⚠️ VULNERABLE (< 1.3.0)')
        sys.exit(1)
except Exception as e:
    print(f'  Status: ❓ UNKNOWN (error: {e})')
    sys.exit(2)
" 2>/dev/null; then
        PYTHON_SECURE="YES"
    else
        PYTHON_SECURE="NO"
    fi
else
    echo "  python3 not available"
    PYTHON_ZLIB="unknown"
    PYTHON_SECURE="UNKNOWN"
fi
echo ""

# Overall assessment
echo "🔒 CVE-2023-45853 Assessment:"
if [ "$PYTHON_SECURE" = "YES" ]; then
    echo "  Result: ✅ MITIGATED - zlib >= 1.3.0 detected"
    echo "  Action: No further action required"
elif [ "$PYTHON_SECURE" = "NO" ]; then
    echo "  Result: ⚠️ VULNERABLE - zlib < 1.3.0 detected"
    echo "  Risk: Medium (requires malicious ZIP file processing)"
    echo "  Action: Consider upgrading base image or accepting calculated risk"
else
    echo "  Result: ❓ UNKNOWN - Unable to determine zlib version"
    echo "  Action: Manual investigation required"
fi
echo ""

# Application-specific risk assessment
echo "🎯 Application Risk Assessment:"
if python3 -c "
import sys
import importlib.util

# Check if common ZIP processing modules are available
zip_modules = ['zipfile', 'gzip', 'zlib']
found_modules = []

for module in zip_modules:
    if importlib.util.find_spec(module) is not None:
        found_modules.append(module)

if found_modules:
    print(f'  ZIP modules found: {', '.join(found_modules)}')
    print('  Risk Level: MEDIUM - Application can process ZIP/compressed files')
    print('  Recommendation: Validate input files and consider upgrading zlib')
else:
    print('  ZIP modules: None found')
    print('  Risk Level: LOW - Application unlikely to process ZIP files')
" 2>/dev/null; then
    :
else
    echo "  Unable to assess application risk"
fi
echo ""

# Exit with appropriate code
if [ "$PYTHON_SECURE" = "YES" ]; then
    exit 0
elif [ "$PYTHON_SECURE" = "NO" ]; then
    exit 1
else
    exit 2
fi