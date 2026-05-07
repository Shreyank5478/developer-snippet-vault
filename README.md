# Developer Snippet Vault

A production-style Flask backend API for managing developer snippets and commands.

## Features

* Create snippets
* View snippets
* Delete snippets
* Input validation
* SQLite persistence
* REST API structure
* Dockerized deployment

## Tech Stack

* Python
* Flask
* Flask-SQLAlchemy
* SQLite
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

On first run, the app will create a local SQLite database file named `snippets.db`.

## API Endpoints

### Health Check

```
GET /
```

### Create Snippet

```
POST /snippets
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
```

### Delete Snippet

```
DELETE /snippets/<id>
```

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
- `MAX_CONTENT_LENGTH` (bytes, default: 1048576)
- `DATABASE_URL` (optional, overrides SQLite path)

## Deployment

This application is deployed on an AWS EC2 Ubuntu server using Docker containers.

## Learning Goals

This project was built to learn:

* Backend API development
* Docker containerization
* Linux server management
* Cloud deployment on AWS
* DevOps workflow fundamentals
