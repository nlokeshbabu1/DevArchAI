#!/bin/bash
# ===========================================
# DevArchAI - Pre-Commit Hooks Installation
# ===========================================
# Run this script to set up pre-commit hooks
# ===========================================

set -e

echo "🔧 DevArchAI - Pre-Commit Hooks Setup"
echo "======================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip first."
    exit 1
fi

echo "✅ pip found: $(pip3 --version)"

# Install pre-commit
echo ""
echo "📦 Installing pre-commit..."
pip3 install pre-commit

# Verify installation
if ! command -v pre-commit &> /dev/null; then
    echo "❌ Failed to install pre-commit. Please check pip installation."
    exit 1
fi

echo "✅ pre-commit installed: $(pre-commit --version)"

# Install hooks
echo ""
echo "🔗 Installing git hooks..."
pre-commit install

echo "✅ Git hooks installed"

# Install hook dependencies
echo ""
echo "📦 Installing hook dependencies..."

# Python dependencies for hooks
pip3 install black isort flake8 mypy ruff detect-secrets

echo "✅ Hook dependencies installed"

# Verify hooks are working
echo ""
echo "🧪 Testing hooks..."
pre-commit run --all-files || true

echo ""
echo "======================================"
echo "✅ Pre-Commit Setup Complete!"
echo "======================================"
echo ""
echo "Your git hooks are now active."
echo ""
echo "To run hooks manually:"
echo "  pre-commit run --all-files"
echo ""
echo "To update hooks:"
echo "  pre-commit autoupdate"
echo ""
echo "To uninstall:"
echo "  pre-commit uninstall"
echo ""
echo "📚 See PRE_COMMIT_SETUP.md for more details."
echo ""
