from __future__ import annotations

import os
from itertools import count
from typing import Any

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

MAX_TITLE_LENGTH = 120
MAX_CATEGORY_LENGTH = 40
MAX_CODE_LENGTH = 10_000
DEFAULT_MAX_CONTENT_LENGTH = 1_048_576

# In-memory data store for snippets. This resets whenever the server restarts.
snippets: list[dict[str, Any]] = []
_id_counter = count(start=1)


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


def _find_snippet(snippet_id: int) -> dict[str, Any] | None:
	return next((snippet for snippet in snippets if snippet["id"] == snippet_id), None)


def _reset_store() -> None:
	snippets.clear()
	global _id_counter
	_id_counter = count(start=1)


def create_app(testing: bool = False) -> Flask:
	app = Flask(__name__)
	app.config["JSON_SORT_KEYS"] = False
	app.config["TESTING"] = testing
	app.config["MAX_CONTENT_LENGTH"] = int(
		os.getenv("MAX_CONTENT_LENGTH", str(DEFAULT_MAX_CONTENT_LENGTH))
	)

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

		snippet = {
			"id": next(_id_counter),
			"title": _clean_text(payload["title"]),
			"code": _clean_text(payload["code"]),
			"category": _clean_text(payload["category"]),
		}
		snippets.append(snippet)

		return api_response(snippet, "Snippet created.", 201)

	@app.get("/snippets")
	def list_snippets():
		data = {"snippets": snippets, "count": len(snippets)}
		return api_response(data, "Snippets retrieved.")

	@app.delete("/snippets/<int:snippet_id>")
	def delete_snippet(snippet_id: int):
		snippet = _find_snippet(snippet_id)
		if snippet is None:
			return api_error("Snippet not found.", 404)

		snippets.remove(snippet)
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
