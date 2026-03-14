#!/bin/bash
#
# Telnyx Fax Webhook Test Runner
# Executes comprehensive integration tests for fax ingestion pipeline
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Fax Webhook Integration Tests"
echo "=========================================="
echo ""

cd "$BACKEND_ROOT"

# Check Python environment
if ! command -v python &> /dev/null; then
    echo "ERROR: Python not found."
    exit 1
fi

echo "Python version: $(python --version)"
echo ""

# Install test dependencies if not present
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-cov requests mock --upgrade 2>/dev/null || true

echo ""
echo "Running Telnyx webhook integration tests..."
echo ""

# Run tests with verbose output
python -m pytest tests/test_fax_webhook_integration.py -v --tb=short \
    --cov=core_app/api/fax_webhook_router \
    --cov=core_app/services/fax_service \
    --cov-report=html:htmlcov \
    --cov-report=term \
    "$@"

TEST_RESULT=$?

echo ""
echo "=========================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ All tests passed"
else
    echo "✗ Tests failed (exit code: $TEST_RESULT)"
fi
echo "=========================================="

# Generate coverage report
if [ -d htmlcov ]; then
    echo ""
    echo "Coverage report generated in: htmlcov/index.html"
fi

exit $TEST_RESULT
