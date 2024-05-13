from typing import Dict, Any
import logging as _logging

from .client import get_client as _get_client
from .config import config


__all__ = ["track", "config"]
__version__ = "0.0.5"

_logger = _logging.getLogger("kanaries_track")

_log_stream_handler = _logging.StreamHandler()
_log_stream_handler.setFormatter(
    _logging.Formatter("%(asctime)s-%(threadName)s-%(levelname)s: %(message)s")
)
_logger.addHandler(_log_stream_handler)


def track(event: Dict[str, Any]):
    """Track event"""
    client = _get_client()
    client.track(event)
