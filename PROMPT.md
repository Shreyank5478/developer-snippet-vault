# Prompt: Developer Snippet Vault (Current State)

You are a senior Software Engineer, DevOps Engineer, and SQA reviewer.

Please use the following project context and change log when reviewing or continuing work.

## Project Summary
- Flask backend API for managing developer snippets and commands.
- In-memory storage only (no database yet).
- REST endpoints: GET /, POST /snippets, GET /snippets, DELETE /snippets/<id>.

## Features (Current)
- Create, list, and delete snippets.
- JSON input validation with clear error messages.
- Consistent success/error response shape.
- Request size limit enforcement.
- Dockerized deployment using Gunicorn.
- Beginner-friendly learning guide.
- Pytest test suite for API behavior.

## Changes Applied (All Recent Updates)
1) App refactor and configuration
- Introduced app factory: create_app(testing=False).
- Added env-based config:
  - PORT (default 5000)
  - FLASK_DEBUG (set to 1 for debug)
  - MAX_CONTENT_LENGTH (default 1048576 bytes)
- Added request size handling with 413 response.
- Kept in-memory store but added _reset_store() for test isolation.

2) Validation improvements
- Added length limits:
  - title: 120 chars
  - category: 40 chars
  - code: 10,000 chars
- Enforced non-empty, string-only fields.

3) Error response consistency
- Error payload now includes data: null (to match success shape).

4) Docker hardening
- Dockerfile now runs as a non-root user.
- Uses gunicorn instead of Flask dev server.
- Adds PYTHONDONTWRITEBYTECODE and PYTHONUNBUFFERED.
- Added .dockerignore to reduce build context.

5) Dependencies cleanup
- requirements.txt rewritten as UTF-8.
- Added gunicorn to requirements.txt.
- Added requirements-dev.txt (pytest, pytest-cov, requests).

6) Testing upgrades
- Added pytest suite using Flask test client:
  - Health check
  - Create snippet success
  - List snippets includes created
  - Invalid JSON
  - Missing fields
  - Empty fields
  - Delete missing snippet

7) Documentation upgrades
- README updated with:
  - Quick start
  - API examples
  - Testing instructions
  - Docker build/run steps
  - Config variables

## Files Modified
- app.py (app factory, validation, error handling, config)
- Dockerfile (gunicorn, non-root, env vars)
- requirements.txt (UTF-8, gunicorn)
- README.md (setup, API, tests, Docker, config)

## Files Added
- .dockerignore
- requirements-dev.txt
- tests/test_app.py

## Constraints and Current Decisions
- Keep in-memory storage for now (no DB yet).
- No authentication or rate limiting yet (learning mode).
- Avoid breaking existing API behavior.

## What I Want You To Do Next
- Continue improving the project without breaking current functionality.
- Keep changes production-minded but beginner-friendly.
- Suggest practical, incremental improvements with clear rationale.
