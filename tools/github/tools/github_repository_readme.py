import base64
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import github_request, missing_credentials_message, missing_parameter_message, raise_request_error


class GithubRepositoryReadmeTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        invoke tools
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        ref = tool_parameters.get("ref", "")
        dir_path = tool_parameters.get("dir", "")
        parameter_error = missing_parameter_message(tool_parameters, ["owner", "repo"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)

        access_token = self.runtime.credentials.get("access_tokens")
        try:
            api_path = f"/repos/{owner}/{repo}/readme"
            if dir_path:
                api_path = f"{api_path}/{dir_path}"
            params = {"ref": ref} if ref else None
            response = github_request("GET", api_path, access_token, params=params)
            response_data = response.json()
            if response.status_code == 200:
                if response_data.get("encoding") != "base64":
                    raise InvokeError(
                        f"Can not get base64 encoded readme, response encoding is {response_data.get('encoding')}"
                    )
                content = response_data.get("content")
                if not content:
                    raise InvokeError("README content is empty")
                decoded_bytes = base64.b64decode(content)
                decoded_str = decoded_bytes.decode("utf-8")
                yield self.create_text_message(decoded_str)
            else:
                raise_request_error(response)
        except InvokeError as e:
            raise e
        except Exception as e:
            raise InvokeError(f"Request failed: {e}") from e
