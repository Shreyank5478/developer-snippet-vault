from unittest.mock import Mock, patch

from click.testing import CliRunner

import cli


def response_with(data, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def test_config_set_key_and_url_are_saved(monkeypatch, tmp_path):
    monkeypatch.setenv("SNIPPET_VAULT_CONFIG", str(tmp_path / "config.json"))
    runner = CliRunner()

    assert runner.invoke(cli.cli, ["config", "set-key", "secret-key"]).exit_code == 0
    result = runner.invoke(cli.cli, ["config", "set-url", "https://example.test/"])

    assert result.exit_code == 0
    assert cli._load_config() == {"url": "https://example.test", "api_key": "secret-key"}


def test_add_reads_code_from_stdin(monkeypatch, tmp_path):
    monkeypatch.setenv("SNIPPET_VAULT_CONFIG", str(tmp_path / "config.json"))
    cli._save_config({"url": "http://localhost:5000", "api_key": "key"})
    response = response_with({"data": {"id": 4, "title": "Hello"}}, 201)
    runner = CliRunner()

    with patch("cli.requests.request", return_value=response) as request:
        result = runner.invoke(cli.cli, ["add", "Hello", "-c", "python"], input="print(1)\n")

    assert result.exit_code == 0
    assert "Created snippet 4: Hello" in result.output
    request.assert_called_once_with(
        "POST",
        "http://localhost:5000/snippets",
        headers={"Authorization": "Bearer key"},
        timeout=10,
        json={"title": "Hello", "code": "print(1)\n", "category": "python"},
    )


def test_list_filters_by_category(monkeypatch, tmp_path):
    monkeypatch.setenv("SNIPPET_VAULT_CONFIG", str(tmp_path / "config.json"))
    cli._save_config({"url": "http://localhost:5000", "api_key": "key"})
    response = response_with(
        {"data": {"snippets": [
            {"id": 1, "category": "python", "title": "One"},
            {"id": 2, "category": "sql", "title": "Two"},
        ]}}
    )

    with patch("cli.requests.request", return_value=response):
        result = CliRunner().invoke(cli.cli, ["list", "-c", "python"])

    assert result.exit_code == 0
    assert "One" in result.output
    assert "Two" not in result.output


def test_rm_reports_deleted_snippet(monkeypatch, tmp_path):
    monkeypatch.setenv("SNIPPET_VAULT_CONFIG", str(tmp_path / "config.json"))
    cli._save_config({"url": "http://localhost:5000", "api_key": "key"})
    response = response_with({"data": {"deleted": {"id": 3, "title": "Old"}}})

    with patch("cli.requests.request", return_value=response):
        result = CliRunner().invoke(cli.cli, ["rm", "3"])

    assert result.exit_code == 0
    assert "Deleted snippet 3: Old" in result.output