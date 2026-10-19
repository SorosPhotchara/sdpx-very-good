"""Request logs use route templates and never include user supplied secrets."""

import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.observability import event_logger, log_event


def test_request_log_omits_query_and_untrusted_request_id() -> None:
    with patch.object(event_logger, "info") as write:
        response = TestClient(app).get(
            "/assignments/12/report?email=private@example.edu",
            headers={"x-request-id": "token-secret"},
        )
    assert response.status_code == 401
    entry = json.loads(write.call_args.args[0])
    assert entry["path"] == "/assignments/{assignment_id}/report"
    assert entry["requestId"] == response.headers["x-request-id"]
    assert "private@example.edu" not in write.call_args.args[0]
    assert "token-secret" not in write.call_args.args[0]


def test_business_event_filters_sensitive_fields() -> None:
    with patch.object(event_logger, "info") as write:
        log_event("evaluation_draft_saved", assignment_id=3, email="private@example.edu", token="secret")
    entry = json.loads(write.call_args.args[0])
    assert entry["assignment_id"] == 3
    assert "email" not in entry and "token" not in entry
