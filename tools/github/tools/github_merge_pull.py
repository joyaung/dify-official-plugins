import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import github_request, missing_credentials_message, missing_parameter_message
from .github_error_handler import handle_github_api_error


class GithubMergePullTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Merge a pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        pull_number = tool_parameters.get("pull_number")
        merge_method = tool_parameters.get("merge_method", "merge")
        commit_title = tool_parameters.get("commit_title", "")
        commit_message = tool_parameters.get("commit_message", "")
        sha = tool_parameters.get("sha", "")

        parameter_error = missing_parameter_message(tool_parameters, ["owner", "repo", "pull_number"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        # Validate merge method
        valid_methods = ["merge", "squash", "rebase"]
        if merge_method not in valid_methods:
            yield self.create_text_message(f"Invalid merge_method. Must be one of: {', '.join(valid_methods)}")
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = f"/repos/{owner}/{repo}/pulls/{int(pull_number)}/merge"

            payload = {"merge_method": merge_method}
            if commit_title:
                payload["commit_title"] = commit_title
            if commit_message:
                payload["commit_message"] = commit_message
            if sha:
                payload["sha"] = sha

            response = github_request("PUT", path, access_token, json=payload)

            if response.status_code == 200:
                merge_data = response.json()

                result = {
                    "success": True,
                    "merged": merge_data.get("merged", False),
                    "message": merge_data.get("message", ""),
                    "sha": merge_data.get("sha", ""),
                }

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                handle_github_api_error(response, f"merge pull request {owner}/{repo}#{pull_number}")
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
