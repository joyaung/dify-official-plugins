import hmac
from collections.abc import Mapping
from werkzeug import Request


class BaseAuth:
    def verify(self, r: Request, settings: Mapping) -> bool:
        api_key = settings.get("api_key")
        if not api_key:
            return False
        authorization = r.headers.get("Authorization") or ""
        return hmac.compare_digest(authorization, f"Bearer {api_key}") or hmac.compare_digest(
            authorization, str(api_key)
        )
