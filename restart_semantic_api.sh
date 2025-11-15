#!/bin/bash
# Quick script to restart semantic search API

echo "=========================================="
echo "🔄 Restarting Semantic Search API"
echo "=========================================="
echo ""

# Find and kill existing semantic API process
SEMANTIC_PID=$(ps aux | grep "python3 semantic_api.py" | grep -v grep | awk '{print $2}')

if [ -n "$SEMANTIC_PID" ]; then
    echo "Stopping existing semantic API (PID: $SEMANTIC_PID)..."
    kill $SEMANTIC_PID 2>/dev/null
    sleep 1
    
    # Check if still running
    if ps -p $SEMANTIC_PID > /dev/null 2>&1; then
        echo "Force killing..."
        kill -9 $SEMANTIC_PID 2>/dev/null
    fi
    echo "✓ Stopped"
else
    echo "No existing semantic API process found"
fi

echo ""
echo "Starting semantic search API..."
echo ""

# Start semantic API
python3 semantic_api.py

