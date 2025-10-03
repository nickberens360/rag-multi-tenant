from pathlib import Path

import pytest

from backend.core.content_indexer import ContentIndexer


@pytest.mark.unit
def test_include_list_forces_per_chunk_llm(tmp_path: Path, monkeypatch):
    # Create a small markdown file that would not be heterogeneous by thresholds
    d = tmp_path / "data"
    d.mkdir()
    fp = d / "simple.md"
    fp.write_text("# Title\n\nAlpha beta gamma delta.\n\n## Sub\n\nAlpha beta gamma delta.")

    # Dummy LLM
    idx = ContentIndexer(object(), persist_dir=str(tmp_path / ".unified_chroma"), classification_mode="hybrid")

    # Disable heuristic fallback, but include the path to force per-chunk
    idx.enable_heterogeneity_fallback = False
    idx._hetero_include_globs = [str(fp)]

    calls = {"count": 0}

    def fake_classify(doc, file_path):
        calls["count"] += 1
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": "general",
            "content_types": "general",
            "content_keywords": "test",
            "topic_confidence": 0.9,
            "classification_method": "startup_llm",
            "is_illustration_data": False,
        }

    assert idx.startup_classifier is not None
    monkeypatch.setattr(idx.startup_classifier, "classify_content_with_llm", fake_classify)

    _, files, chunks = idx.process_directory(str(d), force_reindex=True)

    assert files == 1
    # Per-chunk classification should be enforced: 1 per chunk + initial file-level if used
    # For our include logic we don't skip file-level classification precompute; so calls >= chunks
    assert calls["count"] >= chunks
    # And metrics should record chunk-level fallbacks
    assert idx.get_metrics().get("llm_classifications_fallback_chunk", 0) == chunks
