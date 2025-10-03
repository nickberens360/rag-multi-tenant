#!/usr/bin/env python3
"""
Pre-commit check: forbid legacy config imports.

Fails if any staged file imports backend.core.config or uses
from .config import AppConfig (old pattern). Use backend.core.config_v2 instead.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"\bbackend\.core\.config\b"),
    re.compile(r"^\s*from\s+\.core\.config\s+import\s+AppConfig\b", re.MULTILINE),
    re.compile(r"^\s*from\s+\.\.core\.config\s+import\s+AppConfig\b", re.MULTILINE),
]


def file_has_legacy_import(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    for pat in PATTERNS:
        if pat.search(text):
            return True
    return False


def main(argv: list[str]) -> int:
    # If pre-commit provides a list of files, scan those; otherwise scan repo
    files = [Path(p) for p in argv if Path(p).is_file()]
    if not files:
        # Fallback: scan common code roots
        roots = [Path("backend"), Path("tests"), Path("scripts")]  # scripts included to detect regressions
        files = [p for r in roots for p in r.rglob("*.*") if p.suffix in {".py", ".md"}]

    offenders: list[Path] = []
    for f in files:
        if f.suffix not in {".py", ".md"}:
            continue
        if file_has_legacy_import(f):
            offenders.append(f)

    if offenders:
        print("ERROR: Legacy config import detected. Use backend.core.config_v2 instead.\n")
        for f in offenders:
            print(f" - {f}")
        print("\nTo fix: replace 'backend.core.config' with 'backend.core.config_v2'.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
