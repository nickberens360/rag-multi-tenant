#!/usr/bin/env python3
"""
In-process smoke test using FastAPI TestClient (no external server required).

Validates canonical /api/* endpoints and legacy aliases, and reports status
codes plus presence of Deprecation headers on legacy paths.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from starlette.testclient import TestClient


def main() -> int:
    # Ensure project root is on sys.path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Import the FastAPI app
    from backend.main import app

    client = TestClient(app)

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

    results = []

    # Canonical
    for path in canonical_gets:
        r = client.get(path)
        results.append(("GET", path, r.status_code, r.headers.get("Deprecation")))
    for path, body in canonical_posts:
        r = client.post(path, json=body)
        results.append(("POST", path, r.status_code, r.headers.get("Deprecation")))

    # Legacy
    for path in legacy_gets:
        r = client.get(path)
        results.append(("GET", path, r.status_code, r.headers.get("Deprecation")))
    for path, body in legacy_posts:
        r = client.post(path, json=body)
        results.append(("POST", path, r.status_code, r.headers.get("Deprecation")))

    print("Method  Status  Deprecated  Path")
    print("------  ------  ----------  -------------------------------")
    failures = 0
    for method, path, status, dep in results:
        depv = "yes" if dep else "no"
        print(f"{method:<6}  {status:<6}  {depv:<10}  {path}")
        # Treat 2xx/3xx as pass; others as failures
        if not (200 <= status < 400):
            failures += 1

    print()
    print(f"Checks completed: {len(results)}; failures: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
