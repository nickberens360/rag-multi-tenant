from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document

from backend.ingest.chunking import splitter_for_ext
from backend.ingest.loaders import load_doc


def tokenize(text: str) -> List[str]:
    import re

    words = re.findall(r"\b[a-z]{4,}\b", text.lower())
    stop = {
        "this",
        "that",
        "with",
        "from",
        "they",
        "were",
        "been",
        "have",
        "will",
        "would",
        "could",
        "about",
        "there",
        "their",
        "which",
        "these",
        "those",
        "into",
        "your",
        "also",
        "some",
        "more",
        "such",
        "like",
        "when",
        "what",
        "where",
        "them",
    }
    return [w for w in words if w not in stop]


def topk(tokens: List[str], k: int = 20) -> List[str]:
    freq: Dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:k]]


def heterogeneity_metrics(chunks: List[Document]) -> Tuple[float, float, int]:
    """Compute (avg_jaccard, frac_low, n_chunks) using the same heuristic as the indexer."""
    if not chunks:
        return (1.0, 0.0, 0)

    chunk_sets: List[set[str]] = []
    all_tokens: List[str] = []
    for c in chunks:
        tks = tokenize(c.page_content or "")
        s = set(topk(tks))
        chunk_sets.append(s)
        all_tokens.extend(tks)

    file_set = set(topk(all_tokens, k=40))
    if not file_set:
        return (1.0, 0.0, len(chunks))

    def jaccard(a: set[str], b: set[str]) -> float:
        if not a and not b:
            return 1.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    sims = [jaccard(s, file_set) for s in chunk_sets]
    avg_sim = sum(sims) / len(sims)
    low_count = sum(1 for s in sims if s < 0.25)  # per-chunk threshold default
    frac_low = low_count / len(sims)
    return (avg_sim, frac_low, len(chunks))


def scan_directory(directory: Path) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        # Skip dotfiles and images/binaries (loader handles some)
        if file_path.name.startswith("."):
            continue

        docs = load_doc(file_path)
        if not docs:
            continue

        splitter = splitter_for_ext(file_path.suffix)
        chunks = splitter.split_documents(docs)
        avg_sim, frac_low, n_chunks = heterogeneity_metrics(chunks)
        is_mixed = (avg_sim < 0.35) and (frac_low >= 0.5)  # defaults from indexer

        results.append(
            {
                "file": str(file_path),
                "chunks": n_chunks,
                "avg_jaccard": round(avg_sim, 3),
                "frac_low": round(frac_low, 3),
                "mixed_topic": bool(is_mixed),
            }
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Report files that appear mixed-topic based on token similarity.")
    ap.add_argument("--dir", required=True, help="Directory to scan (recursively)")
    args = ap.parse_args()

    directory = Path(args.dir)
    if not directory.exists():
        print(json.dumps({"error": f"Directory not found: {directory}"}))
        return 1

    results = scan_directory(directory)
    mixed = [r for r in results if r["mixed_topic"]]
    report = {
        "directory": str(directory),
        "files_scanned": len(results),
        "mixed_count": len(mixed),
        "mixed_files": sorted(mixed, key=lambda r: (r["avg_jaccard"], -r["chunks"]))[:200],
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
