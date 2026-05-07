import app as app_module
import pytest


@pytest.fixture()
def client():
    app_module._reset_store()
    app = app_module.create_app(testing=True)
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get("/")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["message"] == "Developer Snippet Vault Running"
    assert payload["data"]["status"] == "running"


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
