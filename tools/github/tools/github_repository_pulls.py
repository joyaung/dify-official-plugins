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
    short_sha,
)


class GithubRepositoryPullsTool(Tool):
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
            path = f"/repos/{owner}/{repo}/pulls"

            params = {"state": state, "per_page": per_page, "sort": sort, "direction": direction}

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                pulls = []
                for pull in response_data:
                    pull_info = {
                        "number": pull.get("number", 0),
                        "title": pull.get("title", ""),
                        "body": (pull.get("body", "") or "")[:200] + "..."
                        if len(pull.get("body", "") or "") > 200
                        else (pull.get("body", "") or ""),
                        "state": pull.get("state", ""),
                        "url": pull.get("html_url", ""),
                        "user": pull.get("user", {}).get("login", ""),
                        "assignee": pull.get("assignee", {}).get("login", "") if pull.get("assignee") else "",
                        "labels": [label.get("name", "") for label in pull.get("labels", [])],
                        "comments": pull.get("comments", 0),
                        "review_comments": pull.get("review_comments", 0),
                        "commits": pull.get("commits", 0),
                        "additions": pull.get("additions", 0),
                        "deletions": pull.get("deletions", 0),
                        "changed_files": pull.get("changed_files", 0),
                        "mergeable": pull.get("mergeable", None),
                        "merged": pull.get("merged", False),
                        "draft": pull.get("draft", False),
                        "head": {
                            "ref": pull.get("head", {}).get("ref", ""),
                            "sha": short_sha(pull.get("head", {}).get("sha")),
                        },
                        "base": {
                            "ref": pull.get("base", {}).get("ref", ""),
                            "sha": short_sha(pull.get("base", {}).get("sha")),
                        },
                        "created_at": format_datetime(pull.get("created_at")),
                        "updated_at": format_datetime(pull.get("updated_at")),
                    }
                    pulls.append(pull_info)

                if not pulls:
                    yield self.create_text_message(f"No {state} pull requests found in {owner}/{repo}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(pulls, ensure_ascii=False),
                            instruction="Summarize the GitHub pull requests in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
