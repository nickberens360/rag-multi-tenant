from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(reason="Disabled to avoid Chroma initialization conflicts in CI")

from backend.core.content_indexer import ContentIndexer
from backend.core.unified_retriever import UnifiedRetriever


def _write_text(path: Path, blocks: list[str]) -> None:
    path.write_text("\n\n".join(blocks), encoding="utf-8")


@pytest.mark.unit
def test_heterogeneity_fallback_process_directory(tmp_path: Path, isolated_chroma_dir: str, mock_llm, monkeypatch):
    # Create a heterogeneous .txt file large enough to split into multiple chunks
    d = tmp_path / "data"
    d.mkdir()
    art_block = ("illustration design gallery creative portfolio art drawing painting ") * 80
    tech_block = ("programming software python javascript typescript database api microservice ") * 80
    resume_block = ("experience company role manager director product leadership startup ") * 80
    fp = d / "mixed.txt"
    _write_text(fp, [art_block, tech_block, resume_block])

    indexer = ContentIndexer(mock_llm, persist_dir=isolated_chroma_dir, classification_mode="hybrid")
    indexer.enable_heterogeneity_fallback = True  # turn on Phase 2
    # Loosen thresholds to ensure detection in test
    indexer._heterogeneity_threshold = 0.6
    indexer._heterogeneity_per_chunk_threshold = 0.5
    indexer._heterogeneity_chunk_fraction = 0.3

    calls = {"count": 0}

    def fake_classify(doc, file_path):
        calls["count"] += 1
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": "skills,project",
            "content_types": "skills,project",
            "content_keywords": "python",
            "topic_confidence": 0.9,
            "classification_method": "startup_llm",
            "is_illustration_data": False,
        }

    assert indexer.startup_classifier is not None
    monkeypatch.setattr(indexer.startup_classifier, "classify_content_with_llm", fake_classify)

    docs, files_processed, total_chunks = indexer.process_directory(str(d), force_reindex=True)

    assert files_processed == 1
    assert total_chunks == len(docs)
    # One file-level classification + one per chunk due to fallback
    assert calls["count"] == 1 + total_chunks
    assert indexer._metrics.get("llm_classifications_performed") == 1
    assert indexer._metrics.get("llm_classifications_fallback_chunk") == total_chunks
    # Check metadata present
    for i, doc in enumerate(docs):
        md = doc.metadata
        assert md.get("chunk_index") == i
        assert md.get("chunk_id")
        assert md.get("classification_method") == "startup_llm"


@pytest.mark.unit
def test_heterogeneity_fallback_reindex_file(
    tmp_path: Path, isolated_chroma_dir: str, mock_embeddings, mock_llm, monkeypatch
):
    # Prepare a heterogeneous .txt file
    d = tmp_path / "data"
    d.mkdir()
    a = ("art design creative portfolio illustration ") * 300
    b = ("python code api database microservice ") * 300
    fp = d / "mixed.txt"
    _write_text(fp, [a, b])

    ur = UnifiedRetriever(embeddings=mock_embeddings, llm=mock_llm, persist_dir=isolated_chroma_dir)

    # Enable Phase 2 and stub vector store
    ur.content_indexer.enable_heterogeneity_fallback = True
    ur.content_indexer._heterogeneity_threshold = 0.6
    ur.content_indexer._heterogeneity_per_chunk_threshold = 0.55
    ur.content_indexer._heterogeneity_chunk_fraction = 0.3

    class NoOpSemantic:
        def delete_where(self, where):
            return None

        def add_documents(self, documents):
            self._added = len(documents)

    ur.semantic_searcher = NoOpSemantic()

    calls = {"count": 0}

    def fake_classify(doc, file_path):
        calls["count"] += 1
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": "skills",
            "content_types": "skills",
            "content_keywords": "python",
            "topic_confidence": 0.95,
            "classification_method": "startup_llm",
            "is_illustration_data": False,
        }

    assert ur.content_indexer.startup_classifier is not None
    monkeypatch.setattr(ur.content_indexer.startup_classifier, "classify_content_with_llm", fake_classify)

    ok = ur.reindex_file(str(fp))
    assert ok is True

    added = getattr(ur.semantic_searcher, "_added", 0)
    # Expect multiple chunks
    assert added >= 2
    # Expect per-chunk fallback to have been used
    assert ur.content_indexer._metrics.get("llm_classifications_fallback_chunk", 0) == added
    total_calls = calls["count"]
    assert total_calls > 1
