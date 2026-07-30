import sys
from types import SimpleNamespace

import pytest
from dify_plugin.entities.provider_config import CredentialType
from dify_plugin.errors.model import InvokeError

sys.path.insert(0, "tools/github")

from tools.github_api import (  # noqa: E402
    GITHUB_API_DOMAIN,
    GITHUB_API_VERSION,
    build_headers,
    error_message,
    format_datetime,
    github_request,
    missing_credentials_message,
    missing_parameter_message,
    raise_request_error,
    short_sha,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, raises=False):
        self.status_code = status_code
        self._payload = payload
        self._raises = raises

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._payload


def test_missing_parameter_message_reports_first_missing_parameter():
    parameters = {"owner": "langgenius", "repo": "", "head": ""}
    assert missing_parameter_message(parameters, ["owner"]) is None
    assert missing_parameter_message(parameters, ["owner", "repo"]) == "Please input repo"
    assert missing_parameter_message(parameters, [("head", "head branch")]) == "Please input head branch"


@pytest.mark.parametrize(
    ("credential_type", "expected"),
    [
        (CredentialType.API_KEY, "GitHub API Access Tokens is required."),
        (CredentialType.OAUTH, "GitHub OAuth Access Tokens is required."),
    ],
)
def test_missing_credentials_message_depends_on_credential_type(credential_type, expected):
    runtime = SimpleNamespace(credentials={}, credential_type=credential_type)
    assert missing_credentials_message(runtime) == expected


def test_missing_credentials_message_none_when_token_present():
    runtime = SimpleNamespace(credentials={"access_tokens": "token"}, credential_type=CredentialType.API_KEY)
    assert missing_credentials_message(runtime) is None


def test_build_headers():
    headers = build_headers("token", Accept="application/vnd.github.raw")
    assert headers == {
        "Content-Type": "application/vnd.github+json",
        "Authorization": "Bearer token",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "Accept": "application/vnd.github.raw",
    }


def test_github_request_targets_the_api_domain(monkeypatch):
    captured = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr("tools.github_api.requests.session", lambda: FakeSession())

    response = github_request("GET", "/repos/langgenius/dify/commits", "token", params={"per_page": 10})

    assert response.status_code == 200
    assert captured["method"] == "GET"
    assert captured["url"] == f"{GITHUB_API_DOMAIN}/repos/langgenius/dify/commits"
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert captured["params"] == {"per_page": 10}
    assert captured["json"] is None


def test_error_message_falls_back_to_unknown_error():
    assert error_message(FakeResponse(payload={"message": "Not Found"})) == "Not Found"
    assert error_message(FakeResponse(payload=[])) == "Unknown error"
    assert error_message(FakeResponse(raises=True)) == "Unknown error"


def test_raise_request_error():
    with pytest.raises(InvokeError, match="Request failed: 404 Not Found"):
        raise_request_error(FakeResponse(status_code=404, payload={"message": "Not Found"}))

    with pytest.raises(InvokeError, match="Request failed while merging: 409 Conflict"):
        raise_request_error(FakeResponse(status_code=409, payload={"message": "Conflict"}), "merging")


def test_format_datetime():
    assert format_datetime("2025-01-02T03:04:05Z") == "2025-01-02 03:04:05"
    assert format_datetime("2025-01-02T03:04:05Z", "%Y-%m-%d") == "2025-01-02"
    assert format_datetime(None) == ""
    assert format_datetime("") == ""


def test_short_sha():
    assert short_sha("0123456789abcdef") == "0123456"
    assert short_sha(None) == ""
    assert short_sha("") == ""
