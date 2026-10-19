"""Emit minimal JSON events without request bodies or identity fields."""

import json
import logging
import sys
from contextvars import ContextVar
from uuid import uuid4

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
# JSON route-template events replace access logs that include raw URLs.
logging.getLogger("uvicorn.access").disabled = True
event_logger = logging.getLogger("paireval.events")
if not event_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    event_logger.addHandler(handler)
event_logger.setLevel(logging.INFO)
event_logger.propagate = False

SAFE_FIELDS = {"method", "path", "statusCode", "duration_ms", "assignment_id", "section", "changed_count"}


def log_event(event: str, **fields: object) -> None:
    data = {"event": event, "requestId": request_id.get() or str(uuid4())}
    data.update({key: value for key, value in fields.items() if key in SAFE_FIELDS})
    event_logger.info(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
