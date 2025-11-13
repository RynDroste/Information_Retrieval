#!/bin/bash
# Quick start script for the frontend

echo "=========================================="
echo "🍜 AFURI Menu Search - Frontend Server"
echo "=========================================="
echo ""
echo "Starting frontend server on port 8000..."
echo ""
echo "📱 Open in your browser:"
echo "   http://localhost:8000/frontend/"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

cd "$(dirname "$0")"
python3 -m http.server 8000

