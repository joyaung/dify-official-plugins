import hashlib
import hmac
import json
import logging
import time
import traceback
from typing import Mapping
from werkzeug import Request, Response
from dify_plugin import Endpoint
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from markdown_to_mrkdwn import SlackMarkdownConverter

converter = SlackMarkdownConverter()
logger = logging.getLogger(__name__)

SIGNATURE_MAX_AGE_SECONDS = 60 * 5


class SlackEndpoint(Endpoint):
    def _verify_signature(self, r: Request, signing_secret: str) -> bool:
        """
        Verify the Slack request signature as described in
        https://api.slack.com/authentication/verifying-requests-from-slack
        """
        if not signing_secret:
            return False
        timestamp = r.headers.get("X-Slack-Request-Timestamp", "")
        signature = r.headers.get("X-Slack-Signature", "")
        if not timestamp or not signature:
            return False
        try:
            if abs(time.time() - int(timestamp)) > SIGNATURE_MAX_AGE_SECONDS:
                return False
        except ValueError:
            return False
        basestring = b"v0:" + timestamp.encode() + b":" + r.get_data()
        expected = "v0=" + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        if not self._verify_signature(r, settings.get("signing_secret", "")):
            return Response(status=401, response="invalid request signature", content_type="text/plain")
        retry_num = r.headers.get("X-Slack-Retry-Num")
        if (not settings.get("allow_retry") and (r.headers.get("X-Slack-Retry-Reason") == "http_timeout" or ((retry_num is not None and int(retry_num) > 0)))):
            return Response(status=200, response="ok")
        data = r.get_json()

        # Handle Slack URL verification challenge
        if data.get("type") == "url_verification":
            return Response(
                response=json.dumps({"challenge": data.get("challenge")}),
                status=200,
                content_type="application/json"
            )
        
        if (data.get("type") == "event_callback"):
            event = data.get("event")
            if (event.get("type") == "app_mention"):
                message = event.get("text", "")
                if message.startswith("<@"):
                    message = message.split("> ", 1)[1] if "> " in message else message
                    channel = event.get("channel", "")
                    token = settings.get("bot_token")
                    client = WebClient(token=token)
                    try: 
                        response = self.session.app.chat.invoke(
                            app_id=settings["app"]["app_id"],
                            query=message,
                            inputs={},
                            response_mode="blocking",
                        )
                        try:
                            answer = response.get("answer", "")
                            formatted_answer = converter.convert(answer)
                            
                            # Create proper mrkdwn block structure
                            blocks = [{
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": formatted_answer
                                }
                            }]
                            
                            result = client.chat_postMessage(
                                channel=channel,
                                text=formatted_answer,  # Fallback text
                                blocks=blocks,
                                mrkdwn=True
                            )
                            return Response(
                                status=200,
                                response=json.dumps(result),
                                content_type="application/json"
                            )
                        except SlackApiError as e:
                            raise e
                    except Exception:
                        logger.error("Failed to handle Slack app_mention: %s", traceback.format_exc())
                        return Response(
                            status=200,
                            response="Sorry, I'm having trouble processing your request. Please try again later.",
                            content_type="text/plain",
                        )
                else:
                    return Response(status=200, response="ok")
            else:
                return Response(status=200, response="ok")
        else:
            return Response(status=200, response="ok")
