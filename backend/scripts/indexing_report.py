from __future__ import annotations

import argparse
import json
import os

from backend.core.app_initializer_v2 import create_processing_llm
from backend.core.content_indexer import ContentIndexer


def main() -> int:
    parser = argparse.ArgumentParser(description="Run indexing for a directory and print LLM usage metrics.")
    parser.add_argument("--dir", dest="directory", required=True, help="Directory to index (recursively)")
    parser.add_argument("--force", action="store_true", help="Force reindex even if unchanged")
    parser.add_argument(
        "--hetero",
        action="store_true",
        help="Enable heterogeneity detection with selective per-chunk LLM fallback",
    )
    parser.add_argument(
        "--persist-dir",
        default="backend/.unified_chroma",
        help="Directory to store index metadata (default: backend/.unified_chroma)",
    )
    args = parser.parse_args()

    # Create processing LLM using app defaults (Claude Haiku or configured)
    llm = create_processing_llm()

    indexer = ContentIndexer(llm, persist_dir=args.persist_dir, classification_mode="hybrid")
    if args.hetero:
        indexer.enable_heterogeneity_fallback = True
        os.environ["ENABLE_HETEROGENEITY_FALLBACK"] = "true"

    docs, files_processed, total_chunks = indexer.process_directory(args.directory, force_reindex=args.force)

    metrics = indexer.get_metrics()
    report = {
        "directory": str(args.directory),
        "files_processed": files_processed,
        "chunks_generated": total_chunks,
        "llm_classifications_performed": metrics.get("llm_classifications_performed", 0),
        "llm_classifications_fallback_chunk": metrics.get("llm_classifications_fallback_chunk", 0),
        "persist_dir": args.persist_dir,
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
