import json
from collections.abc import Generator
from datetime import datetime
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.errors.model import InvokeError

from .github_api import (
    GITHUB_API_DOMAIN,
    github_request,
    missing_credentials_message,
    missing_parameter_message,
    short_sha,
)


class GithubPullReviewsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        Get reviews on a pull request
        """
        owner = tool_parameters.get("owner", "")
        repo = tool_parameters.get("repo", "")
        pull_number = tool_parameters.get("pull_number")
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

        # Validate token exists and is not empty
        if not access_token or not access_token.strip():
            yield self.create_text_message("❌ GitHub access token is empty or invalid")
            return

        # Validate pull_number can be converted to int
        try:
            pull_number_int = int(pull_number)
        except (ValueError, TypeError):
            yield self.create_text_message(f"❌ Invalid pull_number: {pull_number}. Must be a number.")
            return

        try:
            # First, verify PR exists and get its info
            pr_path = f"/repos/{owner}/{repo}/pulls/{pull_number_int}"
            pr_response = github_request("GET", pr_path, access_token)

            # Check for authentication issues
            if pr_response.status_code == 401:
                yield self.create_text_message(
                    "❌ Authentication failed: Invalid or expired GitHub token\n\n"
                    "Please check your access token is correct and has not expired."
                )
                return
            elif pr_response.status_code == 403:
                try:
                    error_msg = pr_response.json().get("message", "Unknown error")
                except (ValueError, KeyError):
                    error_msg = "Unknown error"
                yield self.create_text_message(
                    f"❌ Access denied: {error_msg}\n\n"
                    f"Your token may not have permission to access this repository.\n"
                    f"For langgenius organization, you may need a fine-grained token."
                )
                return

            if pr_response.status_code != 200:
                yield self.create_text_message(
                    f"❌ Pull request not found: {owner}/{repo}#{pull_number}\n"
                    f"Status: {pr_response.status_code}\n"
                    f"Please verify the owner, repository name, and PR number are correct."
                )
                return

            try:
                pr_info = pr_response.json()
            except (ValueError, KeyError) as e:
                yield self.create_text_message(
                    f"❌ Failed to parse PR response: {str(e)}\n"
                    f"Status: {pr_response.status_code}"
                )
                return

            pr_state = pr_info.get("state", "")
            is_draft = pr_info.get("draft", False)
            is_merged = pr_info.get("merged", False)

            # Now get reviews
            path = f"/repos/{owner}/{repo}/pulls/{pull_number_int}/reviews"
            params = {"per_page": per_page}
            response = github_request("GET", path, access_token, params=params)

            if response.status_code == 200:
                try:
                    reviews_data = response.json()
                except (ValueError, KeyError) as e:
                    yield self.create_text_message(
                        f"❌ Failed to parse reviews response: {str(e)}\n"
                        f"Status: {response.status_code}"
                    )
                    return

                reviews = []
                state_summary = {
                    "APPROVED": 0,
                    "CHANGES_REQUESTED": 0,
                    "COMMENTED": 0,
                    "PENDING": 0,
                    "DISMISSED": 0,
                }

                for review in reviews_data:
                    state = review.get("state", "")
                    if state in state_summary:
                        state_summary[state] += 1

                    # Safely parse submitted_at date
                    submitted_at = ""
                    submitted_at_raw = review.get("submitted_at")
                    if submitted_at_raw:
                        try:
                            submitted_at = datetime.strptime(
                                submitted_at_raw, "%Y-%m-%dT%H:%M:%SZ"
                            ).strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            # If date format doesn't match, use original value
                            submitted_at = submitted_at_raw

                    reviews.append(
                        {
                            "id": review.get("id"),
                            "user": review.get("user", {}).get("login", ""),
                            "state": state,
                            "body": review.get("body", "") or "",
                            "commit_id": short_sha(review.get("commit_id")),
                            "submitted_at": submitted_at,
                            "url": review.get("html_url", ""),
                        }
                    )

                result = {
                    "pr_info": {
                        "number": pull_number,
                        "state": pr_state,
                        "draft": is_draft,
                        "merged": is_merged,
                    },
                    "total_reviews": len(reviews),
                    "state_summary": state_summary,
                    "reviews": reviews,
                }

                # Add a note if PR is draft or merged
                note = ""
                if is_draft:
                    note = "\n\n⚠️ Note: This is a draft PR."
                elif is_merged:
                    note = "\n\n✅ Note: This PR has been merged."
                elif pr_state == "closed":
                    note = "\n\n❌ Note: This PR is closed (not merged)."

                yield self.create_text_message(json.dumps(result, ensure_ascii=False, indent=2) + note)
            elif response.status_code == 404:
                # PR exists but reviews endpoint returns 404 - this is the Classic Token issue
                yield self.create_text_message(
                    f"❌ Classic Token Blocked by Organization - Cannot Access Reviews\n\n"
                    f"PR Information:\n"
                    f"- Repository: {owner}/{repo}\n"
                    f"- PR Number: #{pull_number}\n"
                    f"- Status: {pr_state}\n"
                    f"- Draft: {is_draft}\n"
                    f"- Merged: {is_merged}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔍 Root Cause:\n"
                    f"   The langgenius organization has enabled security policies that block Classic Token access to the reviews endpoint\n"
                    f"   Even if the PR exists and is public, Classic Token will return 404\n\n"
                    f"🔧 Solution:\n"
                    f"   Must use Fine-grained Personal Access Token\n\n"
                    f"📝 Steps to Fix:\n"
                    f"   1. Visit: https://github.com/settings/tokens?type=beta\n"
                    f"   2. Click 'Generate new token'\n"
                    f"   3. Configure permissions:\n"
                    f"      • Repository access: Public Repositories (read-only)\n"
                    f"      • Permissions: Pull requests (Read-only)\n"
                    f"   4. After generating the token, update credentials in the Dify plugin\n\n"
                    f"⚠️ Note: Classic Tokens are being phased out by GitHub, recommend using Fine-grained Tokens for all tools\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"API URL: {GITHUB_API_DOMAIN}{path}"
                )
                return
            else:
                # Include more debug info in error
                yield self.create_text_message(
                    f"❌ Failed to get reviews for {owner}/{repo}#{pull_number}\n"
                    f"URL: {GITHUB_API_DOMAIN}{path}\n"
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text[:500]}"
                )
                return
        except InvokeError as e:
            yield self.create_text_message(f"❌ {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"❌ GitHub API request failed: {e}")
