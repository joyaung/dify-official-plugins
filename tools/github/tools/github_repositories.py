import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities import I18nObject, ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage

from .github_api import (
    DISPLAY_DATE_FORMAT,
    format_datetime,
    github_request,
    missing_credentials_message,
    missing_parameter_message,
)


class GithubRepositoriesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        top_n = tool_parameters.get("top_n", 5)
        query = tool_parameters.get("query", "")
        parameter_error = missing_parameter_message(tool_parameters, [("query", "symbol")])
        if parameter_error:
            yield self.create_text_message(parameter_error)

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            response = github_request(
                "GET",
                "/search/repositories",
                access_token,
                params={"q": query, "sort": "stars", "per_page": top_n, "order": "desc"},
            )
            response_data = response.json()
            if response.status_code == 200 and isinstance(response_data.get("items"), list):
                contents = []
                if len(response_data.get("items")) > 0:
                    for item in response_data.get("items"):
                        content = {}
                        content["owner"] = item["owner"]["login"]
                        content["name"] = item["name"]
                        if item["description"] is not None:
                            content["description"] = (
                                item["description"][:100] + "..."
                                if len(item["description"]) > 100
                                else item["description"]
                            )
                        else:
                            content["description"] = ""
                        content["url"] = item["html_url"]
                        content["star"] = item["watchers"]
                        content["forks"] = item["forks"]
                        content["updated"] = format_datetime(item["updated_at"], DISPLAY_DATE_FORMAT)
                        contents.append(content)
                    yield self.create_text_message(
                        self.session.model.summary.invoke(
                            text=json.dumps(contents, ensure_ascii=False),
                            instruction="Summarize the text",
                        )
                    )
                else:
                    yield self.create_text_message(f"No items related to {query} were found.")
            else:
                yield self.create_text_message(response.json().get("message"))
        except Exception as e:
            yield self.create_text_message(f"GitHub API Key and Api Version is invalid. {e}")

    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        return [
            ParameterOption(
                value="iamjoel",
                label=I18nObject(en_US="Joel"),
                icon="https://avatars.githubusercontent.com/u/2120155?s=40&v=4",
            ),
            ParameterOption(
                value="yeuoly",
                label=I18nObject(en_US="Yeuoly"),
                icon="https://avatars.githubusercontent.com/u/45712896?s=60&v=4",
            ),
        ]
