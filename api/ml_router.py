import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "data" / "generated" / "master" / "fixed_data.bundle.json"


def load_bundle():
    try:
        return json.loads(BUNDLE.read_text(encoding="utf-8"))
    except Exception:
        return {"mode": "empty_safe_mode", "availability": {"excel_baseline": False, "historical_data": False, "live_project_data": False}}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = load_bundle()
        av = data.get("availability", {})
        if not av.get("excel_baseline"):
            mode, route = "empty_safe_mode", "no_prediction"
        elif av.get("historical_data") or av.get("live_project_data"):
            mode, route = "hybrid_predictive", "ml_enriched_with_corporate_baseline"
        else:
            mode, route = "baseline_only", "deterministic_corporate_rules"
        body = json.dumps({
            "mode": mode,
            "route": route,
            "principle": "Historical and live data enrich predictions but are never required for app availability.",
            "availability": av,
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
