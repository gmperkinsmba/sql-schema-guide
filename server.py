"""Loopback server for the SQL Schema Guide browser and native app."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import os
import secrets
import socketserver
import sqlite3
import tempfile

from voodoosql import Catalog, FIXTURE, METADATA_DB, QueryPack, RUNTIME, ROOT, RECIPES, save_catalog, seed

HOST = "127.0.0.1"
PORT = 8332
PREFERENCES = RUNTIME / "preferences.json"
DEFAULT_PREFERENCES = {"reduceMotion": False}
MAX_BODY = 16_000

def _read_preferences():
    try:
        if PREFERENCES.stat().st_size > 1024:
            return dict(DEFAULT_PREFERENCES)
        value = json.loads(PREFERENCES.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != set(DEFAULT_PREFERENCES):
            return dict(DEFAULT_PREFERENCES)
        if type(value["reduceMotion"]) is not bool:
            return dict(DEFAULT_PREFERENCES)
        return value
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_PREFERENCES)


def _write_preferences(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT_PREFERENCES) or type(value.get("reduceMotion")) is not bool:
        raise ValueError("Settings accept only the reduceMotion boolean")
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(RUNTIME, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".preferences-", dir=RUNTIME)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, PREFERENCES)
        os.chmod(PREFERENCES, 0o600)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return value


def make_server(port: int = 0) -> ThreadingHTTPServer:
    """Bind a fresh loopback listener. The caller owns its thread and shutdown."""
    seed()
    pack = QueryPack(FIXTURE)

    class LocalServer(ThreadingHTTPServer):
        daemon_threads = True

        def server_bind(self):
            socketserver.TCPServer.server_bind(self)
            self.server_name = HOST
            self.server_port = self.socket.getsockname()[1]

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, _format, *_args):
            return

        def _valid_host(self):
            authority = self.headers.get("Host", "")
            port_text = str(self.server.server_port)
            return authority in (f"127.0.0.1:{port_text}", f"localhost:{port_text}")

        def _valid_origin(self):
            port_text = str(self.server.server_port)
            return self.headers.get("Origin") in (
                f"http://127.0.0.1:{port_text}",
                f"http://localhost:{port_text}",
            )

        def _send(self, status, value, kind="application/json; charset=utf-8", extra=()):
            data = value if isinstance(value, bytes) else value.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
            for key, header_value in extra:
                self.send_header(key, header_value)
            self.end_headers()
            self.wfile.write(data)

        def _json(self, value, status=200):
            return self._send(status, json.dumps(value, ensure_ascii=False, separators=(",", ":")))

        def do_GET(self):
            if not self._valid_host():
                return self._json({"error": "Invalid host"}, 403)
            route = urlparse(self.path).path
            if route == "/":
                page = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
                return self._send(200, page.replace("__TOKEN__", self.server.request_token), "text/html; charset=utf-8")
            assets = {
                "/app.css": ("static/app.css", "text/css; charset=utf-8"),
                "/app-extra.css": ("static/app-extra.css", "text/css; charset=utf-8"),
                "/desktop.css": ("static/desktop.css", "text/css; charset=utf-8"),
                "/app.js": ("static/app.js", "text/javascript; charset=utf-8"),
                "/eval-extra.js": ("static/eval-extra.js", "text/javascript; charset=utf-8"),
            }
            if route in assets:
                path, kind = assets[route]
                return self._send(200, (ROOT / path).read_bytes(), kind)
            if route == "/api/catalog":
                snapshot = Catalog.from_sqlite(FIXTURE)
                save_catalog(snapshot, METADATA_DB)
                return self._json(snapshot.to_dict())
            if route == "/api/graph":
                snapshot = Catalog.from_sqlite(FIXTURE)
                save_catalog(snapshot, METADATA_DB)
                return self._json(snapshot.to_graph())
            if route == "/api/recipes":
                return self._json({"recipes": RECIPES, "fingerprint": pack.fingerprint})
            if route == "/api/settings":
                return self._json({"preferences": _read_preferences(), "saved": PREFERENCES.is_file()})
            return self._json({"error": "Not found"}, 404)

        def do_POST(self):
            if not self._valid_host() or not self._valid_origin():
                return self._json({"error": "Invalid request origin"}, 403)
            if not secrets.compare_digest(self.headers.get("X-Request-Token", ""), self.server.request_token):
                return self._json({"error": "Request token required"}, 403)
            try:
                size = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                size = -1
            if size < 0 or size > MAX_BODY:
                return self._json({"error": "Payload size must be under 16 KB"}, 413)
            try:
                body = json.loads(self.rfile.read(size))
            except (ValueError, OSError):
                return self._json({"error": "Invalid JSON"}, 400)
            if not isinstance(body, dict):
                return self._json({"error": "JSON object required"}, 400)
            route = urlparse(self.path).path
            try:
                if route == "/api/settings":
                    return self._json({"preferences": _write_preferences(body), "saved": True})
                if route == "/api/retrieve":
                    question = body.get("question")
                    if not isinstance(question, str) or len(question) > 1000:
                        return self._json({"error": "Question must be text under 1,000 characters"}, 400)
                    return self._json(pack.retrieve(question))
                if route == "/api/execute":
                    return self._json(pack.execute(body.get("recipe_id"), body.get("params")))
            except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                return self._json({"error": str(exc)}, 400)
            return self._json({"error": "Not found"}, 404)

    server = LocalServer((HOST, port), Handler)
    server.request_token = secrets.token_urlsafe(32)
    return server


def serve(port: int = PORT):
    server = make_server(port=port)
    try:
        print(f"SQL Schema Guide listening at http://{HOST}:{server.server_port}", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
