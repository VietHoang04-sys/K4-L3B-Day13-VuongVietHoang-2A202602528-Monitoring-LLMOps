from __future__ import annotations

import argparse
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.dashboard import DEFAULT_CONFIG_PATH, DEFAULT_LOG_PATH, render_dashboard


class DashboardHandler(BaseHTTPRequestHandler):
    log_path = DEFAULT_LOG_PATH
    config_path = DEFAULT_CONFIG_PATH

    def do_GET(self) -> None:
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        try:
            content = render_dashboard(self.log_path, self.config_path).encode("utf-8")
        except FileNotFoundError as exc:
            self.send_error(503, f"Dashboard source not ready: {exc.filename}")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        print(f"dashboard: {format % args}")


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Serve the six-panel dashboard from structured JSONL logs."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    DashboardHandler.log_path = args.logs
    DashboardHandler.config_path = args.config

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"Dashboard listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
