from typing import Dict, List, Any
import logging

from requests import Session, Response
import backoff

logger = logging.getLogger("kanaries_track")


class RequestClient:
    """Client for sending events to kanaries-track server"""
    def __init__(
        self,
        *,
        host: str,
        auth_token: str,
        max_retries: int,
        timeout: int,
        verify: bool,
        proxy: Any
    ) -> None:
        self.host = host
        self.auth_token = auth_token
        self.max_retries = max_retries
        self.timeout = timeout
        self.verify = verify
        self.proxy = proxy
        self.session = Session()

    def _post(self, path: str, data: Dict[str, Any]) -> Response:
        """Post data to url"""
        url = f"{self.host}{path}"

        @backoff.on_exception(
            backoff.expo,
            Exception,
            max_tries=self.max_retries,
        )
        def __post():
            return self.session.post(
                url,
                headers={"Track-Key": self.auth_token},
                json=data,
                timeout=self.timeout,
                verify=self.verify,
                proxies=self.proxy
            )

        return __post()

    def track(self, events: List[Dict[str, Any]]):
        """Send events to kanaries-track server"""
        logger.debug("send requests to server, event count: %s", len(events))
        try:
            resp = self._post("/ingest/track", events)
            logger.debug("track resp: %s", resp.text)
        except Exception as e:
            logger.debug("Failed to send events to server: %s", str(e))
