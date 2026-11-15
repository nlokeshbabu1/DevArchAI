"""Loopback HTTP server to receive the CLI OAuth callback."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse


class CallbackResult(NamedTuple):
    code: str
    state: str


class LoopbackCallbackServer:
    """Minimal loopback listener for OAuth authorization codes (no secrets in logs)."""

    def __init__(self, path: str = "/callback") -> None:
        self.path = path
        self.port: int | None = None
        self.redirect_uri: str | None = None
        self._result: CallbackResult | None = None
        self._error: str | None = None
        self._done = threading.Event()
        self._http: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                return

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                if parsed.path != parent.path:
                    self.send_response(404)
                    self.end_headers()
                    return
                params = parse_qs(parsed.query)
                code_vals = params.get("code", [])
                state_vals = params.get("state", [])
                if not code_vals or not state_vals:
                    parent._error = "cancelled"
                    self.send_response(400)
                    self.end_headers()
                    parent._done.set()
                    return
                parent._result = CallbackResult(code=code_vals[0], state=state_vals[0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><p>Authentication complete. Return to the terminal.</p></body></html>"
                )
                parent._done.set()

        self._http = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = int(self._http.server_address[1])
        self.redirect_uri = f"http://127.0.0.1:{self.port}{self.path}"
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()

    def wait(self, timeout: float) -> CallbackResult:
        if not self._done.wait(timeout=timeout):
            self.stop()
            raise TimeoutError("Timed out waiting for browser authorization")
        self.stop()
        if self._error == "cancelled":
            raise RuntimeError("cancelled")
        if self._result is None:
            raise RuntimeError("No authorization result received")
        return self._result

    def stop(self) -> None:
        if self._http is not None:
            self._http.shutdown()
            self._http = None