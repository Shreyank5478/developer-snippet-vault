# Developer Snippet Vault

A production-style Flask backend API for managing developer snippets and commands.

## Features

* Create snippets
* View snippets
* Delete snippets
* API-key authentication and per-user ownership
* Input validation
* REST API structure
* Dockerized deployment

## Tech Stack

* Python
* Flask
* Docker
* AWS EC2
* Linux
* Git & GitHub

## Quick Start (Local)

1) Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2) Run the server:

```bash
python app.py
```

The API will be available at `http://127.0.0.1:5000`.

## Web UI

The plain HTML/CSS/JavaScript web UI is served by the same Flask app at:

```text
http://127.0.0.1:5000/app
```

After deployment, replace the host with your deployed service URL. Paste an
existing API key to sign in, or create a user from the UI. A newly created API
key is displayed once, so copy and save it securely.

## CLI

Install the project in editable mode to create the `snip` command:

```bash
pip install -e .
snip config set-url http://127.0.0.1:5000
snip config set-key <your-api-key>
```

Create a user with `POST /users` first to obtain an API key. Then use the CLI:

```bash
snip add "Hello World" -c python
echo "print('hello')" | snip add "Hello World" -c python
snip list
snip list -c python
snip rm 1
```

The CLI stores its connection settings in `~/.snippet-vault/config.json`.

## API Endpoints

### Health Check

```
GET /
```

### Create Snippet

```
POST /snippets
Authorization: Bearer <api-key>
Content-Type: application/json

{
	"title": "Hello World",
	"code": "print('hello')",
	"category": "python"
}
```

### List Snippets

```
GET /snippets
Authorization: Bearer <api-key>
```

### Delete Snippet

```
DELETE /snippets/<id>
Authorization: Bearer <api-key>
```

### Create User

```bash
curl -X POST http://127.0.0.1:5000/users \
	-H "Content-Type: application/json" \
	-d '{"name":"Your Name"}'
```

The response contains the user's API key. Store it securely because it is only
shown when the user is created. Each user can only view and delete their own
snippets.

Rotate a compromised key with the current key:

```bash
curl -X POST https://your-service.onrender.com/users/me/rotate-key \
	-H "Authorization: Bearer <current-api-key>"
```

The old key stops working immediately, and the new key is returned only once.

For production, configure `CORS_ORIGINS` with the exact browser origins you
trust, and use Render rate limiting or an upstream proxy to protect the public
`POST /users` endpoint from automated account creation.

## Testing

Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest
```

Optional smoke test (requires the server running):

```bash
python test_api.py
```

## Docker

Build and run the container:

```bash
docker build -t developer-snippet-vault .
docker run -p 5000:5000 developer-snippet-vault
```

## Configuration

Environment variables:

- `PORT` (default: 5000)
- `FLASK_DEBUG` (set to `1` for debug mode)
- `DATABASE_URL` (PostgreSQL URL; preferred for deployment)
- `MAX_CONTENT_LENGTH` (bytes, default: 1048576)
- `DATABASE_PATH` (SQLite database path, default: `data/snippets.db`)
- `CORS_ORIGINS` (comma-separated origins, default: `*`; restrict this in production)

The app uses PostgreSQL when `DATABASE_URL` is set and SQLite locally when it is
not. PostgreSQL is recommended for Render and concurrent users. During startup,
snippets with no `user_id` are deleted because they predate authentication and
cannot be assigned safely.

For Render, create a PostgreSQL database and set the web service's
`DATABASE_URL` environment variable to the database's internal connection URL.
Do not set `DATABASE_PATH` in that deployment; it is only the local SQLite
fallback.

For local SQLite-only Docker usage, mount the database directory:

```bash
docker run -p 5000:5000 -v snippet-data:/app/data developer-snippet-vault
```

## Deployment

This application is deployed on an AWS EC2 Ubuntu server using Docker containers.

## Learning Goals

This project was built to learn:

* Backend API development
* Docker containerization
* Linux server management
* Cloud deployment on AWS
* DevOps workflow fundamentals
