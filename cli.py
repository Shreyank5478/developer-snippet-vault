import json
import os
import sys
from pathlib import Path

import click
import requests

DEFAULT_URL = "http://127.0.0.1:5000"


def _config_path() -> Path:
	configured_path = os.getenv("SNIPPET_VAULT_CONFIG")
	return Path(configured_path).expanduser() if configured_path else Path.home() / ".snippet-vault" / "config.json"


def _load_config() -> dict[str, str]:
	path = _config_path()
	if not path.exists():
		return {"url": DEFAULT_URL}
	try:
		with path.open(encoding="utf-8") as config_file:
			config = json.load(config_file)
		return config if isinstance(config, dict) else {"url": DEFAULT_URL}
	except (OSError, json.JSONDecodeError) as error:
		raise click.ClickException(f"Could not read config: {error}") from error


def _save_config(config: dict[str, str]) -> None:
	path = _config_path()
	try:
		path.parent.mkdir(parents=True, exist_ok=True)
		with path.open("w", encoding="utf-8") as config_file:
			json.dump(config, config_file, indent=2)
			config_file.write("\n")
	except OSError as error:
		raise click.ClickException(f"Could not save config: {error}") from error


def _request(method: str, endpoint: str, **kwargs):
	config = _load_config()
	api_key = config.get("api_key")
	if not api_key:
		raise click.ClickException("No API key configured. Run: snip config set-key <key>")

	url = f"{config.get('url', DEFAULT_URL).rstrip('/')}{endpoint}"
	try:
		response = requests.request(
			method, url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10, **kwargs
		)
		response.raise_for_status()
		return response.json()
	except requests.RequestException as error:
		message = error.response.json().get("message") if error.response is not None else str(error)
		raise click.ClickException(f"Request failed: {message}") from error
	except ValueError as error:
		raise click.ClickException("Server returned invalid JSON.") from error


@click.group()
def cli():
	"""Manage snippets in Developer Snippet Vault."""


@cli.group()
def config():
	"""Configure the API connection."""


@config.command("set-key")
@click.argument("api_key")
def set_key(api_key: str):
	settings = _load_config()
	settings["api_key"] = api_key
	_save_config(settings)
	click.echo(f"API key saved to {_config_path()}")


@config.command("set-url")
@click.argument("url")
def set_url(url: str):
	settings = _load_config()
	settings["url"] = url.rstrip("/")
	_save_config(settings)
	click.echo(f"Server URL saved: {settings['url']}")


@cli.command()
@click.argument("title")
@click.option("-c", "category", required=True, help="Snippet category.")
def add(title: str, category: str):
	"""Add a snippet, reading code from stdin or a prompt."""
	if not sys.stdin.isatty():
		code = sys.stdin.read()
	else:
		code = click.prompt("Code", prompt_suffix=":", hide_input=False)
	result = _request(
		"POST", "/snippets", json={"title": title, "code": code, "category": category}
	)
	snippet = result.get("data", {})
	click.echo(f"Created snippet {snippet.get('id')}: {snippet.get('title')}")


@cli.command(name="list")
@click.option("-c", "category", help="Only show this category.")
def list_snippets(category: str | None):
	"""List your snippets in a table."""
	result = _request("GET", "/snippets")
	snippets = result.get("data", {}).get("snippets", [])
	if category:
		snippets = [snippet for snippet in snippets if snippet.get("category") == category]
	if not snippets:
		click.echo("No snippets found.")
		return
	click.echo(f"{'ID':<5} {'CATEGORY':<15} TITLE")
	click.echo("-" * 45)
	for snippet in snippets:
		click.echo(f"{snippet['id']:<5} {snippet['category']:<15} {snippet['title']}")


@cli.command()
@click.argument("snippet_id", type=int)
def rm(snippet_id: int):
	"""Delete a snippet by ID."""
	result = _request("DELETE", f"/snippets/{snippet_id}")
	deleted = result.get("data", {}).get("deleted", {})
	click.echo(f"Deleted snippet {deleted.get('id')}: {deleted.get('title')}")


if __name__ == "__main__":
	cli()