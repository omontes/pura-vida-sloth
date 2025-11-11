#!/bin/bash

# Pura Vida Sloth - Backend Startup Script
# Usage: ./start_backend.sh

echo "Canopy Intelligence - Starting Backend..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create .env with Neo4j credentials:"
    echo ""
    echo "NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io"
    echo "NEO4J_USERNAME=neo4j"
    echo "NEO4J_PASSWORD=your-password"
    echo "NEO4J_DATABASE=neo4j"
    exit 1
fi

# Check if requirements are installed
echo "📦 Checking dependencies..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing API dependencies..."
    pip install -r requirements-api.txt
fi

echo "✅ Dependencies OK"
echo ""

# Start FastAPI server
echo "🚀 Starting FastAPI on http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
