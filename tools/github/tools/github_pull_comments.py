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
    short_sha,
)
from .github_error_handler import handle_github_api_error


class GithubPullCommentsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Get comments on a pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        pull_number = tool_parameters.get("pull_number")
        comment_type = tool_parameters.get("comment_type", "all")
        per_page = tool_parameters.get("per_page", 30)

        parameter_error = missing_parameter_message(tool_parameters, ["owner", "repo", "pull_number"])
        if parameter_error:
            yield self.create_text_message(parameter_error)
            return

        credentials_error = missing_credentials_message(self.runtime)
        if credentials_error:
            yield self.create_text_message(credentials_error)
            return

        access_token = self.runtime.credentials.get("access_tokens")

        try:
            result = {"issue_comments": [], "review_comments": []}

            # Get issue comments (general comments on the PR)
            if comment_type in ["all", "issue"]:
                issue_path = f"/repos/{owner}/{repo}/issues/{int(pull_number)}/comments"
                response = github_request("GET", issue_path, access_token, params={"per_page": per_page})

                if response.status_code == 200:
                    for comment in response.json():
                        result["issue_comments"].append({
                            "id": comment.get("id"),
                            "user": comment.get("user", {}).get("login", ""),
                            "body": comment.get("body", ""),
                            "created_at": format_datetime(comment.get("created_at")),
                            "updated_at": format_datetime(comment.get("updated_at")),
                            "url": comment.get("html_url", ""),
                        })
                else:
                    handle_github_api_error(response, f"get issue comments for pull request {owner}/{repo}#{pull_number}")

            # Get review comments (comments on specific lines of code)
            if comment_type in ["all", "review"]:
                review_path = f"/repos/{owner}/{repo}/pulls/{int(pull_number)}/comments"
                response = github_request("GET", review_path, access_token, params={"per_page": per_page})

                if response.status_code == 200:
                    for comment in response.json():
                        result["review_comments"].append({
                            "id": comment.get("id"),
                            "user": comment.get("user", {}).get("login", ""),
                            "body": comment.get("body", ""),
                            "path": comment.get("path", ""),
                            "line": comment.get("line"),
                            "original_line": comment.get("original_line"),
                            "side": comment.get("side", ""),
                            "commit_id": short_sha(comment.get("commit_id")),
                            "in_reply_to_id": comment.get("in_reply_to_id"),
                            "created_at": format_datetime(comment.get("created_at")),
                            "updated_at": format_datetime(comment.get("updated_at")),
                            "url": comment.get("html_url", ""),
                        })
                else:
                    handle_github_api_error(response, f"get review comments for pull request {owner}/{repo}#{pull_number}")

            # Add summary counts
            result["total_issue_comments"] = len(result["issue_comments"])
            result["total_review_comments"] = len(result["review_comments"])

            yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2))

        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
