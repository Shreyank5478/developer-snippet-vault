# Developer Snippet Vault

Developer Snippet Vault is a small Flask service for saving code snippets and
commands. It exposes a REST API, a browser UI, and a command-line client. Each
user gets an API key and can only access their own snippets.

## What It Includes

- REST API for creating, listing, and deleting snippets
- API-key authentication with per-user ownership
- PostgreSQL support for deployed environments
- SQLite fallback for local development
- Alembic migrations for controlled schema changes
- Plain HTML, CSS, and JavaScript web UI
- `snip` CLI for terminal use
- Docker and Gunicorn deployment

## Why It Changed

The first version kept snippets in memory, which meant a restart erased
everything. That was replaced with SQLite, then moved to PostgreSQL for the
deployed application. PostgreSQL is a better fit for multiple users and
concurrent requests, and Neon keeps the database independent from Render's
temporary service filesystem.

Authentication was added because an open snippet API would let any user read
or delete anyone else's data. API keys are stored as hashes, and the raw key is
shown only when the account is created or the key is rotated.

The web UI and CLI were added so the service can be used without writing curl
commands for every operation.

## Running Locally

Create an environment and install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The default local database is `data/snippets.db`. Apply the schema before
starting the server:

```bash
alembic upgrade head
python app.py
```

The API is available at `http://127.0.0.1:5000` and the web UI is at:

```text
http://127.0.0.1:5000/app
```

## Web UI

Open `/app` in a browser. You can either paste an existing API key or create a
new account. A new key is displayed once, so save it before leaving the page.

The UI supports:

- Creating an account
- Signing in and signing out
- Adding snippets
- Viewing your snippets
- Copying code
- Deleting snippets

## CLI

Install the project in editable mode:

```bash
pip install -e .
```

Configure the server and API key:

```bash
snip config set-url http://127.0.0.1:5000
snip config set-key <your-api-key>
```

Use the commands:

```bash
snip add "Hello World" -c python
echo "print('hello')" | snip add "Hello World" -c python
snip list
snip list -c python
snip rm 1
```

The CLI stores its settings in `~/.snippet-vault/config.json`.

## API

### Health check

```http
GET /
```

### Create a user

```bash
curl -X POST http://127.0.0.1:5000/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Your Name"}'
```

The response contains the API key. The server does not provide it again later.

### Create a snippet

```bash
curl -X POST http://127.0.0.1:5000/snippets \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Hello World","code":"print(1)","category":"python"}'
```

### List snippets

```bash
curl http://127.0.0.1:5000/snippets \
  -H "Authorization: Bearer <api-key>"
```

### Delete a snippet

```bash
curl -X DELETE http://127.0.0.1:5000/snippets/<id> \
  -H "Authorization: Bearer <api-key>"
```

### Rotate an API key

```bash
curl -X POST http://127.0.0.1:5000/users/me/rotate-key \
  -H "Authorization: Bearer <current-api-key>"
```

Rotating a key invalidates the old one immediately. Save the new key from the
response.

## Database Configuration

The application uses PostgreSQL when `DATABASE_URL` is set. This is the
recommended configuration for Render and Neon:

```text
DATABASE_URL=<Neon PostgreSQL connection string>
```

Do not commit the connection string or put it in chat. Add it as a secret in
Render's environment settings.

When `DATABASE_URL` is not set, the app uses local SQLite:

```text
DATABASE_PATH=data/snippets.db
```

Run migrations with:

```bash
alembic upgrade head
```

The migrations create the schema, remove pre-authentication snippets that have
no owner, and require every new snippet to belong to a user. The orphan cleanup
is a migration step, not something that runs on every application request.

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string; preferred for deployment
- `DATABASE_PATH`: SQLite file path used when `DATABASE_URL` is absent
- `PORT`: server port, default `5000`
- `MAX_CONTENT_LENGTH`: maximum request size in bytes, default `1048576`
- `CORS_ORIGINS`: comma-separated allowed origins; defaults to `*` for now

For production, set `CORS_ORIGINS` to the exact origins that should call the
API and use rate limiting for the public `POST /users` endpoint.

## Docker and Render

Build and run locally:

```bash
docker build -t developer-snippet-vault .
docker run -p 5000:5000 developer-snippet-vault
```

The container runs `alembic upgrade head` before starting Gunicorn. On Render,
set `DATABASE_URL` to the Neon connection string and deploy the branch that
contains the migrations. Do not rely on a local SQLite file for deployed data.

Note: on free-tier hosting, both the web service and database may take up to a
minute to respond after a period of inactivity.

Once `DATABASE_URL` is configured and the service is deployed, the UI is
available at:

```text
https://developer-snippet-vault.onrender.com/app
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
more details.

## Testing

Install development dependencies and run the full suite:

```bash
pip install -r requirements-dev.txt
pytest
```

The smoke test expects a running server:

```bash
python test_api.py https://developer-snippet-vault.onrender.com
```
