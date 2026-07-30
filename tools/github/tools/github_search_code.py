import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import (
    github_request,
    missing_credentials_message,
    missing_parameter_message,
    raise_request_error,
    short_sha,
)


class GithubSearchCodeTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        query = tool_parameters.get("query", "")
        per_page = tool_parameters.get("per_page", 10)
        sort = tool_parameters.get("sort", "")
        order = tool_parameters.get("order", "desc")

        parameter_error = missing_parameter_message(tool_parameters, [("query", "search query")])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            path = "/search/code"

            params = {"q": query, "per_page": per_page, "order": order}

            if sort:
                params["sort"] = sort

            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                response_data = response.json()

                total_count = response_data.get("total_count", 0)
                items = response_data.get("items", [])

                search_results = []
                for item in items:
                    result_info = {
                        "name": item.get("name", ""),
                        "path": item.get("path", ""),
                        "sha": short_sha(item.get("sha")),
                        "url": item.get("html_url", ""),
                        "git_url": item.get("git_url", ""),
                        "download_url": item.get("download_url", ""),
                        "score": item.get("score", 0),
                        "repository": {
                            "id": item.get("repository", {}).get("id", 0),
                            "name": item.get("repository", {}).get("name", ""),
                            "full_name": item.get("repository", {}).get("full_name", ""),
                            "url": item.get("repository", {}).get("html_url", ""),
                            "description": item.get("repository", {}).get("description", ""),
                            "language": item.get("repository", {}).get("language", ""),
                            "stars": item.get("repository", {}).get("stargazers_count", 0),
                            "forks": item.get("repository", {}).get("forks_count", 0),
                            "is_private": item.get("repository", {}).get("private", False),
                            "owner": {
                                "login": item.get("repository", {}).get("owner", {}).get("login", ""),
                                "type": item.get("repository", {}).get("owner", {}).get("type", ""),
                            },
                        },
                        "text_matches": [
                            {
                                "fragment": match.get("fragment", ""),
                                "matches": [
                                    {"text": m.get("text", ""), "indices": m.get("indices", [])}
                                    for m in match.get("matches", [])
                                ],
                            }
                            for match in item.get("text_matches", [])
                        ],
                    }
                    search_results.append(result_info)

                result = {"total_count": total_count, "query": query, "results": search_results}

                if not search_results:
                    yield self.create_text_message(f"No code found for query: {query}")
                else:
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(result, ensure_ascii=False),
                            instruction="Summarize the GitHub code search results in a structured format",
                        )
                    )
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"GitHub API request failed: {e}") from e
