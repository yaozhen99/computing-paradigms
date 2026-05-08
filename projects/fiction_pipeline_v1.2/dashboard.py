"""Fiction Pipeline v1.2 — Read-only Dashboard Server

Usage:  python dashboard.py
Open:   http://localhost:8420

Zero external dependencies. Ctrl+C to stop.
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 8420
HOST = "127.0.0.1"
PIPELINE_ROOT = Path(__file__).resolve().parent
WORKSPACE = PIPELINE_ROOT / "workspace"
DASHBOARD_DIR = PIPELINE_ROOT / "dashboard"


def safe_project_path(project: str, rel_path: str) -> Path | None:
    """Resolve a relative path inside a project directory, blocking traversal."""
    project_dir = (WORKSPACE / project).resolve()
    if not project_dir.is_dir():
        return None
    target = (project_dir / rel_path).resolve()
    if not str(target).startswith(str(project_dir)):
        return None
    return target


def read_json(path: Path) -> dict | list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_text(path: Path, tail: int = 0) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            if tail:
                lines = f.readlines()
                return "".join(lines[-tail:])
            return f.read()
    except OSError:
        return None


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_file(DASHBOARD_DIR / "index.html", "text/html")
        elif path == "/style.css":
            self._serve_file(DASHBOARD_DIR / "style.css", "text/css")
        elif path == "/app.js":
            self._serve_file(DASHBOARD_DIR / "app.js", "application/javascript")
        elif path == "/api/projects":
            self._api_projects()
        elif path.startswith("/api/project/"):
            self._api_project(path, qs)
        else:
            self._respond(404, {"error": "not found"})

    def _serve_file(self, filepath: Path, content_type: str):
        data = read_text(filepath)
        if data is None:
            self._respond(404, {"error": "file not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.end_headers()
        self.wfile.write(data.encode("utf-8"))

    def _api_projects(self):
        projects = []
        if WORKSPACE.is_dir():
            for d in sorted(WORKSPACE.iterdir()):
                if d.is_dir() and (d / "_system" / "system_state.json").is_file():
                    projects.append(d.name)
        self._respond(200, {"projects": projects})

    def _api_project(self, path: str, qs: dict):
        parts = path.strip("/").split("/")
        # /api/project/<name>/<action>
        if len(parts) < 4:
            self._respond(400, {"error": "bad request"})
            return
        name = parts[2]
        action = parts[3]
        project_dir = WORKSPACE / name

        if not project_dir.is_dir():
            self._respond(404, {"error": "project not found"})
            return

        if action == "state":
            data = read_json(project_dir / "_system" / "system_state.json")
            self._respond(200 if data else 404, data or {"error": "state not found"})

        elif action == "manifest":
            data = read_json(project_dir / "_system" / "stage_manifest.json")
            self._respond(200 if data else 404, data or {"error": "manifest not found"})

        elif action == "locks":
            pipes_dir = project_dir / "_pipes"
            locks = {}
            if pipes_dir.is_dir():
                for f in sorted(pipes_dir.glob("lock_*.json")):
                    data = read_json(f)
                    if data:
                        locks[f.stem] = data
            self._respond(200, {"locks": locks})

        elif action == "log":
            log_path = project_dir / "_logs" / "pipeline_execution_log.md"
            text = read_text(log_path, tail=200)
            self._respond(200, {"log": text or ""})

        elif action == "file":
            rel = qs.get("path", [""])[0]
            if not rel:
                self._respond(400, {"error": "missing path param"})
                return
            target = safe_project_path(name, rel)
            if target is None or not target.is_file():
                self._respond(404, {"error": "file not found or path denied"})
                return
            text = read_text(target, tail=500)
            self._respond(200, {
                "path": rel,
                "content": text or "",
                "ext": target.suffix.lstrip("."),
            })

        else:
            self._respond(404, {"error": f"unknown action: {action}"})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # silence default stderr logging


def main():
    server = HTTPServer((HOST, PORT), DashboardHandler)
    print(f"Fiction Pipeline Dashboard -> http://{HOST}:{PORT}")
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
