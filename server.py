"""
server.py
Lightweight HTTP Server for the Pench Satellite Re-ID Dashboard.
Serves HTML, CSS, JavaScript, JSON bundles, and local dataset photos.
"""

import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), CORSHTTPRequestHandler) as httpd:
            print("=" * 70, flush=True)
            print(f"PENCH SATELLITE RE-ID MONITORING DASHBOARD IS RUNNING", flush=True)
            print(f"URL: http://localhost:{PORT}", flush=True)
            print("=" * 70, flush=True)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.", flush=True)
    except Exception as e:
        print(f"Server error: {e}", flush=True)

if __name__ == "__main__":
    run_server()
