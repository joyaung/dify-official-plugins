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


class GithubRepositoryInfoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")

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
            path = f"/repos/{owner}/{repo}"

            response = github_request("GET", path, access_token)

            if response.status_code == 200:
                response_data = response.json()

                # Extract key information
                repo_info = {
                    "name": response_data.get("name", ""),
                    "full_name": response_data.get("full_name", ""),
                    "description": response_data.get("description", ""),
                    "url": response_data.get("html_url", ""),
                    "clone_url": response_data.get("clone_url", ""),
                    "ssh_url": response_data.get("ssh_url", ""),
                    "language": response_data.get("language", ""),
                    "stars": response_data.get("stargazers_count", 0),
                    "forks": response_data.get("forks_count", 0),
                    "watchers": response_data.get("watchers_count", 0),
                    "open_issues": response_data.get("open_issues_count", 0),
                    "size": response_data.get("size", 0),
                    "default_branch": response_data.get("default_branch", ""),
                    "is_private": response_data.get("private", False),
                    "is_fork": response_data.get("fork", False),
                    "is_archived": response_data.get("archived", False),
                    "license": response_data.get("license", {}).get("name", "") if response_data.get("license") else "",
                    "created_at": format_datetime(response_data.get("created_at")),
                    "updated_at": format_datetime(response_data.get("updated_at")),
                    "pushed_at": format_datetime(response_data.get("pushed_at")),
                    "topics": response_data.get("topics", []),
                    "owner": {
                        "login": response_data.get("owner", {}).get("login", ""),
                        "type": response_data.get("owner", {}).get("type", ""),
                        "url": response_data.get("owner", {}).get("html_url", ""),
                    },
                }

                yield self.create_text_message(
                    self.session.model.summary.invoke(
                        text=json.dumps(repo_info, ensure_ascii=False),
                        instruction="Summarize the repository information in a structured format",
                    )
                )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
