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


class GithubUserReposTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        username = tool_parameters.get("username", "")
        per_page = tool_parameters.get("per_page", 10)
        sort = tool_parameters.get("sort", "updated")
        direction = tool_parameters.get("direction", "desc")
        type = tool_parameters.get("type", "all")  # noqa: A001

        parameter_error = missing_parameter_message(tool_parameters, ["username"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/users/{username}/repos"

            params = {"per_page": per_page, "sort": sort, "direction": direction, "type": type}

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                repos = []
                for repo in response_data:
                    repo_info = {
                        "id": repo.get("id", 0),
                        "name": repo.get("name", ""),
                        "full_name": repo.get("full_name", ""),
                        "description": repo.get("description", ""),
                        "url": repo.get("html_url", ""),
                        "clone_url": repo.get("clone_url", ""),
                        "ssh_url": repo.get("ssh_url", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "watchers": repo.get("watchers_count", 0),
                        "open_issues": repo.get("open_issues_count", 0),
                        "size": repo.get("size", 0),
                        "default_branch": repo.get("default_branch", ""),
                        "is_private": repo.get("private", False),
                        "is_fork": repo.get("fork", False),
                        "is_archived": repo.get("archived", False),
                        "license": repo.get("license", {}).get("name", "") if repo.get("license") else "",
                        "created_at": format_datetime(repo.get("created_at")),
                        "updated_at": format_datetime(repo.get("updated_at")),
                        "pushed_at": format_datetime(repo.get("pushed_at")),
                        "topics": repo.get("topics", []),
                    }
                    repos.append(repo_info)

                if not repos:
                    yield self.create_text_message(f"No repositories found for user {username}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(repos, ensure_ascii=False),
                            instruction="Summarize the GitHub user repositories in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
