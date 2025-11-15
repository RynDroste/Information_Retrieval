#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Search API Server
Provides REST API for semantic search using LaBSE embeddings
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import sys
import os
from pathlib import Path

try:
    from semantic_search import SemanticSearch
    from labse_embedder import LaBSEEmbedder
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

SEMANTIC_PORT = 8889

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()
EMBEDDINGS_FILE = SCRIPT_DIR / 'data' / 'embeddings.json'

class SemanticAPIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        if not hasattr(self.__class__, '_semantic_search'):
            if SEMANTIC_AVAILABLE:
                try:
                    # Use absolute path to embeddings file
                    embeddings_path = str(EMBEDDINGS_FILE)
                    print(f"Initializing semantic search with embeddings: {embeddings_path}")
                    self.__class__._semantic_search = SemanticSearch(embeddings_file=embeddings_path)
                    if not self.__class__._semantic_search.is_available():
                        print(f"Warning: Semantic search initialized but not available")
                        print(f"  Embeddings file exists: {os.path.exists(embeddings_path)}")
                        print(f"  Embeddings count: {len(self.__class__._semantic_search.embeddings)}")
                        self.__class__._semantic_search = None
                    else:
                        print(f"✓ Semantic search initialized successfully")
                except Exception as e:
                    print(f"Warning: Failed to initialize semantic search: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    self.__class__._semantic_search = None
            else:
                self.__class__._semantic_search = None
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for semantic search"""
        try:
            if self.path != '/semantic/rerank':
                self.send_response(404)
                self.end_headers()
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            query = request_data.get('query', '')
            candidates = request_data.get('candidates', [])
            top_k = request_data.get('top_k', 10)
            keyword_weight = request_data.get('keyword_weight', 0.6)
            semantic_weight = request_data.get('semantic_weight', 0.4)
            
            if not self.__class__._semantic_search:
                # Return candidates as-is if semantic search not available
                response = {
                    'success': False,
                    'message': 'Semantic search not available',
                    'results': candidates[:top_k]
                }
            else:
                # Perform semantic reranking
                results = self.__class__._semantic_search.search(
                    query, candidates, top_k, keyword_weight, semantic_weight
                )
                response = {
                    'success': True,
                    'results': results
                }
            
            # Send response
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({
                'success': False,
                'error': str(e)
            }).encode('utf-8')
            self.wfile.write(error_response)
            print(f"Error in semantic API: {e}", file=sys.stderr)
    
    def do_GET(self):
        """Handle GET requests - check if semantic search is available"""
        if self.path == '/semantic/status':
            is_available = self.__class__._semantic_search is not None and \
                          self.__class__._semantic_search.is_available()
            response = {
                'available': is_available,
                'embeddings_count': len(self.__class__._semantic_search.embeddings) if self.__class__._semantic_search else 0
            }
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        if 'Error' in format % args:
            super().log_message(format, *args)

def main():
    if not SEMANTIC_AVAILABLE:
        print("Error: Semantic search modules not available")
        print("Please install: pip3 install sentence-transformers numpy torch")
        sys.exit(1)
    
    server = HTTPServer(('localhost', SEMANTIC_PORT), SemanticAPIHandler)
    print(f"Semantic Search API Server running on http://localhost:{SEMANTIC_PORT}")
    print("Endpoints:")
    print("  GET  /semantic/status - Check if semantic search is available")
    print("  POST /semantic/rerank - Rerank search results using semantic similarity")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down semantic API server...")
        server.shutdown()

if __name__ == '__main__':
    main()

