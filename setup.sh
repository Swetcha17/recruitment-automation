#!/bin/bash

# Resume Search - Complete Setup Script
# Run this once to set up everything

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "Python found: $(python3 --version)"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install -U pip -q

# Install requirements
echo ""
echo "Installing dependencies (this may take 2-3 minutes)..."
pip install -r requirements.txt -q

echo ""
echo "✓ All dependencies installed"

# Parse resumes
echo "  Step 1: Parsing Resumes"
python parse_resumes.py

# Build FAISS index
echo "  Step 2: Building FAISS Index"
python build_faiss.py

# Build FTS index
echo "  Step 3: Building SQLite FTS Index"
python build_fts.py

# Done
echo " Setup Complete!"
echo "To start the search interface, run:"
echo ""
echo "    source .venv/bin/activate"
echo "    streamlit run app.py"
echo "Then open http://localhost:8501 in your browser"