#!/bin/bash
# Quick start script for the frontend

echo "Starting web server for frontend..."
echo "Open http://localhost:8000/frontend/ in your browser"
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
python3 -m http.server 8000

