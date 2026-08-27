"""Bounded, retrying HTTP helpers for public data providers."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional, Tuple

import requests


@dataclass
class ExternalServiceError(RuntimeError):
    service: str
    category: str
    message: str
    status_code: Optional[int] = None

    def __str__(self) -> str:
        status = f" (HTTP {self.status_code})" if self.status_code else ""
        return f"{self.service} {self.category}{status}: {self.message}"


_SESSION = requests.Session()
RETRY_STATUSES = {429, 500, 502, 503, 504}


def _retry_delay(response: Optional[requests.Response], attempt: int) -> float:
    if response is not None:
        raw = response.headers.get("Retry-After", "").strip()
        if raw:
            try:
                return min(float(raw), 30.0)
            except ValueError:
                try:
                    parsed = parsedate_to_datetime(raw).timestamp() - time.time()
                    return max(0.0, min(parsed, 30.0))
                except Exception:
                    pass
    return min(0.5 * (2**attempt) + random.uniform(0.0, 0.2), 5.0)


def request_json(
    method: str,
    url: str,
    *,
    service: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Tuple[float, float] = (5.0, 20.0),
    attempts: int = 3,
    deadline: Optional[float] = None,
    session: Optional[requests.Session] = None,
) -> Any:
    client = session or _SESSION
    last_error: Optional[ExternalServiceError] = None
    for attempt in range(max(1, attempts)):
        if deadline is not None and time.monotonic() >= deadline:
            raise ExternalServiceError(service, "timeout", "operation deadline exceeded")
        response: Optional[requests.Response] = None
        try:
            response = client.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                timeout=timeout,
            )
            if response.status_code in RETRY_STATUSES:
                last_error = ExternalServiceError(
                    service,
                    "rate-limited" if response.status_code == 429 else "unavailable",
                    "temporary provider failure",
                    response.status_code,
                )
                if attempt + 1 < attempts:
                    time.sleep(_retry_delay(response, attempt))
                    continue
                raise last_error
            if response.status_code in {401, 403, 406}:
                raise ExternalServiceError(
                    service,
                    "rejected",
                    "request identification or authorization was rejected",
                    response.status_code,
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise ExternalServiceError(service, "malformed-response", "expected JSON data")
            return payload
        except ExternalServiceError:
            raise
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = ExternalServiceError(service, "timeout", str(exc))
            if attempt + 1 < attempts:
                time.sleep(_retry_delay(response, attempt))
                continue
        except (requests.RequestException, ValueError) as exc:
            raise ExternalServiceError(service, "request-failed", str(exc)) from exc
    raise last_error or ExternalServiceError(service, "request-failed", "unknown failure")
