import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workers.worker import run_once

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            stats = run_once()
            body = json.dumps({"ok": True, **stats, "note": "Core app remains operational if Redis or this worker is unavailable."}).encode()
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
            self.send_response(500)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers(); self.wfile.write(body)
