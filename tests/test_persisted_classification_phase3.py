import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(reason="Disabled to avoid Chroma initialization conflicts in CI")

from backend.core.content_indexer import ContentIndexer
from backend.core.unified_retriever import UnifiedRetriever


def _write_md(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


@pytest.mark.unit
def test_persisted_classification_reused_on_force_reindex_process_directory(
    tmp_path: Path, isolated_chroma_dir: str, mock_llm, monkeypatch
):
    d = tmp_path / "data"
    d.mkdir()
    fp = d / "example.md"
    _write_md(fp, ("This is a test document about programming and projects. ") * 200)

    # First run: classify once and persist
    calls1 = {"count": 0}
    idx1 = ContentIndexer(mock_llm, persist_dir=isolated_chroma_dir, classification_mode="hybrid")
    assert idx1.startup_classifier is not None

    def fake_classify1(doc, file_path):
        calls1["count"] += 1
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": "project,technical",
            "content_types": "project,technical",
            "content_keywords": "python",
            "topic_confidence": 0.9,
            "classification_method": "startup_llm",
        }

    monkeypatch.setattr(idx1.startup_classifier, "classify_content_with_llm", fake_classify1)
    docs1, files1, chunks1 = idx1.process_directory(str(d), force_reindex=True)
    assert files1 == 1
    assert calls1["count"] == 1

    # Verify classification persisted
    from pathlib import Path

    meta_path = Path(isolated_chroma_dir) / "index_metadata.json"
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    entry = data.get(str(fp))
    assert isinstance(entry, dict) and "hash" in entry and "classification" in entry

    # Second run: force reindex but reuse persisted classification (no new LLM calls)
    calls2 = {"count": 0}
    idx2 = ContentIndexer(mock_llm, persist_dir=isolated_chroma_dir, classification_mode="hybrid")
    assert idx2.startup_classifier is not None

    def fake_classify2(doc, file_path):
        calls2["count"] += 1
        return fake_classify1(doc, file_path)

    monkeypatch.setattr(idx2.startup_classifier, "classify_content_with_llm", fake_classify2)
    docs2, files2, chunks2 = idx2.process_directory(str(d), force_reindex=True)
    assert files2 == 1
    # Should reuse persisted classification, resulting in zero LLM calls in second run
    assert calls2["count"] == 0


@pytest.mark.unit
def test_persisted_classification_reused_on_reindex_file(
    tmp_path: Path, isolated_chroma_dir: str, mock_embeddings, mock_llm, monkeypatch
):
    d = tmp_path / "data"
    d.mkdir()
    fp = d / "example.txt"
    _write_md(fp, ("skills experience project technical programming ") * 300)

    # First run: classify once and persist via reindex_file
    ur1 = UnifiedRetriever(embeddings=mock_embeddings, llm=mock_llm, persist_dir=isolated_chroma_dir)
    ur1.semantic_searcher = type(
        "NoOp", (), {"delete_where": lambda self, where: None, "add_documents": lambda self, docs: None}
    )()
    calls1 = {"count": 0}

    def fake_classify1(doc, file_path):
        calls1["count"] += 1
        return {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": "skills",
            "content_types": "skills",
            "content_keywords": "python",
            "topic_confidence": 0.95,
            "classification_method": "startup_llm",
        }

    assert ur1.content_indexer.startup_classifier is not None
    monkeypatch.setattr(ur1.content_indexer.startup_classifier, "classify_content_with_llm", fake_classify1)
    assert ur1.reindex_file(str(fp)) is True
    assert calls1["count"] == 1

    # Second run: new retriever, reuse persisted classification
    ur2 = UnifiedRetriever(embeddings=mock_embeddings, llm=mock_llm, persist_dir=isolated_chroma_dir)
    ur2.semantic_searcher = type(
        "NoOp", (), {"delete_where": lambda self, where: None, "add_documents": lambda self, docs: None}
    )()
    calls2 = {"count": 0}

    def fake_classify2(doc, file_path):
        calls2["count"] += 1
        return fake_classify1(doc, file_path)

    assert ur2.content_indexer.startup_classifier is not None
    monkeypatch.setattr(ur2.content_indexer.startup_classifier, "classify_content_with_llm", fake_classify2)
    assert ur2.reindex_file(str(fp)) is True
    assert calls2["count"] == 0
