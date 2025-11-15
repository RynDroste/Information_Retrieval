#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solr Proxy Server
Proxies requests to Solr to avoid CORS issues
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import json
import sys

SOLR_URL = 'http://localhost:8983'
PROXY_PORT = 8888

class SolrProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests and proxy to Solr"""
        try:
            # Parse the request path
            parsed_path = urlparse(self.path)
            query_string = parsed_path.query
            
            # Build Solr URL
            solr_path = parsed_path.path
            if solr_path.startswith('/solr/'):
                # Direct Solr path
                solr_full_url = f"{SOLR_URL}{solr_path}"
            else:
                # Default to RamenProject core
                solr_full_url = f"{SOLR_URL}/solr/RamenProject/select"
            
            if query_string:
                solr_full_url += f"?{query_string}"
            
            # Make request to Solr
            req = urllib.request.Request(solr_full_url)
            req.add_header('User-Agent', 'Solr-Proxy/1.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()
                status_code = response.getcode()
                
                # Send response with CORS headers
                self.send_response(status_code)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({
                'error': str(e),
                'code': e.code
            }).encode('utf-8')
            self.wfile.write(error_response)
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({
                'error': str(e),
                'type': type(e).__name__
            }).encode('utf-8')
            self.wfile.write(error_response)
            print(f"Error proxying request: {e}", file=sys.stderr)
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        # Only log errors
        if 'Error' in format % args:
            super().log_message(format, *args)

def main():
    server = HTTPServer(('localhost', PROXY_PORT), SolrProxyHandler)
    print(f"Solr Proxy Server running on http://localhost:{PROXY_PORT}")
    print(f"Proxying requests to {SOLR_URL}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down proxy server...")
        server.shutdown()

if __name__ == '__main__':
    main()

