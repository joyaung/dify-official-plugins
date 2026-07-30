import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import github_request, missing_credentials_message, missing_parameter_message, raise_request_error


class GithubRepositoryContributorsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        per_page = tool_parameters.get("per_page", 10)

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
            path = f"/repos/{owner}/{repo}/contributors"

            params = {"per_page": per_page}

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                contributors = []
                for contributor in response_data:
                    contributor_info = {
                        "login": contributor.get("login", ""),
                        "id": contributor.get("id", 0),
                        "avatar_url": contributor.get("avatar_url", ""),
                        "url": contributor.get("html_url", ""),
                        "contributions": contributor.get("contributions", 0),
                        "type": contributor.get("type", ""),
                        "site_admin": contributor.get("site_admin", False),
                    }
                    contributors.append(contributor_info)

                if not contributors:
                    yield self.create_text_message(f"No contributors found in {owner}/{repo}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(contributors, ensure_ascii=False),
                            instruction="Summarize the GitHub contributors in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
