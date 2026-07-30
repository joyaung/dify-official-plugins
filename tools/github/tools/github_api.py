"""
Shared helpers for calling the GitHub REST API from the tools of this plugin.
"""
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, NoReturn

import requests
from dify_plugin.entities.provider_config import CredentialType
from dify_plugin.errors.model import InvokeError

GITHUB_API_DOMAIN = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
API_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_DATE_FORMAT = "%Y-%m-%d"


def missing_parameter_message(
    tool_parameters: Mapping[str, Any], required: Sequence[str | tuple[str, str]]
) -> str | None:
    """
    Return a message for the first missing required parameter, or None when all are present.

    Each entry is either a parameter name, or a (parameter name, label) pair when the
    message should mention something other than the raw parameter name.
    """
    for entry in required:
        name, label = entry if isinstance(entry, tuple) else (entry, entry)
        if not tool_parameters.get(name):
            return f"Please input {label}"
    return None


def missing_credentials_message(runtime) -> str | None:
    """
    Return a message when the access token needed to call the API is not configured.
    """
    if "access_tokens" in runtime.credentials:
        return None
    if runtime.credential_type == CredentialType.API_KEY:
        return "GitHub API Access Tokens is required."
    if runtime.credential_type == CredentialType.OAUTH:
        return "GitHub OAuth Access Tokens is required."
    return None


def build_headers(access_token: str | None, **extra: str) -> dict[str, str]:
    """
    Build the default GitHub API request headers.
    """
    return {
        "Content-Type": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        **extra,
    }


def github_request(
    method: str,
    path: str,
    access_token: str | None,
    *,
    params: Mapping[str, Any] | None = None,
    json: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> requests.Response:
    """
    Send a request to the GitHub API and return the raw response.

    `path` is appended to the API domain, e.g. "/repos/langgenius/dify/commits".
    """
    with requests.session() as session:
        return session.request(
            method=method,
            url=f"{GITHUB_API_DOMAIN}{path}",
            headers=dict(headers) if headers is not None else build_headers(access_token),
            params=params,
            json=json,
        )


def raise_request_error(response: requests.Response, context: str = "") -> NoReturn:
    """
    Raise an InvokeError describing a failed GitHub API response.
    """
    context_msg = f" while {context}" if context else ""
    raise InvokeError(f"Request failed{context_msg}: {response.status_code} {error_message(response)}")


def error_message(response: requests.Response) -> str:
    """
    Extract the error message of a failed GitHub API response.
    """
    try:
        payload = response.json()
    except Exception:
        return "Unknown error"
    if isinstance(payload, Mapping):
        return payload.get("message") or "Unknown error"
    return "Unknown error"


def format_datetime(value: str | None, fmt: str = DISPLAY_DATETIME_FORMAT) -> str:
    """
    Convert a GitHub API timestamp into a human readable one, "" when absent.
    """
    if not value:
        return ""
    return datetime.strptime(value, API_DATETIME_FORMAT).strftime(fmt)


def short_sha(value: str | None) -> str:
    """
    Shorten a git object id to its usual 7 character prefix.
    """
    return value[:7] if value else ""
