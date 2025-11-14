#!/bin/bash
# Quick start script for the frontend

echo "=========================================="
echo "🍜 AFURI Menu Search - Frontend Server"
echo "=========================================="
echo ""
echo "Starting Solr proxy server on port 8888..."
echo "Starting frontend server on port 8000..."
echo ""
echo "📱 Open in your browser:"
echo "   http://localhost:8000/frontend/"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Start Solr proxy in background
python3 solr_proxy.py &
PROXY_PID=$!

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $PROXY_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Start frontend server
python3 -m http.server 8000

# Cleanup if frontend server exits
cleanup

