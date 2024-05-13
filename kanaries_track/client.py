from typing import Dict, Any
from datetime import datetime
from threading import Thread
from functools import lru_cache
import queue
import uuid
import logging
import time
import atexit

from dateutil.tz import tzlocal

from .config import config
from .request import RequestClient


logger = logging.getLogger("kanaries_track")


class _Consumer(Thread):
    def __init__(
        self,
        *,
        event_queue: queue.Queue,
        request_client: RequestClient,
        upload_size: int,
        upload_interval_seconds: int
    ) -> None:
        super().__init__()
        self.event_queue = event_queue
        self.request_client = request_client
        self.upload_size = upload_size
        self.upload_interval_seconds = upload_interval_seconds
        self.daemon = True
        self.ruuning = True

    def run(self):
        """Run the consumer"""
        logger.debug("Consumer started")
        while self.ruuning:
            self._upload()
        logger.debug("Consumer stopped")

    def pause(self):
        """Pause the consumer"""
        self.ruuning = False

    def _upload(self):
        """Upload events"""
        start_time = time.monotonic()
        events = []
        while len(events) < self.upload_size:
            elapsed_seconds = time.monotonic() - start_time
            if elapsed_seconds >= self.upload_interval_seconds:
                break
            try:
                event = self.event_queue.get(block=True, timeout=self.upload_interval_seconds - elapsed_seconds)
                events.append(event)
            except queue.Empty:
                break
            except Exception as e:
                logger.debug("Failed to get event from queue: %s", str(e))

        logger.debug("invoke uploading events, event count: %s", len(events))
        if events:
            self.request_client.track(events)


class Client:
    """Client for sending events to kanaries-track server"""
    def __init__(
        self,
        *,
        host: str,
        auth_token: str,
        debug: bool,
        send: bool,
        sync_send: bool,
        max_queue_size: int,
        timeout_seconds: int,
        max_retries: int,
        proxies: Dict[str, Any],
        thread_count: int,
        verify: bool,
        upload_interval_seconds: int,
        upload_size: int
    ):
        self.host = host
        self.auth_token = auth_token
        self.debug = debug
        self.send = send
        self.sync_send = sync_send
        self.max_queue_size = max_queue_size
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.proxies = proxies
        self.thread_count = thread_count
        self.verify = verify
        self.upload_interval_seconds = upload_interval_seconds
        self.upload_size = upload_size

        self._consumers = []
        self._request_client = RequestClient(
            host=self.host,
            auth_token=self.auth_token,
            max_retries=self.max_retries,
            timeout=self.timeout_seconds,
            verify=self.verify,
            proxy=self.proxies
        )
        self._event_queue = queue.Queue(self.max_queue_size)

        if not self.sync_send and self.send:
            for _ in range(self.thread_count):
                consumer = _Consumer(
                    event_queue=self._event_queue,
                    request_client=self._request_client,
                    upload_size=self.upload_size,
                    upload_interval_seconds=self.upload_interval_seconds
                )
                consumer.start()
                self._consumers.append(consumer)

        atexit.register(self._end)

        if self.debug:
            logger.setLevel(logging.DEBUG)

    def track(self, event: Dict[str, Any]):
        """Track an event"""
        event = self._fill_data(event)

        if not self.send:
            return

        if self.sync_send:
            self._request_client.track([event])
        else:
            self._enqueue(event)

    def _fill_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Fill data for an event"""
        event["timestamp"] = datetime.now().replace(tzinfo=tzlocal()).isoformat()
        event["message_id"] = str(uuid.uuid4())
        return event

    def _enqueue(self, event: Dict[str, Any]):
        """Enqueue an event"""
        logger.debug("enqueue event: %s", event)
        try:
            self._event_queue.put(event, block=False)
        except queue.Full:
            logger.warning("Event queue is full, dropping event")

    def _end(self):
        """End the client when the main thread exits"""
        for consumer in self._consumers:
            consumer.pause()
            consumer.join()


@lru_cache(maxsize=1)
def get_client():
    """Get a client"""
    return Client(
        host=config.host,
        auth_token=config.auth_token,
        debug=config.debug,
        send=config.send,
        sync_send=config.sync_send,
        max_queue_size=config.max_queue_size,
        timeout_seconds=config.timeout,
        max_retries=config.max_retries,
        proxies=config.proxies,
        thread_count=config.thread,
        verify=config.verify,
        upload_interval_seconds=config.upload_interval,
        upload_size=config.upload_size
    )
