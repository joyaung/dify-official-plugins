import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import format_datetime, github_request, missing_credentials_message, missing_parameter_message
from .github_error_handler import handle_github_api_error


class GithubUpdatePullTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Update an existing pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        pull_number = tool_parameters.get("pull_number")
        title = tool_parameters.get("title")
        body = tool_parameters.get("body")
        state = tool_parameters.get("state")
        base = tool_parameters.get("base")
        maintainer_can_modify = tool_parameters.get("maintainer_can_modify")

        parameter_error = missing_parameter_message(tool_parameters, ["owner", "repo", "pull_number"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        # Validate state if provided
        if state and state not in ["open", "closed"]:
            yield self.create_text_message("Invalid state. Must be 'open' or 'closed'")
            return

        # Build payload with only provided fields
        payload = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if base is not None:
            payload["base"] = base
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify

        if not payload:
            yield self.create_text_message("Please provide at least one field to update (title, body, state, base, or maintainer_can_modify)")
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/repos/{owner}/{repo}/pulls/{int(pull_number)}"

            response = github_request("PATCH", path, access_token, json=payload)

            if response.status_code == 200:
                pull = response.json()

                result = {
                    "success": True,
                    "number": pull.get("number", 0),
                    "title": pull.get("title", ""),
                    "state": pull.get("state", ""),
                    "url": pull.get("html_url", ""),
                    "draft": pull.get("draft", False),
                    "base": {
                        "ref": pull.get("base", {}).get("ref", ""),
                    },
                    "updated_at": format_datetime(pull.get("updated_at")),
                }

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                handle_github_api_error(response, f"update pull request {owner}/{repo}#{pull_number}")
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
