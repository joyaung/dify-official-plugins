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


class GithubRepositoryReleasesTool(Tool):
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
            path = f"/repos/{owner}/{repo}/releases"

            params = {"per_page": per_page}

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                releases = []
                for release in response_data:
                    release_info = {
                        "id": release.get("id", 0),
                        "tag_name": release.get("tag_name", ""),
                        "name": release.get("name", ""),
                        "body": (release.get("body", "") or "")[:300] + "..."
                        if len(release.get("body", "") or "") > 300
                        else (release.get("body", "") or ""),
                        "url": release.get("html_url", ""),
                        "tarball_url": release.get("tarball_url", ""),
                        "zipball_url": release.get("zipball_url", ""),
                        "author": release.get("author", {}).get("login", ""),
                        "draft": release.get("draft", False),
                        "prerelease": release.get("prerelease", False),
                        "assets": [
                            {
                                "name": asset.get("name", ""),
                                "size": asset.get("size", 0),
                                "download_count": asset.get("download_count", 0),
                                "download_url": asset.get("browser_download_url", ""),
                            }
                            for asset in release.get("assets", [])
                        ],
                        "created_at": format_datetime(release.get("created_at")),
                        "published_at": format_datetime(release.get("published_at")),
                    }
                    releases.append(release_info)

                if not releases:
                    yield self.create_text_message(f"No releases found in {owner}/{repo}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(releases, ensure_ascii=False),
                            instruction="Summarize the GitHub releases in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
