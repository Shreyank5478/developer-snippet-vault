from __future__ import annotations

import os
import hashlib
import secrets
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, Text
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException

MAX_TITLE_LENGTH = 120
MAX_CATEGORY_LENGTH = 40
MAX_CODE_LENGTH = 10_000
MAX_NAME_LENGTH = 120
DEFAULT_MAX_CONTENT_LENGTH = 1_048_576

DEFAULT_DATABASE_PATH = "data/snippets.db"
DEFAULT_CORS_ORIGINS = "*"
_engines: dict[str, Engine] = {}
metadata = MetaData()
users_table = Table(
	"users",
	metadata,
	Column("id", Integer, primary_key=True),
	Column("name", String(120), nullable=False),
	Column("api_key_hash", String(64), nullable=False, unique=True),
)
snippets_table = Table(
	"snippets",
	metadata,
	Column("id", Integer, primary_key=True),
	Column("title", String(120), nullable=False),
	Column("code", Text, nullable=False),
	Column("category", String(40), nullable=False),
	Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
)


def _database_url() -> str:
	database_url = os.getenv("DATABASE_URL")
	if database_url:
		if database_url.startswith("postgres://"):
			return "postgresql+psycopg://" + database_url[len("postgres://"):]
		if database_url.startswith("postgresql://"):
			return "postgresql+psycopg://" + database_url[len("postgresql://"):]
		return database_url

	database_path = Path(os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH))
	database_path.parent.mkdir(parents=True, exist_ok=True)
	return f"sqlite:///{database_path.resolve()}"


def _get_engine() -> Engine:
	database_url = _database_url()
	if database_url not in _engines:
		connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
		_engines[database_url] = create_engine(
			database_url,
			connect_args=connect_args,
			pool_pre_ping=True,
		)
	return _engines[database_url]


def _get_connection():
	return _get_engine().connect()


def _initialize_database() -> None:
	engine = _get_engine()
	with engine.begin() as connection:
		if engine.dialect.name == "sqlite":
			connection.execute(text("PRAGMA foreign_keys = ON"))
		metadata.create_all(connection)
	columns = {column["name"] for column in inspect(engine).get_columns("snippets")}
	if "user_id" not in columns:
		with engine.begin() as connection:
			connection.execute(text(
				"ALTER TABLE snippets ADD COLUMN user_id INTEGER REFERENCES users(id)"
			))
	with engine.begin() as connection:
		connection.execute(text("DELETE FROM snippets WHERE user_id IS NULL"))


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


def _hash_api_key(api_key: str) -> str:
	return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _authenticated_user_id() -> int | None:
	header = request.headers.get("Authorization", "")
	if header.startswith("Bearer "):
		api_key = header[7:].strip()
	else:
		api_key = request.headers.get("X-API-Key", "").strip()
	if not api_key:
		return None

	with _get_engine().connect() as connection:
		row = connection.execute(
			text("SELECT id FROM users WHERE api_key_hash = :api_key_hash"),
			{"api_key_hash": _hash_api_key(api_key)},
		).mappings().first()
	return int(row["id"]) if row else None


def require_api_key(view):
	@wraps(view)
	def wrapped(*args, **kwargs):
		user_id = _authenticated_user_id()
		if user_id is None:
			return api_error("A valid API key is required.", 401)
		g.user_id = user_id
		return view(*args, **kwargs)

	return wrapped


def _find_snippet(snippet_id: int, user_id: int) -> dict[str, Any] | None:
	with _get_engine().connect() as connection:
		row = connection.execute(
			text(
				"SELECT id, title, code, category FROM snippets "
				"WHERE id = :snippet_id AND user_id = :user_id"
			),
			{"snippet_id": snippet_id, "user_id": user_id},
		).mappings().first()
	return dict(row) if row else None


def _reset_store() -> None:
	_initialize_database()
	with _get_engine().begin() as connection:
		connection.execute(text("DELETE FROM snippets"))
		connection.execute(text("DELETE FROM users"))


def create_app(testing: bool = False) -> Flask:
	app = Flask(__name__)
	cors_origins = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
	CORS(app, origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()])
	app.config["JSON_SORT_KEYS"] = False
	app.config["TESTING"] = testing
	app.config["MAX_CONTENT_LENGTH"] = int(
		os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_MAX_CONTENT_LENGTH))
	)
	_initialize_database()

	@app.get("/")
	def health_check():
		data = {"service": "Developer Snippet Vault", "status": "running"}
		return api_response(data, "Developer Snippet Vault Running")

	@app.get("/app")
	def web_app():
		return send_from_directory(app.static_folder, "index.html")

	@app.post("/users")
	def create_user():
		payload, error_response = _get_json_body()
		if error_response:
			return error_response
		name = payload.get("name")
		if not isinstance(name, str) or not name.strip():
			return api_error("Validation failed.", 400, {"name": "Must be a non-empty string."})
		if len(name.strip()) > MAX_NAME_LENGTH:
			return api_error(
				"Validation failed.",
				400,
				{"name": f"Must be {MAX_NAME_LENGTH} characters or fewer."},
			)

		api_key = secrets.token_urlsafe(32)
		with _get_engine().begin() as connection:
			result = connection.execute(
				users_table.insert().values(
					name=_clean_text(name), api_key_hash=_hash_api_key(api_key)
				),
			)
		user = {"id": result.inserted_primary_key[0], "name": _clean_text(name), "api_key": api_key}
		return api_response(user, "User created.", 201)

	@app.post("/users/me/rotate-key")
	@require_api_key
	def rotate_api_key():
		api_key = secrets.token_urlsafe(32)
		with _get_engine().begin() as connection:
			connection.execute(
				text("UPDATE users SET api_key_hash = :api_key_hash WHERE id = :user_id"),
				{"api_key_hash": _hash_api_key(api_key), "user_id": g.user_id},
			)
		return api_response(
			{"user_id": g.user_id, "api_key": api_key},
			"API key rotated. Save the new key; it will not be shown again.",
		)

	@app.post("/snippets")
	@require_api_key
	def create_snippet():
		payload, error_response = _get_json_body()
		if error_response:
			return error_response

		is_valid, errors = _validate_snippet_payload(payload)
		if not is_valid:
			return api_error("Validation failed.", 400, errors)

		title = _clean_text(payload["title"])
		code = _clean_text(payload["code"])
		category = _clean_text(payload["category"])
		with _get_engine().begin() as connection:
			result = connection.execute(
				snippets_table.insert().values(
					title=title, code=code, category=category, user_id=g.user_id
				),
			)
			snippet = {
				"id": result.inserted_primary_key[0],
				"title": title,
				"code": code,
				"category": category,
			}

		return api_response(snippet, "Snippet created.", 201)

	@app.get("/snippets")
	@require_api_key
	def list_snippets():
		with _get_engine().connect() as connection:
			rows = connection.execute(
				text("SELECT id, title, code, category FROM snippets "
					 "WHERE user_id = :user_id ORDER BY id"),
				{"user_id": g.user_id},
			).mappings().all()
		snippets = [dict(row) for row in rows]
		data = {"snippets": snippets, "count": len(snippets)}
		return api_response(data, "Snippets retrieved.")

	@app.delete("/snippets/<int:snippet_id>")
	@require_api_key
	def delete_snippet(snippet_id: int):
		snippet = _find_snippet(snippet_id, g.user_id)
		if snippet is None:
			return api_error("Snippet not found.", 404)

		with _get_engine().begin() as connection:
			connection.execute(
				text("DELETE FROM snippets WHERE id = :snippet_id AND user_id = :user_id"),
				{"snippet_id": snippet_id, "user_id": g.user_id},
			)
		return api_response({"deleted": snippet}, "Snippet deleted.")

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
