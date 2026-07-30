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


class GithubUserInfoTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        username = tool_parameters.get("username", "")

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
            path = f"/users/{username}"

            response = github_request("GET", path, access_token)

            if response.status_code == 200:
                response_data = response.json()

                user_info = {
                    "login": response_data.get("login", ""),
                    "id": response_data.get("id", 0),
                    "name": response_data.get("name", ""),
                    "company": response_data.get("company", ""),
                    "blog": response_data.get("blog", ""),
                    "location": response_data.get("location", ""),
                    "email": response_data.get("email", ""),
                    "bio": response_data.get("bio", ""),
                    "twitter_username": response_data.get("twitter_username", ""),
                    "avatar_url": response_data.get("avatar_url", ""),
                    "url": response_data.get("html_url", ""),
                    "type": response_data.get("type", ""),
                    "site_admin": response_data.get("site_admin", False),
                    "public_repos": response_data.get("public_repos", 0),
                    "public_gists": response_data.get("public_gists", 0),
                    "followers": response_data.get("followers", 0),
                    "following": response_data.get("following", 0),
                    "created_at": format_datetime(response_data.get("created_at")),
                    "updated_at": format_datetime(response_data.get("updated_at")),
                    "hireable": response_data.get("hireable", None),
                    "gravatar_id": response_data.get("gravatar_id", ""),
                }

                yield self.create_text_message(
                    self.session.model.summary.invoke(
                        text=json.dumps(user_info, ensure_ascii=False),
                        instruction="Summarize the GitHub user information in a structured format",
                    )
                )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
