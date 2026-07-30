import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import format_datetime, github_request, missing_credentials_message, missing_parameter_message
from .github_error_handler import handle_github_api_error


class GithubIssueCommentTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Create a comment on an issue
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        issue_number = tool_parameters.get("issue_number")
        body = tool_parameters.get("body", "")

        parameter_error = missing_parameter_message(
            tool_parameters,
            ["owner", "repo", "issue_number", ("body", "comment body")],
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
            path = f"/repos/{owner}/{repo}/issues/{int(issue_number)}/comments"

            payload = {"body": body}

            response = github_request("POST", path, access_token, json=payload)

            # API can return 200 or 201 for success
            if response.status_code in [200, 201]:
                comment = response.json()

                # Safely extract user login
                user_data = comment.get("user", {})
                user_login = user_data.get("login", "") if isinstance(user_data, dict) else ""

                result = {
                    "success": True,
                    "id": comment.get("id"),
                    "user": user_login,
                    "body": comment.get("body", ""),
                    "created_at": format_datetime(comment.get("created_at")),
                    "updated_at": format_datetime(comment.get("updated_at")),
                    "url": comment.get("html_url", ""),
                }

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                handle_github_api_error(response, f"create comment on issue {owner}/{repo}#{issue_number}")
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
