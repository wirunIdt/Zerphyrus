import os
import sys
from pathlib import Path

from flask import Flask, Response, jsonify, request
from werkzeug.wrappers import Response as WerkzeugResponse


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR / "project"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.chdir(BASE_DIR)

app = Flask(__name__)
_main_app = None


def load_main_app():
    global _main_app
    if _main_app is None:
        from app import app as flask_app

        _main_app = flask_app
    return _main_app


@app.get("/healthz")
@app.get("/health")
def healthcheck():
    return jsonify(status="ok", app="zerphyrus", entrypoint="vercel")


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def proxy_to_main_app(path):
    try:
        main_app = load_main_app()
        return WerkzeugResponse.from_app(main_app.wsgi_app, request.environ)
    except Exception as exc:
        body = {
            "status": "error",
            "app": "zerphyrus",
            "error": type(exc).__name__,
            "message": str(exc),
        }
        return Response(jsonify(body).get_data(), status=500, content_type="application/json")
