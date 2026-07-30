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


class GithubRepositoryCommitsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        per_page = tool_parameters.get("per_page", 10)
        sha = tool_parameters.get("sha", "")
        path = tool_parameters.get("path", "")

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
            path = f"/repos/{owner}/{repo}/commits"

            params = {"per_page": per_page}

            if sha:
                params["sha"] = sha
            if path:
                params["path"] = path

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                commits = []
                for commit in response_data:
                    commit_info = {
                        "sha": short_sha(commit.get("sha")),
                        "full_sha": commit.get("sha", ""),
                        "message": commit.get("commit", {}).get("message", ""),
                        "author": {
                            "name": commit.get("commit", {}).get("author", {}).get("name", ""),
                            "email": commit.get("commit", {}).get("author", {}).get("email", ""),
                            "date": format_datetime(commit.get("commit", {}).get("author", {}).get("date")),
                        },
                        "committer": {
                            "name": commit.get("commit", {}).get("committer", {}).get("name", ""),
                            "email": commit.get("commit", {}).get("committer", {}).get("email", ""),
                            "date": format_datetime(commit.get("commit", {}).get("committer", {}).get("date")),
                        },
                        "url": commit.get("html_url", ""),
                        "comment_count": commit.get("commit", {}).get("comment_count", 0),
                        "verification": {
                            "verified": commit.get("commit", {}).get("verification", {}).get("verified", False),
                            "reason": commit.get("commit", {}).get("verification", {}).get("reason", ""),
                        },
                        "stats": {
                            "additions": commit.get("stats", {}).get("additions", 0),
                            "deletions": commit.get("stats", {}).get("deletions", 0),
                            "total": commit.get("stats", {}).get("total", 0),
                        }
                        if commit.get("stats")
                        else {},
                        "files_changed": len(commit.get("files", [])) if commit.get("files") else 0,
                    }
                    commits.append(commit_info)

                if not commits:
                    yield self.create_text_message(f"No commits found in {owner}/{repo}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(commits, ensure_ascii=False),
                            instruction="Summarize the GitHub commits in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
