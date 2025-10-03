#!/usr/bin/env python3
"""
Simple smoke test for API routing.

Checks canonical /api/* endpoints and legacy aliases, validating status codes,
content types, and Deprecation headers on legacy paths.

Usage:
  python scripts/smoke_test_api.py --base http://localhost:8000 --timeout 6
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class CheckResult:
    method: str
    path: str
    status: Optional[int]
    content_type: Optional[str]
    deprecated: Optional[bool]
    ok: bool
    error: Optional[str] = None


def http_request(base: str, method: str, path: str, body: Optional[dict], timeout: float) -> CheckResult:
    url = base.rstrip("/") + path
    data_bytes: Optional[bytes] = None
    headers = {"User-Agent": "smoke-test/1.0"}
    if body is not None:
        data_bytes = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get("Content-Type")
            dep = resp.headers.get("Deprecation")
            # Read a small chunk (avoid hanging on streams)
            try:
                resp.read(256)
            except Exception:
                pass
            return CheckResult(
                method=method,
                path=path,
                status=resp.status,
                content_type=ct,
                deprecated=(dep is not None),
                ok=(200 <= resp.status < 400),
            )
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type") if e.headers else None
        dep = e.headers.get("Deprecation") if e.headers else None
        return CheckResult(
            method=method,
            path=path,
            status=e.code,
            content_type=ct,
            deprecated=(dep is not None),
            ok=False,
            error=f"HTTPError {e.code}",
        )
    except Exception as e:
        return CheckResult(
            method=method, path=path, status=None, content_type=None, deprecated=None, ok=False, error=str(e)
        )


def run(base: str, timeout: float) -> int:
    canonical_gets: List[str] = [
        "/api/health",
        "/api/status",
        "/api/rate-limits",
        "/api/db-paths",
        "/api/welcome-questions",
        "/api/default-model",
        "/api/smart-query/status",
        "/api/knowledge/stats",
        "/api/knowledge/sources",
    ]
    canonical_posts: List[Tuple[str, dict]] = [
        ("/api/query", {"question": "hello", "chat_history": []}),
        ("/api/smart-query", {"question": "Who is Nick?", "chat_history": []}),
        ("/api/smart-query/analyze", {"question": "What projects?", "chat_history": []}),
    ]

    legacy_gets: List[str] = [
        "/",
        "/status",
        "/health",
        "/rate-limits",
        "/db-paths",
        "/welcome-questions",
        "/api/public/smart-query/status",
    ]
    legacy_posts: List[Tuple[str, dict]] = [
        ("/query", {"question": "hello", "chat_history": []}),
        ("/api/public/smart-query", {"question": "test", "chat_history": []}),
        ("/api/public/smart-query/analyze", {"question": "test", "chat_history": []}),
    ]

    results: List[CheckResult] = []

    # Canonical GETs
    for path in canonical_gets:
        results.append(http_request(base, "GET", path, None, timeout))

    # Canonical POSTs
    for path, body in canonical_posts:
        results.append(http_request(base, "POST", path, body, timeout))

    # Legacy GETs (expect Deprecation header when 2xx)
    for path in legacy_gets:
        results.append(http_request(base, "GET", path, None, timeout))

    # Legacy POSTs (expect Deprecation header when 2xx)
    for path, body in legacy_posts:
        results.append(http_request(base, "POST", path, body, timeout))

    # Print summary
    print("Method  Status  Deprecated  Content-Type               Path")
    print("------  ------  ----------  -------------------------  -------------------------------")
    failures = 0
    for r in results:
        status = r.status if r.status is not None else "ERR"
        dep = "yes" if r.deprecated else "no"
        ct = (r.content_type or "").split(";")[0][:25]
        print(f"{r.method:<6}  {status!s:<6}  {dep:<10}  {ct:<25}  {r.path}")
        if not r.ok:
            failures += 1

    print()
    print(f"Checks completed: {len(results)}; failures: {failures}")
    return 0 if failures == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000", help="Base URL of the FastAPI server")
    ap.add_argument("--timeout", type=float, default=6.0, help="Per-request timeout in seconds")
    args = ap.parse_args()

    try:
        return run(args.base, args.timeout)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
