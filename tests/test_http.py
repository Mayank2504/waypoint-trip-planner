from __future__ import annotations

import pytest
import requests

from waypoint.http import ExternalServiceError, request_json


class Response:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload if payload is not None else {"ok": True}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class Session:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_request_json_success():
    session = Session([Response(payload={"value": 1})])
    assert request_json("GET", "https://example.test", service="test", session=session) == {
        "value": 1
    }


def test_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("waypoint.http.time.sleep", lambda _: None)
    session = Session([Response(429), Response(payload={"ok": True})])
    result = request_json(
        "GET", "https://example.test", service="test", attempts=2, session=session
    )
    assert result["ok"] is True
    assert len(session.calls) == 2


def test_connection_timeout_retries(monkeypatch):
    monkeypatch.setattr("waypoint.http.time.sleep", lambda _: None)
    session = Session([requests.Timeout("slow"), Response(payload={"ok": True})])
    assert request_json(
        "GET", "https://example.test", service="test", attempts=2, session=session
    )["ok"]


def test_rejected_request_is_not_retried():
    session = Session([Response(403), Response()])
    with pytest.raises(ExternalServiceError) as exc:
        request_json(
            "GET", "https://example.test", service="test", attempts=2, session=session
        )
    assert exc.value.category == "rejected"
    assert len(session.calls) == 1


def test_non_json_shape_rejected():
    session = Session([Response(payload="text")])
    with pytest.raises(ExternalServiceError):
        request_json("GET", "https://example.test", service="test", session=session)
