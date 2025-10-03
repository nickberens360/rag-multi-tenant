import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(reason="Disabled to avoid Chroma initialization conflicts in CI")

from backend.core.content_indexer import ContentIndexer
from backend.core.unified_retriever import UnifiedRetriever


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.mark.unit
def test_process_directory_uses_single_llm_call_per_file(
    tmp_path: Path, isolated_chroma_dir: str, mock_llm, monkeypatch
):
    # Arrange: create a JSON file that produces multiple docs/chunks
    d = tmp_path / "data"
    d.mkdir()
    payload = {
        "title": "Test Document",
        "section1": {"text": "A" * 1200},
        "section2": {"text": "B" * 1200},
    }
    fp = d / "example.json"
    _write_json(fp, payload)

    indexer = ContentIndexer(mock_llm, persist_dir=isolated_chroma_dir, classification_mode="hybrid")

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

    # Stub the startup classifier method
    assert indexer.startup_classifier is not None
    monkeypatch.setattr(indexer.startup_classifier, "classify_content_with_llm", fake_classify)

    # Act
    docs, files_processed, total_chunks = indexer.process_directory(str(d), force_reindex=True)

    # Assert: exactly 1 LLM classification for the single file
    assert files_processed == 1
    assert calls["count"] == 1
    assert indexer._metrics.get("llm_classifications_performed") == 1
    # All chunks should carry file-level metadata
    assert total_chunks == len(docs)
    for doc in docs:
        md = doc.metadata
        assert md.get("classification_method") == "startup_llm"
        assert md.get("topic_confidence") == 0.9
        assert md.get("content_type") == "skills,project" or md.get("content_types") == "skills,project"
        assert md.get("file_topics") is not None
        assert md.get("chunk_index") is not None
        assert md.get("chunk_id") is not None


@pytest.mark.unit
def test_reindex_file_uses_single_llm_call(
    tmp_path: Path, isolated_chroma_dir: str, mock_embeddings, mock_llm, monkeypatch
):
    # Create test file
    d = tmp_path / "data"
    d.mkdir()
    fp = d / "example.json"
    _write_json(fp, {"a": "A" * 1200, "b": "B" * 1200})

    ur = UnifiedRetriever(embeddings=mock_embeddings, llm=mock_llm, persist_dir=isolated_chroma_dir)

    # Replace semantic_searcher with a no-op to avoid Chroma dependency in test
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

    # Act
    ok = ur.reindex_file(str(fp))

    # Assert
    assert ok is True
    assert calls["count"] == 1
    assert ur.content_indexer._metrics.get("llm_classifications_performed") == 1
