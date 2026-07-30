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


class GithubCreatePullReviewTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Create a review on a pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        pull_number = tool_parameters.get("pull_number")
        event = tool_parameters.get("event", "").upper()
        body = tool_parameters.get("body", "")
        commit_id = tool_parameters.get("commit_id", "")

        parameter_error = missing_parameter_message(
            tool_parameters,
            ["owner", "repo", "pull_number", ("event", "event (APPROVE, REQUEST_CHANGES, or COMMENT)")],
        )
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        # Validate event
        valid_events = ["APPROVE", "REQUEST_CHANGES", "COMMENT"]
        if event not in valid_events:
            yield self.create_text_message(f"Invalid event. Must be one of: {', '.join(valid_events)}")
            return

        # Body is required for REQUEST_CHANGES and COMMENT
        if event in ["REQUEST_CHANGES", "COMMENT"] and not body:
            yield self.create_text_message(f"Body is required when event is {event}")
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/repos/{owner}/{repo}/pulls/{int(pull_number)}/reviews"

            payload = {"event": event}
            if body:
                payload["body"] = body
            if commit_id:
                payload["commit_id"] = commit_id

            response = github_request("POST", path, access_token, json=payload)

            # API can return 200 or 201 for success
            if response.status_code in [200, 201]:
                review = response.json()

                # Safely extract user login
                user_data = review.get("user", {})
                user_login = user_data.get("login", "") if isinstance(user_data, dict) else ""

                result = {
                    "success": True,
                    "id": review.get("id"),
                    "user": user_login,
                    "state": review.get("state", ""),
                    "body": review.get("body", "") or "",
                    "commit_id": short_sha(review.get("commit_id")),
                    "submitted_at": format_datetime(review.get("submitted_at")),
                    "url": review.get("html_url", ""),
                }

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                handle_github_api_error(response, f"create review for pull request {owner}/{repo}#{pull_number}")
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
