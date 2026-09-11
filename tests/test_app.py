import app as app_module
import pytest


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snippets.db"))
    app_module._reset_store()
    app = app_module.create_app(testing=True)
    with app.test_client() as client:
        user_response = client.post("/users", json={"name": "Test User"})
        api_key = user_response.get_json()["data"]["api_key"]
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {api_key}"
        yield client


def test_health_check(client):
    response = client.get("/")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["message"] == "Developer Snippet Vault Running"
    assert payload["data"]["status"] == "running"


def test_web_app_is_served_at_app_route(client):
    response = client.get("/app")

    assert response.status_code == 200
    assert b"Snippet Vault" in response.data
    assert response.mimetype == "text/html"


def test_api_includes_cors_header(client):
    response = client.get("/", headers={"Origin": "https://example.test"})

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://example.test"


def test_cors_can_be_restricted(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snippets.db"))
    monkeypatch.setenv("CORS_ORIGINS", "https://trusted.example")
    app = app_module.create_app(testing=True)

    with app.test_client() as test_client:
        allowed = test_client.get("/", headers={"Origin": "https://trusted.example"})
        blocked = test_client.get("/", headers={"Origin": "https://other.example"})

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://trusted.example"
    assert "Access-Control-Allow-Origin" not in blocked.headers


def test_create_snippet_success(client):
    payload = {"title": "Hello", "code": "print('hi')", "category": "python"}
    response = client.post("/snippets", json=payload)
    data = response.get_json()

    assert response.status_code == 201
    assert data["data"]["title"] == payload["title"]
    assert data["data"]["code"] == payload["code"]
    assert data["data"]["category"] == payload["category"]


def test_list_snippets_includes_created(client):
    payload = {"title": "Hello", "code": "print('hi')", "category": "python"}
    create_response = client.post("/snippets", json=payload)
    snippet_id = create_response.get_json()["data"]["id"]

    response = client.get("/snippets")
    data = response.get_json()

    assert response.status_code == 200
    assert data["data"]["count"] == 1
    assert any(item["id"] == snippet_id for item in data["data"]["snippets"])


def test_snippets_persist_when_app_is_recreated(client, monkeypatch, tmp_path):
    payload = {"title": "Persistent", "code": "echo hello", "category": "shell"}
    client.post("/snippets", json=payload)
    authorization = client.environ_base["HTTP_AUTHORIZATION"]

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snippets.db"))
    recreated_app = app_module.create_app(testing=True)
    with recreated_app.test_client() as recreated_client:
        response = recreated_client.get(
            "/snippets", headers={"Authorization": authorization}
        )

    data = response.get_json()
    assert response.status_code == 200
    assert data["data"]["count"] == 1
    assert data["data"]["snippets"][0]["title"] == payload["title"]


def test_app_startup_deletes_orphaned_snippets(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snippets.db"))
    app_module.create_app(testing=True)
    with app_module._get_engine().begin() as connection:
        connection.execute(
            app_module.snippets_table.insert().values(
                title="Legacy", code="old", category="test", user_id=None
            )
        )

    app_module.create_app(testing=True)
    with app_module._get_engine().connect() as connection:
        count = connection.execute(
            app_module.text("SELECT COUNT(*) FROM snippets")
        ).scalar_one()

    assert count == 0


def test_snippet_routes_require_authentication(client):
    client.environ_base.pop("HTTP_AUTHORIZATION")

    response = client.get("/snippets")

    assert response.status_code == 401


def test_users_cannot_access_each_others_snippets(client, monkeypatch, tmp_path):
    payload = {"title": "Private", "code": "secret", "category": "test"}
    snippet_id = client.post("/snippets", json=payload).get_json()["data"]["id"]

    second_app = app_module.create_app(testing=True)
    with second_app.test_client() as second_client:
        second_user = second_client.post("/users", json={"name": "Other User"})
        second_key = second_user.get_json()["data"]["api_key"]
        response = second_client.get(
            "/snippets", headers={"X-API-Key": second_key}
        )
        delete_response = second_client.delete(
            f"/snippets/{snippet_id}", headers={"X-API-Key": second_key}
        )

    assert response.status_code == 200
    assert response.get_json()["data"]["count"] == 0
    assert delete_response.status_code == 404


def test_rotating_api_key_invalidates_the_old_key(client):
    old_key = client.environ_base["HTTP_AUTHORIZATION"].removeprefix("Bearer ")
    response = client.post("/users/me/rotate-key")
    new_key = response.get_json()["data"]["api_key"]

    assert response.status_code == 200
    assert new_key != old_key

    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {old_key}"
    assert client.get("/snippets").status_code == 401

    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {new_key}"
    assert client.get("/snippets").status_code == 200


def test_invalid_json_returns_error(client):
    response = client.post(
        "/snippets",
        data="not json",
        content_type="application/json",
    )
    data = response.get_json()

    assert response.status_code == 400
    assert data["success"] is False
    assert data["message"]


def test_missing_fields_returns_errors(client):
    response = client.post("/snippets", json={"title": "Only title"})
    data = response.get_json()

    assert response.status_code == 400
    assert "code" in data.get("errors", {})
    assert "category" in data.get("errors", {})


def test_user_name_length_is_validated(client):
    response = client.post("/users", json={"name": "x" * 121})

    assert response.status_code == 400
    assert "name" in response.get_json()["errors"]


def test_empty_field_returns_error(client):
    response = client.post(
        "/snippets",
        json={"title": " ", "code": "print('x')", "category": "python"},
    )
    data = response.get_json()

    assert response.status_code == 400
    assert "title" in data.get("errors", {})


def test_delete_missing_snippet_returns_404(client):
    response = client.delete("/snippets/9999")
    data = response.get_json()

    assert response.status_code == 404
    assert data["message"] == "Snippet not found."
