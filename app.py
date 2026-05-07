from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException

MAX_TITLE_LENGTH = 120
MAX_CATEGORY_LENGTH = 40
MAX_CODE_LENGTH = 10_000
DEFAULT_MAX_CONTENT_LENGTH = 1_048_576

db = SQLAlchemy()


class Snippet(db.Model):
    """Represents a saved developer snippet in the database."""

    __tablename__ = "snippets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    code = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(MAX_CATEGORY_LENGTH), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def api_response(data: Any, message: str, status_code: int = 200):
    payload = {"success": True, "message": message, "data": data}
    return jsonify(payload), status_code


def api_error(
    message: str,
    status_code: int = 400,
    errors: dict[str, str] | None = None,
):
    payload: dict[str, Any] = {"success": False, "message": message, "data": None}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code


def _get_json_body() -> tuple[dict[str, Any] | None, tuple | None]:
    if not request.is_json:
        return None, api_error("Request body must be JSON.", 400)

    payload = request.get_json(silent=True)
    if payload is None:
        return None, api_error("Invalid JSON payload.", 400)

    if not isinstance(payload, dict):
        return None, api_error("JSON body must be an object.", 400)

    return payload, None


def _validate_snippet_payload(payload: dict[str, Any]) -> tuple[bool, dict[str, str]]:
    required_fields = ("title", "code", "category")
    errors: dict[str, str] = {}

    for field in required_fields:
        value = payload.get(field)
        if value is None:
            errors[field] = "Field is required."
            continue
        if not isinstance(value, str):
            errors[field] = "Must be a string."
            continue
        if not value.strip():
            errors[field] = "Must be a non-empty string."
            continue
        if field == "title" and len(value.strip()) > MAX_TITLE_LENGTH:
            errors[field] = f"Must be {MAX_TITLE_LENGTH} characters or fewer."
        if field == "category" and len(value.strip()) > MAX_CATEGORY_LENGTH:
            errors[field] = f"Must be {MAX_CATEGORY_LENGTH} characters or fewer."
        if field == "code" and len(value) > MAX_CODE_LENGTH:
            errors[field] = f"Must be {MAX_CODE_LENGTH} characters or fewer."

    return len(errors) == 0, errors


def _clean_text(value: str) -> str:
    return value.strip()


def _snippet_to_dict(snippet: Snippet) -> dict[str, Any]:
    # Keep response format unchanged by returning only existing fields.
    return {
        "id": snippet.id,
        "title": snippet.title,
        "code": snippet.code,
        "category": snippet.category,
    }


def _find_snippet(snippet_id: int) -> Snippet | None:
    return db.session.get(Snippet, snippet_id)


def _reset_store(app: Flask) -> None:
    """Reset the database for tests by recreating all tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()


def _build_database_uri(testing: bool) -> str:
    base_dir = Path(__file__).resolve().parent
    filename = "snippets_test.db" if testing else "snippets.db"
    return f"sqlite:///{(base_dir / filename).as_posix()}"


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["TESTING"] = testing
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_MAX_CONTENT_LENGTH))
    )

    database_uri = _build_database_uri(testing)
    if not testing:
        database_uri = os.getenv("DATABASE_URL", database_uri)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    # Create the SQLite database file and tables on startup if missing.
    with app.app_context():
        db.create_all()

    @app.get("/")
    def health_check():
        data = {"service": "Developer Snippet Vault", "status": "running"}
        return api_response(data, "Developer Snippet Vault Running")

    @app.post("/snippets")
    def create_snippet():
        payload, error_response = _get_json_body()
        if error_response:
            return error_response

        is_valid, errors = _validate_snippet_payload(payload)
        if not is_valid:
            return api_error("Validation failed.", 400, errors)

        snippet = Snippet(
            title=_clean_text(payload["title"]),
            code=_clean_text(payload["code"]),
            category=_clean_text(payload["category"]),
        )
        db.session.add(snippet)
        db.session.commit()

        return api_response(_snippet_to_dict(snippet), "Snippet created.", 201)

    @app.get("/snippets")
    def list_snippets():
        snippet_rows = Snippet.query.order_by(Snippet.id.asc()).all()
        data = {
            "snippets": [_snippet_to_dict(item) for item in snippet_rows],
            "count": len(snippet_rows),
        }
        return api_response(data, "Snippets retrieved.")

    @app.delete("/snippets/<int:snippet_id>")
    def delete_snippet(snippet_id: int):
        snippet = _find_snippet(snippet_id)
        if snippet is None:
            return api_error("Snippet not found.", 404)

        db.session.delete(snippet)
        db.session.commit()
        return api_response({"deleted": _snippet_to_dict(snippet)}, "Snippet deleted.")

    @app.errorhandler(404)
    def handle_not_found(_):
        return api_error("Route not found.", 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(_):
        return api_error("Method not allowed.", 405)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        if error.code == 413:
            return api_error("Request body too large.", 413)
        return api_error(error.description or "Request failed.", error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        app.logger.exception("Unhandled exception: %s", error)
        return api_error("Internal server error.", 500)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
