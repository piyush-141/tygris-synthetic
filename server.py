"""
server.py
Lightweight HTTP Server for the Pench Satellite Re-ID Dashboard.
Serves HTML, CSS, JavaScript, JSON bundles, and local dataset photos.
"""

import http.server
import socketserver
import os
import sys

PORT = 8000
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
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print("=" * 70)
        print(f"PENCH SATELLITE RE-ID MONITORING DASHBOARD IS RUNNING")
        print(f"URL: http://localhost:{PORT}")
        print("=" * 70)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down.")
            httpd.server_close()

if __name__ == "__main__":
    run_server()
