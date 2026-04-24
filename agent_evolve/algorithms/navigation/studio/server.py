"""Local HTTP server for the studio — stdlib only, zero new dependencies.

Routes:
  GET  /                      static/index.html
  GET  /static/*              static asset (mime-typed)
  GET  /api/schema            palette + type catalogue (schema.build_schema)
  GET  /api/specs             list of shipped reference Activities
  GET  /api/specs/<name>      one shipped Activity JSON
  POST /api/validate          body: Activity JSON; returns {ok, error?}
  POST /api/export            body: {activity, class_name, template_name}
                              returns generated .py text
"""

from __future__ import annotations

import json
import logging
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from ..activity.registry import default_registry
from ..activity.spec import Activity
from ..activity.validator import ActivityValidationError, validate
from .codegen import CodegenError, generate_template_py
from .schema import build_schema

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"
_SPECS_DIR = Path(__file__).parent.parent / "activity" / "specs"


class _Handler(BaseHTTPRequestHandler):
    # Keep the default stderr access log quiet in normal use.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.debug("%s - %s", self.address_string(), format % args)

    # ── request dispatch ────────────────────────────────────────────

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._serve_file(_STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_file(_STATIC_DIR / rel, None)
            return
        if path == "/api/schema":
            self._send_json(build_schema())
            return
        if path == "/api/specs":
            self._send_json(self._list_specs())
            return
        if path.startswith("/api/specs/"):
            name = unquote(path[len("/api/specs/"):])
            self._serve_spec(name)
            return
        self._send_error(HTTPStatus.NOT_FOUND, f"no route for GET {path!r}")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_body()
        if path == "/api/validate":
            self._handle_validate(body)
            return
        if path == "/api/export":
            self._handle_export(body)
            return
        self._send_error(HTTPStatus.NOT_FOUND, f"no route for POST {path!r}")

    # ── handlers ────────────────────────────────────────────────────

    def _handle_validate(self, body: dict[str, Any]) -> None:
        spec = body.get("activity") or body
        try:
            activity = Activity.from_json(spec)
            validate(activity, default_registry())
        except ActivityValidationError as e:
            self._send_json({"ok": False, "error": str(e)})
            return
        except Exception as e:
            self._send_json({"ok": False, "error": f"malformed spec: {e}"})
            return
        self._send_json({"ok": True})

    def _handle_export(self, body: dict[str, Any]) -> None:
        try:
            spec = body["activity"]
            class_name = body.get("class_name") or "StudioTemplate"
            template_name = body.get("template_name") or "studio_template"
            src = generate_template_py(
                spec, class_name=class_name, template_name=template_name,
            )
        except (CodegenError, KeyError, TypeError) as e:
            self._send_error(HTTPStatus.BAD_REQUEST, str(e))
            return
        self._send(
            HTTPStatus.OK,
            "text/x-python; charset=utf-8",
            src.encode("utf-8"),
            extra_headers={
                "Content-Disposition": f'attachment; filename="{template_name}.py"',
            },
        )

    def _serve_spec(self, name: str) -> None:
        # strict filename: alphanumerics + underscore + dash + dot
        if not name or ".." in name or "/" in name or "\\" in name:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid spec name")
            return
        if not name.endswith(".json"):
            name = name + ".json"
        path = _SPECS_DIR / name
        if not path.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, f"spec {name!r} not found")
            return
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"spec unreadable: {e}")
            return
        self._send_json(data)

    def _list_specs(self) -> dict[str, Any]:
        specs: list[dict[str, Any]] = []
        if _SPECS_DIR.is_dir():
            for path in sorted(_SPECS_DIR.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                    specs.append({
                        "name": path.stem,
                        "file": path.name,
                        "description": data.get("description", ""),
                    })
                except Exception:
                    continue
        return {"specs": specs}

    # ── IO helpers ──────────────────────────────────────────────────

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _serve_file(self, path: Path, content_type: str | None) -> None:
        try:
            real = path.resolve()
            real.relative_to(_STATIC_DIR.resolve())
        except (ValueError, OSError):
            self._send_error(HTTPStatus.FORBIDDEN, "path escape")
            return
        if not real.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, f"not found: {path.name}")
            return
        ctype = content_type or mimetypes.guess_type(str(real))[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, ctype, real.read_bytes())

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._send(status, "application/json", body)

    def _send_error(self, status: HTTPStatus, msg: str) -> None:
        body = json.dumps({"error": msg}).encode("utf-8")
        self._send(status, "application/json", body)

    def _send(
        self,
        status: HTTPStatus,
        content_type: str,
        body: bytes,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)


def launch(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start the studio HTTP server (blocking).

    Ctrl-C stops it cleanly.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer((host, port), _Handler)
    url = f"http://{host}:{port}/"
    print(f"[studio] serving at {url}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[studio] shutting down")
    finally:
        server.server_close()
