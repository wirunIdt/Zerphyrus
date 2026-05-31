import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR / "project"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.chdir(BASE_DIR)

_app = None


def _load_app():
    global _app
    if _app is None:
        from app import app as flask_app  # noqa: E402

        _app = flask_app
    return _app


def handler(environ, start_response):
    if environ.get("PATH_INFO") in {"/healthz", "/health"}:
        body = b'{"status":"ok","app":"zerphyrus","entrypoint":"vercel"}'
        start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body]
    return _load_app()(environ, start_response)


app = handler
