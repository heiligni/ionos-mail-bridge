"""Small token-protected API bound to the local machine."""

from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .mail import Config, create_draft, list_folders, send_message


def serve(config: Config, token: str, port: int = 8765) -> None:
    if not token:
        raise ValueError("Set IONOS_API_TOKEN before starting the API")

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status: int, payload: dict | list) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied, f"Bearer {token}"):
                self._reply(401, {"error": "Unauthorized"})
                return False
            return True

        def do_GET(self) -> None:
            if self.path == "/health":
                self._reply(200, {"status": "ok"})
                return
            if not self._authorized():
                return
            if self.path == "/v1/folders":
                try:
                    self._reply(200, list_folders(config))
                except Exception as exc:
                    self._reply(502, {"error": str(exc)})
            else:
                self._reply(404, {"error": "Not found"})

        def do_POST(self) -> None:
            if not self._authorized():
                return
            if self.path not in ("/v1/drafts", "/v1/messages"):
                self._reply(404, {"error": "Not found"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 1_048_576:
                    self._reply(413, {"error": "JSON body must be between 1 byte and 1 MiB"})
                    return
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("JSON body must be an object")
                allowed = {"to", "cc", "bcc", "subject", "body"}
                if set(payload) - allowed:
                    raise ValueError("Unknown fields: " + ", ".join(sorted(set(payload) - allowed)))
                arguments = {
                    "to": payload["to"], "subject": payload["subject"], "body": payload["body"],
                    "cc": payload.get("cc"), "bcc": payload.get("bcc"),
                }
                if self.path == "/v1/drafts":
                    self._reply(201, create_draft(config, **arguments))
                else:
                    self._reply(200, send_message(config, **arguments))
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                self._reply(400, {"error": str(exc)})
            except Exception as exc:
                self._reply(502, {"error": str(exc)})

        def log_message(self, format: str, *args: object) -> None:
            # Never write request bodies or bearer credentials to logs.
            print("mail-api:", format % args)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    try:
        print(f"Listening on http://127.0.0.1:{port}")
        server.serve_forever()
    finally:
        server.server_close()
