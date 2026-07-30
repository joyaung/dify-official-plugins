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
    raise_request_error,
)


class GithubRepositoryIssuesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        state = tool_parameters.get("state", "open")
        per_page = tool_parameters.get("per_page", 10)
        sort = tool_parameters.get("sort", "created")
        direction = tool_parameters.get("direction", "desc")

        parameter_error = missing_parameter_message(tool_parameters, ["owner", "repo"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/repos/{owner}/{repo}/issues"

            params = {"state": state, "per_page": per_page, "sort": sort, "direction": direction}

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                issues = []
                for issue in response_data:
                    # Skip pull requests (they also appear in issues API)
                    if issue.get("pull_request"):
                        continue

                    issue_info = {
                        "number": issue.get("number", 0),
                        "title": issue.get("title", ""),
                        "body": (issue.get("body", "") or "")[:200] + "..."
                        if len(issue.get("body", "") or "") > 200
                        else (issue.get("body", "") or ""),
                        "state": issue.get("state", ""),
                        "url": issue.get("html_url", ""),
                        "user": issue.get("user", {}).get("login", ""),
                        "assignee": issue.get("assignee", {}).get("login", "") if issue.get("assignee") else "",
                        "labels": [label.get("name", "") for label in issue.get("labels", [])],
                        "comments": issue.get("comments", 0),
                        "created_at": format_datetime(issue.get("created_at")),
                        "updated_at": format_datetime(issue.get("updated_at")),
                    }
                    issues.append(issue_info)

                if not issues:
                    yield self.create_text_message(f"No {state} issues found in {owner}/{repo}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(issues, ensure_ascii=False),
                            instruction="Summarize the GitHub issues in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
