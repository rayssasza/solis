import hashlib
import hmac
import base64
import json
import logging
from email.utils import formatdate
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SolisAuth:
    CONTENT_TYPE = "application/json"

    def __init__(self, api_id: str, api_secret: str):
        self.api_id = api_id
        self._api_secret = api_secret.encode("utf-8")

    def _md5_base64(self, body_bytes: bytes) -> str:
        md5_digest = hashlib.md5(body_bytes).digest()
        return base64.b64encode(md5_digest).decode("utf-8")

    def _gmt_date(self) -> str:
        return formatdate(usegmt=True)

    def _sign(self, string_to_sign: str) -> str:
        mac = hmac.new(
            self._api_secret,
            msg=string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha1,
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    def build_headers(
        self,
        method: str,
        endpoint: str,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, str]:
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        body_bytes = body_str.encode("utf-8")

        content_md5 = self._md5_base64(body_bytes)
        date_str = self._gmt_date()

        string_to_sign = "\n".join([
            method.upper(),
            content_md5,
            self.CONTENT_TYPE,
            date_str,
            endpoint,
        ])

        signature = self._sign(string_to_sign)
        authorization = f"API {self.api_id}:{signature}"

        headers = {
            "Content-MD5": content_md5,
            "Content-Type": self.CONTENT_TYPE,
            "Date": date_str,
            "Authorization": authorization,
        }

        logger.debug(
            "Headers gerados | endpoint=%s | method=%s | Date=%s",
            endpoint,
            method,
            date_str,
        )
        return headers
