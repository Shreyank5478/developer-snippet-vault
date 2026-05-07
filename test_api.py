"""Beginner-friendly API tests for Developer Snippet Vault."""

import sys

import requests


BASE_URL = "http://127.0.0.1:5000"
if len(sys.argv) > 1:
    BASE_URL = sys.argv[1].rstrip("/")


def print_result(test_name: str, passed: bool, details: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {details}" if details else ""
    print(f"[{status}] {test_name}{suffix}")


def main() -> None:
    # Make sure the Flask app is running before starting the tests.
    try:
        requests.get(f"{BASE_URL}/", timeout=5)
    except requests.RequestException as exc:
        print_result("Server reachable", False, str(exc))
        return

    # 1) GET / should return a JSON status message.
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()
        passed = (
            response.status_code == 200
            and data.get("success") is True
            and data.get("message") == "Developer Snippet Vault Running"
            and data.get("data", {}).get("status") == "running"
        )
        print_result("GET / returns status message", passed)
    except requests.RequestException as exc:
        print_result("GET / returns status message", False, str(exc))
        return
    except ValueError as exc:
        print_result("GET / returns status message", False, f"Invalid JSON: {exc}")
        return

    # 2) POST /snippets with valid data should create a snippet.
    snippet_payload = {
        "title": "Hello World",
        "code": "print('hello')",
        "category": "python",
    }
    snippet_id = None
    try:
        response = requests.post(f"{BASE_URL}/snippets", json=snippet_payload, timeout=5)
        if response.status_code == 201:
            data = response.json()
            snippet = data.get("data", {})
            has_fields = (
                isinstance(snippet.get("id"), int)
                and snippet.get("title") == snippet_payload["title"]
                and snippet.get("code") == snippet_payload["code"]
                and snippet.get("category") == snippet_payload["category"]
            )
            print_result("POST /snippets valid payload", has_fields)
            snippet_id = snippet.get("id")
        else:
            print_result("POST /snippets valid payload", False, f"Status {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        print_result("POST /snippets valid payload", False, str(exc))
        return

    # 3) GET /snippets should return a list containing the new snippet.
    try:
        response = requests.get(f"{BASE_URL}/snippets", timeout=5)
        if response.status_code == 200:
            data = response.json()
            snippet_list = data.get("data", {}).get("snippets", [])
            has_snippet = isinstance(snippet_list, list) and any(
                item.get("id") == snippet_id for item in snippet_list
            )
            print_result("GET /snippets returns list", has_snippet)
        else:
            print_result("GET /snippets returns list", False, f"Status {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        print_result("GET /snippets returns list", False, str(exc))
        return

    # 4) POST /snippets with invalid JSON should fail.
    try:
        response = requests.post(
            f"{BASE_URL}/snippets",
            data="not valid json",
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if response.status_code == 400:
            message = response.json().get("message")
            print_result("POST /snippets invalid JSON", bool(message))
        else:
            print_result("POST /snippets invalid JSON", False, f"Status {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        print_result("POST /snippets invalid JSON", False, str(exc))
        return

    # 5) POST /snippets with missing fields should fail.
    try:
        response = requests.post(
            f"{BASE_URL}/snippets",
            json={"title": "Only a title"},
            timeout=5,
        )
        if response.status_code == 400:
            errors = response.json().get("errors", {})
            print_result("POST /snippets missing fields", bool(errors))
        else:
            print_result("POST /snippets missing fields", False, f"Status {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        print_result("POST /snippets missing fields", False, str(exc))
        return

    # 6) POST /snippets with empty fields should fail.
    try:
        response = requests.post(
            f"{BASE_URL}/snippets",
            json={"title": " ", "code": "print('x')", "category": "python"},
            timeout=5,
        )
        if response.status_code == 400:
            errors = response.json().get("errors", {})
            print_result("POST /snippets empty field", bool(errors))
        else:
            print_result("POST /snippets empty field", False, f"Status {response.status_code}")
    except (requests.RequestException, ValueError) as exc:
        print_result("POST /snippets empty field", False, str(exc))
        return

    # 7) DELETE /snippets/<id> should delete an existing snippet.
    if isinstance(snippet_id, int):
        try:
            response = requests.delete(f"{BASE_URL}/snippets/{snippet_id}", timeout=5)
            if response.status_code == 200:
                deleted = response.json().get("data", {}).get("deleted", {})
                print_result("DELETE /snippets/<id> existing", deleted.get("id") == snippet_id)
            else:
                print_result("DELETE /snippets/<id> existing", False, f"Status {response.status_code}")
        except (requests.RequestException, ValueError) as exc:
            print_result("DELETE /snippets/<id> existing", False, str(exc))
            return
    else:
        print_result("DELETE /snippets/<id> existing", False, "No snippet id to delete")

    # 8) DELETE /snippets/<id> for a missing snippet should return 404.
    try:
        response = requests.delete(f"{BASE_URL}/snippets/99999", timeout=5)
        passed = response.status_code == 404 and response.json().get("message")
        print_result("DELETE /snippets/<id> non-existing", bool(passed))
    except (requests.RequestException, ValueError) as exc:
        print_result("DELETE /snippets/<id> non-existing", False, str(exc))


if __name__ == "__main__":
    main()
