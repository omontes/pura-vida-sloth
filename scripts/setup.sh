#!/bin/bash

# Financial Document Harvester - Setup Script
# ============================================

echo "================================================"
echo "Financial Document Harvester - Setup"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python $required_version or higher is required"
    echo "   Current version: $python_version"
    exit 1
fi

echo "✓ Python version: $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create data directories
echo "Creating data directories..."
mkdir -p data/sec
mkdir -p data/earnings
mkdir -p data/research
mkdir -p data/regulatory
mkdir -p data/press_releases
echo "✓ Data directories created"
echo ""

# Test import
echo "Testing installation..."
python -c "from src.downloaders import SECDownloader; print('✓ Imports working')"
echo ""

echo "================================================"
echo "Setup Complete! 🎉"
echo "================================================"
echo ""
echo "To get started:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run harvester: python financial_doc_harvester.py"
echo ""
echo "For help: python financial_doc_harvester.py --help"
echo ""
