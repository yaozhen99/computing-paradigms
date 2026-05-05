"""
Hermes Bridge - 双向通信桥
- Atlas/Claude Code → Hermes: POST /task 派任务
- Hermes → Claude Code: POST /message 发消息, GET /inbox 收件箱

端口: 8891 (team-1)
"""
import json
import os
import re
import subprocess
import threading
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

BRIDGE_DIR = Path(r"C:\tower-of-babel\hermes-bridge")
WSL_BRIDGE_DIR = "/mnt/c/tower-of-babel/hermes-bridge"
TASKS_DIR = BRIDGE_DIR / "tasks"
RESULTS_DIR = BRIDGE_DIR / "results"
INBOX_DIR = BRIDGE_DIR / "inbox"

# 安全：Bearer Token认证，从环境变量读取
BRIDGE_API_TOKEN = os.environ.get("BRIDGE_API_TOKEN", "")

TASKS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
INBOX_DIR.mkdir(parents=True, exist_ok=True)

HERMES_CMD_TEMPLATE = r'wsl -d Ubuntu -- bash -c "source ~/hermes-venv/bin/activate 2>/dev/null; hermes chat -q \"{query}\" -Q"'
HERMES_TIMEOUT = 300  # 测试任务需要更长时间


def run_shell(task_id: str, command: str):
    """Directly execute a shell command, save result"""
    result_file = RESULTS_DIR / f"{task_id}.json"
    try:
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "running",
            "started": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")

        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=300
        )
        raw_output = (proc.stdout or "") + (proc.stderr or "")
        debug_info = f"stdout_len={len(proc.stdout or '')}, stderr_len={len(proc.stderr or '')}, rc={proc.returncode}"
        # Remove ANSI escape sequences
        clean = re.sub(r'\x1b\[[0-9;]*m', '', raw_output)
        output = clean.strip()

        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "done" if proc.returncode == 0 else "error",
            "output": output,
            "debug": debug_info,
            "error": "" if proc.returncode == 0 else output,
            "returncode": proc.returncode,
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")

    except subprocess.TimeoutExpired:
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "timeout",
            "error": "Shell command timed out after 300s",
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "error",
            "error": str(e),
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False))


def run_hermes(task_id: str, query: str):
    """Run hermes chat with query, save result"""
    result_file = RESULTS_DIR / f"{task_id}.json"
    try:
        # Update status to running
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "running",
            "started": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")

        # Build command - use double quotes for the query
        cmd = HERMES_CMD_TEMPLATE.format(query=query.replace('"', '\\"'))

        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=HERMES_TIMEOUT
        )
        # Combine stdout and stderr, then clean up
        raw_output = (proc.stdout or "") + (proc.stderr or "")
        # Debug: log raw output length
        debug_info = f"stdout_len={len(proc.stdout or '')}, stderr_len={len(proc.stderr or '')}, rc={proc.returncode}"
        # Remove ANSI escape sequences
        clean = re.sub(r'\x1b\[[0-9;]*m', '', raw_output)
        # Remove session_id lines and banner noise
        lines = []
        in_banner = False
        for line in clean.split('\n'):
            stripped = line.strip()
            # Skip empty lines
            if not stripped:
                continue
            # Skip session_id line
            if stripped.startswith('session_id:'):
                continue
            # Skip banner block (starts with ── Hermes Agent)
            if 'Hermes Agent v' in stripped or '─── Hermes Agent' in stripped:
                in_banner = True
                continue
            if in_banner:
                if stripped.startswith('Query:') or stripped.startswith('─'):
                    in_banner = False
                    continue
                continue
            # Skip resume/session/duration/messages lines
            if stripped.startswith('Resume this session') or stripped.startswith('Session:') or stripped.startswith('Duration:') or stripped.startswith('Messages:'):
                continue
            # Skip "Initializing agent..."
            if stripped == 'Initializing agent...':
                continue
            # Skip Hermes separator lines (─ and ⚕)
            if re.match(r'^[─═\-]+$', stripped):
                continue
            if stripped.startswith('─  ⚕ Hermes'):
                continue
            if stripped.startswith('────────────────────────────────────────────────'):
                continue
            lines.append(stripped)
        output = '\n'.join(lines).strip()

        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "done" if proc.returncode == 0 else "error",
            "output": output,
            "debug": debug_info,
            "error": "" if proc.returncode == 0 else output,
            "returncode": proc.returncode,
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")

    except subprocess.TimeoutExpired:
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "timeout",
            "error": f"Hermes timed out after {HERMES_TIMEOUT}s",
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        result_file.write_text(json.dumps({
            "task_id": task_id,
            "status": "error",
            "error": str(e),
            "completed": datetime.now().isoformat(),
        }, ensure_ascii=False))


class BridgeHandler(BaseHTTPRequestHandler):
    def _check_auth(self):
        """验证Bearer Token，未配置token时跳过认证（向后兼容）"""
        if not BRIDGE_API_TOKEN:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:] == BRIDGE_API_TOKEN:
            return True
        return False

    def _send_unauthorized(self):
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "unauthorized", "hint": "需要 Authorization: Bearer <token>"}).encode())

    def do_POST(self):
        if not self._check_auth():
            self._send_unauthorized()
            return
        if self.path == "/task":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                query = data.get("query", "")
                task_type = data.get("type", "hermes")  # "hermes" or "shell"
                source = data.get("from", "unknown")
                task_id = data.get("task_id", str(uuid.uuid4())[:8])

                # 拒绝空query
                if not query or not query.strip():
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "error": "query cannot be empty",
                        "task_id": task_id,
                    }).encode())
                    return

                # Save task
                (TASKS_DIR / f"{task_id}.json").write_text(json.dumps({
                    "task_id": task_id,
                    "query": query,
                    "type": task_type,
                    "from": source,
                    "created": datetime.now().isoformat(),
                }, ensure_ascii=False), encoding="utf-8")

                # Run in background thread
                if task_type == "shell":
                    t = threading.Thread(target=run_shell, args=(task_id, query), daemon=True)
                else:
                    t = threading.Thread(target=run_hermes, args=(task_id, query), daemon=True)
                t.start()

                self.send_response(202)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "task_id": task_id,
                    "status": "running",
                }).encode())

            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path == "/message":
            # Hermes → Claude Code: push message to inbox
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                msg_id = data.get("id", str(uuid.uuid4())[:8])
                msg = {
                    "id": msg_id,
                    "from": data.get("from", "hermes"),
                    "subject": data.get("subject", ""),
                    "body": data.get("body", ""),
                    "created": datetime.now().isoformat(),
                    "read": False,
                }
                (INBOX_DIR / f"{msg_id}.json").write_text(
                    json.dumps(msg, ensure_ascii=False), encoding="utf-8"
                )
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"id": msg_id, "status": "delivered"}).encode())
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        if not self._check_auth():
            self._send_unauthorized()
            return
        if self.path.startswith("/inbox/"):
            msg_id = self.path.split("/")[-1]
            msg_file = INBOX_DIR / f"{msg_id}.json"
            if msg_file.exists():
                msg_file.unlink()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"id": msg_id, "status": "deleted"}).encode())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if not self._check_auth():
            self._send_unauthorized()
            return
        if self.path == "/result":
            # List all results
            results = []
            for f in RESULTS_DIR.glob("*.json"):
                try:
                    results.append(json.loads(f.read_text(encoding="utf-8")))
                except:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode())

        elif self.path.startswith("/result/"):
            task_id = self.path.split("/")[-1]
            result_file = RESULTS_DIR / f"{task_id}.json"
            if result_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(result_file.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()
        elif self.path == "/inbox":
            # List inbox messages
            messages = []
            for f in sorted(INBOX_DIR.glob("*.json")):
                try:
                    messages.append(json.loads(f.read_text(encoding="utf-8")))
                except:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(messages, ensure_ascii=False).encode())

        elif self.path.startswith("/inbox/"):
            msg_id = self.path.split("/")[-1]
            msg_file = INBOX_DIR / f"{msg_id}.json"
            if msg_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(msg_file.read_bytes())
            else:
                self.send_response(404)
                self.end_headers()

        elif self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "bridge": "hermes-bridge",
                "status": "running",
                "tasks": len(list(TASKS_DIR.glob("*.json"))),
                "results": len(list(RESULTS_DIR.glob("*.json"))),
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # 写日志到文件而不是静默
        log_file = BRIDGE_DIR / "bridge.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {format % args}\n")
        except:
            pass


if __name__ == "__main__":
    port = 8891
    # 写PID文件，方便管理
    pid_file = BRIDGE_DIR / "bridge.pid"
    pid_file.write_text(str(os.getpid()))
    server = HTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"Hermes Bridge running at http://localhost:{port} (PID={os.getpid()})")
    print(f"  POST /task      - submit task to Hermes")
    print(f"  POST /message   - push message to Claude Code inbox")
    print(f"  GET  /result/<id> - get task result")
    print(f"  GET  /result    - list all results")
    print(f"  GET  /inbox     - list inbox messages")
    print(f"  GET  /inbox/<id> - read single message")
    print(f"  DELETE /inbox/<id> - delete message")
    print(f"  GET  /status    - bridge status")
    try:
        server.serve_forever()
    finally:
        pid_file.unlink(missing_ok=True)
