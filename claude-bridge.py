#!/usr/bin/env python3
"""Thin HTTP bridge: Docker ai-service → claude CLI on the Mac host.

Usage: python3 claude-bridge.py   (or: make ai-bridge)

POST /  body: {"prompt": "..."}
        response: {"content": "..."}
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys


PORT = 9999


class BridgeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        prompt = body.get("prompt", "")

        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            resp = json.dumps({"error": result.stderr.strip()}).encode()
            self.send_response(500)
        else:
            resp = json.dumps({"content": result.stdout.strip()}).encode()
            self.send_response(200)

        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, fmt, *args):
        # Print prompt preview so you can see what's being called
        print(f"[bridge] {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), BridgeHandler)
    print(f"Claude CLI bridge listening on :{PORT}")
    print("Make sure you are logged in: claude auth login")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
