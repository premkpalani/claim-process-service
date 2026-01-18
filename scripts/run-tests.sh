#!/bin/bash
# Pre-commit hook script to run tests
# This script ensures all tests pass before allowing a commit
#
# Skip tests with: SKIP_TESTS=1 git commit -m "message"
# Or use: git commit --no-verify -m "message" (skips ALL hooks)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Allow skipping tests with environment variable
if [ "$SKIP_TESTS" = "1" ]; then
    echo -e "${YELLOW}⚠ Tests skipped (SKIP_TESTS=1)${NC}"
    exit 0
fi

echo "Running tests..."

# Check if we're in a virtual environment or use system Python
if [ -n "$VIRTUAL_ENV" ]; then
    PYTEST_CMD="pytest"
elif [ -f "venv/bin/pytest" ]; then
    PYTEST_CMD="venv/bin/pytest"
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST_CMD=".venv/bin/pytest"
else
    # Try to find pytest
    if command -v pytest &> /dev/null; then
        PYTEST_CMD="pytest"
    else
        PYTEST_CMD="python3 -m pytest"
    fi
fi

# Check if required dependencies are available
python3 -c "import sqlmodel" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠ Dependencies not installed. Skipping tests.${NC}"
    echo -e "${YELLOW}  Run 'pip install -r requirements.txt' to enable test validation.${NC}"
    echo -e "${YELLOW}  Tests will still run in CI/CD pipeline.${NC}"
    exit 0
fi

# Run tests with minimal output
$PYTEST_CMD --tb=short -q tests/

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Tests failed! Commit blocked.${NC}"
    echo -e "${RED}  Fix the failing tests or use SKIP_TESTS=1 to bypass.${NC}"
    exit 1
fi
