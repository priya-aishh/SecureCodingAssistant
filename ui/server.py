"""Local browser console for live attack probes and the full agent journey."""

import argparse
import codecs
import json
import os
import pty
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from dotenv import dotenv_values

from src.mock_wikipedia import wikipedia_article_url


ROOT = Path(__file__).resolve().parent.parent
HTML = (Path(__file__).with_name("index.html")).read_text(encoding="utf-8")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
PHASE = re.compile(r"\[(Understanding|Init|Design|Coding|Review|Commit|Attack lab)\]")
ARTIFACTS = {
    "task.md", "design.md", "design_review.md", "coding_summary.md",
    "coding_review.md", "coding_diff.patch", "coding_validation.json",
    "report.md", "report.json", "audit.jsonl",
}
RUNS: dict[str, "Run"] = {}
RUNS_LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(24)


class Run:
    def __init__(self, data: dict):
        self.id = secrets.token_hex(6)
        self.kind = data["kind"]
        self.root = Path(tempfile.mkdtemp(prefix=f"coding-ui-{self.id}-"))
        self.status = "starting"
        self.phase = "Setup"
        self.events: list[dict] = []
        self.seq = 0
        self.lock = threading.Lock()
        self.process_lock = threading.Lock()
        self.process: subprocess.Popen | None = None
        self.master: int | None = None
        self.exit_code: int | None = None
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.data = data
        self.tail = ""
        self.stop_requested = threading.Event()

    def emit(self, message: str) -> None:
        message = ANSI.sub("", message).replace("\r\n", "\n").replace("\r", "\n")
        with self.lock:
            self.seq += 1
            self.events.append({"seq": self.seq, "text": message})
            self.events = self.events[-5000:]
            phases = PHASE.findall(message)
            if phases:
                self.phase = phases[-1]
            self.tail = (self.tail + message)[-300:]
            if not self.stop_requested.is_set() and "Type LGTM to approve or describe what to change:" in self.tail:
                self.status = "awaiting_approval"
                self.tail = ""

    def command(self) -> list[str]:
        data = self.data
        article = data.get("article", "").strip()
        url = data.get("url", "").strip()
        if self.kind == "attack":
            page = self.root / "article.md"
            page.write_text(article, encoding="utf-8")
            return [sys.executable, "-m", "attack_lab.run", "--mode", "live",
                    "--custom-page", str(page), "--url", url,
                    "--question", data["question"].strip(), "--output", str(self.root / "report")]

        task = data["task"].strip()
        command = [sys.executable, "main.py", "--workspace", data["workspace"].strip(),
                   "--artifacts-dir", str(self.root / "artifacts"), "--prompt", task]
        if article:
            fixture = self.root / "pages"
            fixture.mkdir()
            (fixture / "article.md").write_text(article, encoding="utf-8")
            (fixture / "manifest.json").write_text(json.dumps({url: "article.md"}), encoding="utf-8")
            command += ["--mock-mode", "--mock-pages-dir", str(fixture)]
            command[command.index("--prompt") + 1] = task + f"\n\nConsult this background page when relevant: {url}"
        elif data.get("mock_mode", True):
            command.append("--mock-mode")
        return command

    def run(self) -> None:
        try:
            if self.stop_requested.is_set():
                return
            command = self.command()
            if self.stop_requested.is_set():
                return
            env = os.environ.copy()
            env.update({"PYTHONUNBUFFERED": "1", "NO_COLOR": "1", "TERM": "dumb"})
            if self.data.get("api_key"):
                env["GEMINI_API_KEY"] = self.data["api_key"]
            self.data.pop("api_key", None)
            with self.process_lock:
                if self.stop_requested.is_set():
                    return
                master, slave = pty.openpty()
                self.master = master
                try:
                    self.process = subprocess.Popen(
                        command, cwd=ROOT, env=env, stdin=slave, stdout=slave, stderr=slave,
                        start_new_session=True, close_fds=True,
                    )
                finally:
                    os.close(slave)
            with self.lock:
                stopped = self.stop_requested.is_set()
                if not stopped:
                    self.status = "running"
                    self.phase = "Agent" if self.kind == "attack" else "Understanding"
            if stopped:
                self.stop()
            else:
                self.emit(f"[UI] Started {self.kind} run. Output: {self.root}\n")
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            while True:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                self.emit(decoder.decode(chunk))
            tail = decoder.decode(b"", final=True)
            if tail:
                self.emit(tail)
            self.exit_code = self.process.wait()
            if not self.stop_requested.is_set():
                self.status = "completed" if self.exit_code == 0 else "failed"
            self.phase = "Report" if self.kind == "attack" else self.phase
            self.emit(f"\n[UI] Run {self.status} (exit {self.exit_code}).\n")
        except Exception as error:
            self.status = "stopped" if self.stop_requested.is_set() else "failed"
            self.emit(f"[UI] Run failed: {type(error).__name__}: {error}\n")
        finally:
            if self.master is not None:
                os.close(self.master)

    def stop(self) -> None:
        """Terminate the run and its child processes before allowing a new run."""
        with self.lock:
            self.stop_requested.set()
            self.status = "stopped"
        with self.process_lock:
            process = self.process
        if process is None or process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()

    def artifacts(self) -> list[str]:
        base = self.root / ("report" if self.kind == "attack" else "artifacts")
        names = [name for name in ARTIFACTS if (base / name).is_file()]
        if self.kind == "attack" and (base / "custom" / "audit.jsonl").is_file():
            names.append("custom/audit.jsonl")
        return sorted(names)

    def snapshot(self, since: int) -> dict:
        with self.lock:
            events = [event for event in self.events if event["seq"] > since]
            return {"id": self.id, "kind": self.kind, "status": self.status,
                    "phase": self.phase, "exit_code": self.exit_code,
                    "started_at": self.started_at, "events": events,
                    "artifacts": self.artifacts()}


def validate(data: dict) -> None:
    if data.get("kind") not in {"attack", "journey"}:
        raise ValueError("Choose an attack probe or full journey")
    article = data.get("article", "").strip()
    url = data.get("url", "").strip()
    if len(article.encode("utf-8")) > 64_000:
        raise ValueError("Article body must be 64 KB or smaller")
    if article or url:
        if not article or not wikipedia_article_url(url):
            raise ValueError("Provide both article text and an HTTPS en.wikipedia.org/wiki/ URL")
    if data["kind"] == "attack":
        if not article or not data.get("question", "").strip():
            raise ValueError("An attack probe needs article text and a question")
    else:
        workspace_input = data.get("workspace", "").strip()
        workspace = Path(workspace_input).expanduser().resolve() if workspace_input else None
        if workspace is None or not workspace.is_dir() or not data.get("task", "").strip():
            raise ValueError("The full journey needs an existing workspace and feature request")
        data["workspace"] = str(workspace)
    if len(data.get("api_key", "")) > 500:
        raise ValueError("API key is too long")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code: int, value: dict) -> None:
        self.send(code, json.dumps(value).encode("utf-8"))

    def authorized(self) -> bool:
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        return host in allowed and self.headers.get("X-UI-Token") == TOKEN

    def do_GET(self) -> None:
        path = urlsplit(self.path)
        host = self.headers.get("Host", "")
        if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            return self.send_json(403, {"error": "Local host only"})
        if path.path == "/":
            return self.send(200, HTML.replace("__TOKEN__", TOKEN).encode("utf-8"), "text/html; charset=utf-8")
        if not self.authorized():
            return self.send_json(403, {"error": "Unauthorized"})
        if path.path == "/api/meta":
            key_present = bool(os.getenv("GEMINI_API_KEY") or dotenv_values(ROOT / ".env").get("GEMINI_API_KEY"))
            return self.send_json(200, {"key_configured": key_present})
        parts = path.path.strip("/").split("/")
        if len(parts) >= 3 and parts[:2] == ["api", "runs"]:
            run = RUNS.get(parts[2])
            if not run:
                return self.send_json(404, {"error": "Run not found"})
            if len(parts) == 3:
                try:
                    since = int(parse_qs(path.query).get("since", ["0"])[0])
                except ValueError:
                    return self.send_json(400, {"error": "Invalid event cursor"})
                return self.send_json(200, run.snapshot(since))
            if len(parts) == 5 and parts[3] == "artifacts":
                name = unquote(parts[4])
                if name not in run.artifacts():
                    return self.send_json(404, {"error": "Artifact not found"})
                base = run.root / ("report" if run.kind == "attack" else "artifacts")
                file = (base / name).resolve()
                if not file.is_relative_to(base.resolve()):
                    return self.send_json(403, {"error": "Artifact outside run directory"})
                return self.send(200, file.read_bytes(), "text/plain; charset=utf-8")
        self.send_json(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self.authorized():
            return self.send_json(403, {"error": "Unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 128_000:
                raise ValueError("Request body is too large or empty")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            parts = urlsplit(self.path).path.strip("/").split("/")
            if parts == ["api", "reset"]:
                with RUNS_LOCK:
                    for run in RUNS.values():
                        run.stop()
                    RUNS.clear()
                return self.send_json(200, {"ok": True})
            if parts == ["api", "runs"]:
                validate(data)
                with RUNS_LOCK:
                    if any(run.status in {"starting", "running", "awaiting_approval"} for run in RUNS.values()):
                        return self.send_json(409, {"error": "A run is already active"})
                    run = Run(data)
                    RUNS[run.id] = run
                threading.Thread(target=run.run, daemon=True).start()
                return self.send_json(201, {"id": run.id})
            if len(parts) == 4 and parts[:2] == ["api", "runs"]:
                run = RUNS.get(parts[2])
                if not run:
                    return self.send_json(404, {"error": "Run not found"})
                if parts[3] == "input" and run.status == "awaiting_approval":
                    value = str(data.get("text", "")).replace("\r", " ").replace("\n", " ").strip()
                    if not value or len(value) > 2000:
                        raise ValueError("Feedback must contain 1 to 2000 characters")
                    os.write(run.master, (value + "\n").encode("utf-8"))
                    run.status = "running"
                    run.tail = ""
                    run.emit("[UI] Human design response submitted.\n")
                    return self.send_json(200, {"ok": True})
                if parts[3] == "stop" and run.status in {"starting", "running", "awaiting_approval"}:
                    run.stop()
                    return self.send_json(200, {"ok": True})
            return self.send_json(409, {"error": "Action unavailable for this run"})
        except (ValueError, OSError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Local live agent browser UI")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Agent UI: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
