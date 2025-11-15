#!/bin/bash
# Quick start script for the frontend

USE_SEMANTIC=${1:-false}

# Function to kill existing processes
kill_existing_processes() {
    echo "Checking for existing processes..."
    local found_any=false
    
    # Find and kill start_frontend.sh processes (excluding current one)
    START_FRONTEND_PIDS=$(ps aux | grep "[s]tart_frontend.sh" | grep -v "$$" | awk '{print $2}')
    if [ -n "$START_FRONTEND_PIDS" ]; then
        echo "  → Found existing start_frontend.sh processes, killing them..."
        echo "$START_FRONTEND_PIDS" | xargs kill -9 2>/dev/null
        found_any=true
        sleep 1
    fi
    
    # Find and kill solr_proxy.py processes
    SOLR_PROXY_PIDS=$(ps aux | grep "[s]olr_proxy.py" | awk '{print $2}')
    if [ -n "$SOLR_PROXY_PIDS" ]; then
        echo "  → Found existing solr_proxy.py processes, killing them..."
        echo "$SOLR_PROXY_PIDS" | xargs kill -9 2>/dev/null
        found_any=true
        sleep 1
    fi
    
    # Find and kill semantic_api.py processes
    SEMANTIC_API_PIDS=$(ps aux | grep "[s]emantic_api.py" | awk '{print $2}')
    if [ -n "$SEMANTIC_API_PIDS" ]; then
        echo "  → Found existing semantic_api.py processes, killing them..."
        echo "$SEMANTIC_API_PIDS" | xargs kill -9 2>/dev/null
        found_any=true
        sleep 1
    fi
    
    # Find and kill http.server processes (check by process name and port)
    HTTP_SERVER_PIDS=$(ps aux | grep "[h]ttp.server.*8000" | awk '{print $2}')
    if [ -n "$HTTP_SERVER_PIDS" ]; then
        echo "  → Found existing http.server processes, killing them..."
        echo "$HTTP_SERVER_PIDS" | xargs kill -9 2>/dev/null
        found_any=true
        sleep 1
    fi
    
    # Check ports using lsof if available, otherwise use netstat or ps
    if command -v lsof >/dev/null 2>&1; then
        # Find and kill processes using port 8000
        PORT_8000_PIDS=$(lsof -ti:8000 2>/dev/null)
        if [ -n "$PORT_8000_PIDS" ]; then
            echo "  → Found processes using port 8000, killing them..."
            echo "$PORT_8000_PIDS" | xargs kill -9 2>/dev/null
            found_any=true
            sleep 1
        fi
        
        # Find and kill processes using port 8888 (Solr proxy)
        PORT_8888_PIDS=$(lsof -ti:8888 2>/dev/null)
        if [ -n "$PORT_8888_PIDS" ]; then
            echo "  → Found processes using port 8888, killing them..."
            echo "$PORT_8888_PIDS" | xargs kill -9 2>/dev/null
            found_any=true
            sleep 1
        fi
        
        # Find and kill processes using port 8889 (Semantic API)
        PORT_8889_PIDS=$(lsof -ti:8889 2>/dev/null)
        if [ -n "$PORT_8889_PIDS" ]; then
            echo "  → Found processes using port 8889, killing them..."
            echo "$PORT_8889_PIDS" | xargs kill -9 2>/dev/null
            found_any=true
            sleep 1
        fi
    fi
    
    if [ "$found_any" = true ]; then
        echo "✓ Cleanup complete"
    else
        echo "✓ No existing processes found"
    fi
    echo ""
}

# Kill existing processes before starting
kill_existing_processes

echo "=========================================="
echo "🍜 AFURI Menu Search - Frontend Server"
echo "=========================================="
echo ""
echo "Starting Solr proxy server on port 8888..."
if [ "$USE_SEMANTIC" = "true" ]; then
    echo "Checking semantic search setup..."
    echo "  → Will verify/generate embeddings before starting API"
    echo "Starting semantic search API on port 8889..."
fi
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

# Start semantic search API if requested
if [ "$USE_SEMANTIC" = "true" ]; then
    if [ -f "semantic_api.py" ]; then
        # Check if embeddings file exists
        if [ ! -f "data/embeddings.json" ]; then
            echo ""
            echo "⚠ Embeddings file not found: data/embeddings.json"
            echo "Checking if we can generate embeddings..."
            
            # Check if cleaned data exists
            if [ -f "data/cleaned_data.json" ]; then
                echo "✓ Found cleaned_data.json, generating embeddings..."
                echo "This may take a few minutes (first time will download LaBSE model ~1.2GB)..."
                python3 run_pipeline.py --use-labse --skip-scrape --skip-clean
                
                # Check if embeddings were generated successfully
                if [ -f "data/embeddings.json" ]; then
                    EMBEDDING_COUNT=$(python3 -c "import json; data = json.load(open('data/embeddings.json')); print(len(data))" 2>/dev/null || echo "0")
                    echo "✓ Generated embeddings file with $EMBEDDING_COUNT embeddings"
                else
                    echo "⚠ Failed to generate embeddings file"
                    echo "⚠ Semantic search API will start but may not be available"
                fi
            else
                echo "⚠ cleaned_data.json not found"
                echo "⚠ Please run: python3 run_pipeline.py --use-labse --configure-solr"
                echo "⚠ Semantic search API will start but may not be available"
            fi
        else
            # Verify embeddings file is valid
            EMBEDDING_COUNT=$(python3 -c "import json; data = json.load(open('data/embeddings.json')); print(len(data))" 2>/dev/null || echo "0")
            if [ "$EMBEDDING_COUNT" = "0" ]; then
                echo "⚠ Embeddings file exists but appears to be empty or invalid"
                echo "⚠ Regenerating embeddings..."
                if [ -f "data/cleaned_data.json" ]; then
                    python3 run_pipeline.py --use-labse --skip-scrape --skip-clean
                else
                    echo "⚠ cleaned_data.json not found, cannot regenerate embeddings"
                fi
            else
                echo "✓ Found embeddings file with $EMBEDDING_COUNT embeddings"
            fi
        fi
        
        echo ""
        echo "Starting semantic search API..."
        # Ensure we're in the correct directory (absolute path)
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        cd "$SCRIPT_DIR"
        
        # Verify embeddings file exists with absolute path
        EMBEDDINGS_ABS_PATH="$SCRIPT_DIR/data/embeddings.json"
        if [ ! -f "$EMBEDDINGS_ABS_PATH" ]; then
            echo "  ✗ Error: Embeddings file not found at $EMBEDDINGS_ABS_PATH"
            echo "  ⚠ Semantic API will start but will not be available"
        fi
        
        # Start API in background
        python3 semantic_api.py &
        SEMANTIC_PID=$!
        
        # Wait for API server to start
        echo "  → Waiting for API server to start..."
        sleep 2
        
        # Check if API process is still running
        if ! kill -0 $SEMANTIC_PID 2>/dev/null; then
            echo "  ✗ Semantic API process failed to start"
            SEMANTIC_PID=""
        else
            # Trigger initialization by making a status request (retry up to 6 times)
            MAX_RETRIES=6
            RETRY_COUNT=0
            API_READY=false
            
            while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
                # Check if process is still running
                if ! kill -0 $SEMANTIC_PID 2>/dev/null; then
                    echo "  ✗ Semantic API process died unexpectedly"
                    SEMANTIC_PID=""
                    break
                fi
                
                # Make a request to trigger initialization and check status
                API_STATUS=$(curl -s http://localhost:8889/semantic/status 2>/dev/null)
                if [ $? -eq 0 ] && [ -n "$API_STATUS" ]; then
                    AVAILABLE=$(echo "$API_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print('true' if data.get('available') else 'false')" 2>/dev/null || echo "false")
                    EMBEDDING_COUNT=$(echo "$API_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('embeddings_count', 0))" 2>/dev/null || echo "0")
                    
                    if [ "$AVAILABLE" = "true" ] && [ "$EMBEDDING_COUNT" -gt 0 ]; then
                        echo "  ✓ Semantic API ready with $EMBEDDING_COUNT embeddings"
                        API_READY=true
                        break
                    fi
                fi
                
                RETRY_COUNT=$((RETRY_COUNT + 1))
                if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                    echo "  → Waiting for API to load embeddings... (attempt $RETRY_COUNT/$MAX_RETRIES)"
                    sleep 3
                fi
            done
            
            if [ "$API_READY" = false ]; then
                echo "  ⚠ Warning: Semantic API started but embeddings not loaded after $MAX_RETRIES attempts"
                echo "  ⚠ Trying to restart API..."
                kill $SEMANTIC_PID 2>/dev/null
                sleep 2
                
                # Restart API
                python3 semantic_api.py &
                SEMANTIC_PID=$!
                sleep 4
                
                # Final check
                API_STATUS=$(curl -s http://localhost:8889/semantic/status 2>/dev/null)
                if [ $? -eq 0 ]; then
                    AVAILABLE=$(echo "$API_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print('true' if data.get('available') else 'false')" 2>/dev/null || echo "false")
                    EMBEDDING_COUNT=$(echo "$API_STATUS" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('embeddings_count', 0))" 2>/dev/null || echo "0")
                    
                    if [ "$AVAILABLE" = "true" ] && [ "$EMBEDDING_COUNT" -gt 0 ]; then
                        echo "  ✓ Semantic API ready after restart with $EMBEDDING_COUNT embeddings"
                    else
                        echo "  ✗ Semantic API still not available after restart"
                        echo "  ⚠ Please check the API logs for errors"
                    fi
                fi
            fi
        fi
    else
        echo "⚠ Warning: semantic_api.py not found, skipping semantic API"
        SEMANTIC_PID=""
    fi
else
    SEMANTIC_PID=""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $PROXY_PID 2>/dev/null
    if [ -n "$SEMANTIC_PID" ]; then
        kill $SEMANTIC_PID 2>/dev/null
    fi
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Start frontend server
python3 -m http.server 8000

# Cleanup if frontend server exits
cleanup

