import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import (
    format_datetime,
    github_request,
    missing_credentials_message,
    missing_parameter_message,
    short_sha,
)
from .github_error_handler import handle_github_api_error


class GithubCreatePullTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Create a new pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        title = tool_parameters.get("title", "")
        head = tool_parameters.get("head", "")
        base = tool_parameters.get("base", "")
        body = tool_parameters.get("body", "")
        draft = tool_parameters.get("draft", False)
        maintainer_can_modify = tool_parameters.get("maintainer_can_modify", True)

        parameter_error = missing_parameter_message(
            tool_parameters,
            ["owner", "repo", "title", ("head", "head branch"), ("base", "base branch")],
        )
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/repos/{owner}/{repo}/pulls"

            payload = {
                "title": title,
                "head": head,
                "base": base,
                "draft": draft,
                "maintainer_can_modify": maintainer_can_modify,
            }
            if body:
                payload["body"] = body

            response = github_request("POST", path, access_token, json=payload)

            if response.status_code == 201:
                pull = response.json()

                result = {
                    "success": True,
                    "number": pull.get("number", 0),
                    "title": pull.get("title", ""),
                    "state": pull.get("state", ""),
                    "url": pull.get("html_url", ""),
                    "draft": pull.get("draft", False),
                    "head": {
                        "ref": pull.get("head", {}).get("ref", ""),
                        "sha": short_sha(pull.get("head", {}).get("sha")),
                    },
                    "base": {
                        "ref": pull.get("base", {}).get("ref", ""),
                    },
                    "created_at": format_datetime(pull.get("created_at")),
                }

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                handle_github_api_error(response, f"create pull request in {owner}/{repo}")
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
