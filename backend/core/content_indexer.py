"""
Content indexer component for handling file processing and metadata extraction.

This module provides focused functionality for:
- File discovery and hash computation
- Content metadata extraction using LLM and heuristics
- Directory indexing with incremental updates
- File filtering and validation
"""

import fnmatch
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel

from ..ingest.chunking import splitter_for_ext
from ..ingest.loaders import load_doc
from .fast_content_classifier import FastContentClassifier
from .llm_utils import _MAX_TEXT_LENGTH_FOR_TOPICS  # reuse existing truncation constant
from .llm_utils import extract_topics_with_llm, generate_document_context
from .startup_content_classifier import StartupContentClassifier

logger = logging.getLogger(__name__)


class ContentIndexer:
    """Handles content discovery, processing, and metadata extraction for indexing."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        persist_dir: str = "backend/.unified_chroma",
        use_fast_classifier: bool = True,
        classification_mode: str = "hybrid",  # "fast", "startup_llm", "hybrid"
    ):
        self.llm = llm
        self.persist_dir = persist_dir
        self._document_contexts: Dict[str, str] = {}  # Cache for document contexts
        self.use_fast_classifier = use_fast_classifier
        self.classification_mode = classification_mode
        self.use_per_file_classification: bool = True  # Phase 1 feature flag (default on)
        self._file_classification_cache: Dict[str, Dict[str, Any]] = {}
        self._metrics: Dict[str, int] = {
            "llm_classifications_performed": 0,
            "llm_classifications_fallback_chunk": 0,
        }
        # Phase 2 (optional) heterogeneity fallback flag via env
        self.enable_heterogeneity_fallback: bool = os.getenv("ENABLE_HETEROGENEITY_FALLBACK", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        self._heterogeneity_threshold: float = 0.35  # average Jaccard similarity threshold
        self._heterogeneity_chunk_fraction: float = 0.5  # fraction of chunks below per-chunk threshold to trigger
        self._heterogeneity_per_chunk_threshold: float = 0.25
        # Optional include list to force per-chunk fallback for specific paths (glob patterns)
        include_env = os.getenv("HETEROGENEITY_FALLBACK_INCLUDE", "")
        self._hetero_include_globs: List[str] = [g.strip() for g in include_env.split(",") if g.strip()]

        # Initialize classifiers based on mode
        if classification_mode == "fast" or (classification_mode == "hybrid" and use_fast_classifier):
            self.fast_classifier = FastContentClassifier()
        else:
            self.fast_classifier = None

        if classification_mode == "startup_llm" or classification_mode == "hybrid":
            self.startup_classifier = StartupContentClassifier(llm)
        else:
            self.startup_classifier = None

        logger.info(f"ContentIndexer initialized with classification_mode={classification_mode}")

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_metrics(self) -> Dict[str, int]:
        """Return a copy of simple indexing metrics for reporting."""
        return dict(self._metrics)

    def extract_content_metadata(
        self, doc: Document, file_path: Path, precomputed: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Extract metadata using the configured classification mode.

        Modes:
        - "fast": Use fast pattern-based classification (fastest, hardcoded patterns)
        - "startup_llm": Use LLM classification (slower startup, better accuracy)
        - "hybrid": Use startup LLM classification (recommended)
        """
        content = doc.page_content

        # Short-circuit with precomputed file-level metadata (Phase 1 reuse)
        if precomputed is not None:
            # Namespaced file-level keys for lineage/debug
            file_topics = [t.strip() for t in (precomputed.get("content_type", "").split(",")) if t.strip()]
            merged = dict(precomputed)
            merged.update(
                {
                    "file_topics": file_topics,
                    "file_keywords": precomputed.get("content_keywords", ""),
                    "file_topic_confidence": precomputed.get("topic_confidence", 0.0),
                    "file_classification_method": precomputed.get("classification_method", "startup_llm"),
                }
            )
            # Legacy/flattened keys populated from file-level values
            merged.setdefault("content_types", precomputed.get("content_type", ""))
            merged.setdefault("classification_method", precomputed.get("classification_method", "startup_llm"))
            merged.setdefault("topic_confidence", precomputed.get("topic_confidence", 0.0))
            merged.setdefault("content_keywords", precomputed.get("content_keywords", ""))
            return merged

        # Route to appropriate classification method based on mode
        if self.classification_mode == "startup_llm" or self.classification_mode == "hybrid":
            # Use high-accuracy LLM classification during indexing
            if self.startup_classifier:
                return self.startup_classifier.classify_content_with_llm(doc, file_path)
            else:
                # In hybrid mode, fallback to fast classifier first
                if self.classification_mode == "hybrid" and self.fast_classifier:
                    logger.warning(
                        "Startup classifier not available in hybrid mode, falling back to fast content classifier."
                    )
                    return self.fast_classifier.enhance_document_metadata(doc, file_path)

                logger.warning("Startup classifier not available, falling back to legacy method")

        elif self.classification_mode == "fast":
            # Use fast pattern-based classification
            if self.fast_classifier:
                return self.fast_classifier.enhance_document_metadata(doc, file_path)
            else:
                logger.warning("Fast classifier not available, falling back to legacy method")

        # Legacy LLM-based extraction (fallback)
        logger.info(f"Using legacy classification for {file_path.name}")
        content_types = extract_topics_with_llm(self.llm, content)

        # Deterministic heuristics
        fname = file_path.name.lower()
        text_lc = content.lower()
        heuristic_tags: List[str] = []

        # Filename-based tags
        if "about" in fname:
            heuristic_tags.append("about")
        if "resume" in fname:
            heuristic_tags.extend(["experience", "skills"])
        if "project" in fname:
            heuristic_tags.append("project")
        if "illustration" in fname or "illustrations" in fname:
            heuristic_tags.append("creative")

        # Content keyword-based tags (covers queries like "artistic inspiration")
        creative_keywords = [
            "art",
            "artistic",
            "inspiration",
            "illustration",
            "illustrations",
            "design",
            "creative",
            "cartoon",
            "cartoons",
        ]
        if any(k in text_lc for k in creative_keywords):
            heuristic_tags.append("creative")

        about_keywords = ["about", "background", "bio", "who is nick", "who am i"]
        if any(k in text_lc for k in about_keywords):
            heuristic_tags.append("about")

        # Special handling for illustration JSON files
        is_illustration_data = file_path.name == "illustrations.json"
        illustration_file = None

        if is_illustration_data:
            heuristic_tags.append("creative")  # Ensure creative tag for illustrations
            # Extract file name from JSON content for frontend display
            try:
                if '"file"' in doc.page_content:
                    data = json.loads(doc.page_content)
                    if isinstance(data, dict) and "file" in data:
                        illustration_file = data.get("file")
                        logger.info(f"Found illustration file: {illustration_file}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse JSON to find illustration file in doc from {file_path.name}")

        # Merge, dedupe, normalize
        merged_types = sorted({t.strip().lower() for t in (content_types + heuristic_tags) if t and t.strip()})

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": ",".join(merged_types),
            "content_types": ",".join(merged_types),  # Backward compatibility alias
            "content_length": len(content),
            "has_code": "```" in doc.page_content or "function" in text_lc,
            "is_illustration_data": is_illustration_data,
        }

        # Add illustration file path for frontend display
        if illustration_file:
            metadata["illustration_file"] = illustration_file
            metadata["display_path"] = f"/illustrations/{illustration_file}"

        return metadata

    def should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed based on its name and type."""
        # Skip system/config files that aren't content
        skip_files = {"robots.txt", "sitemap.xml", ".htaccess", "favicon.ico", "manifest.json"}

        if file_path.name.lower() in skip_files:
            logger.debug(f"Skipping system file: {file_path}")
            return False

        return True

    def should_skip_file(
        self, file_path: Path, file_hash: str, indexed_files: Dict[str, Any], force_reindex: bool
    ) -> bool:
        """Check if a file should be skipped during indexing.

        Backward compatible with legacy index_metadata schema where the value
        was a plain hash string, and the new schema where it's an object
        {"hash": <str>, "classification": <dict>}.
        """
        if force_reindex:
            return False
        entry = indexed_files.get(str(file_path))
        if entry is None:
            return False
        if isinstance(entry, str):
            return entry == file_hash
        if isinstance(entry, dict):
            return entry.get("hash") == file_hash
        return False

    def process_directory(self, directory: str, force_reindex: bool = False) -> Tuple[List[Document], int, int]:
        """
        Process all files in a directory and return documents ready for indexing.

        Returns:
            Tuple of (documents, files_processed, total_chunks)
        """
        base_path = Path(directory)
        if not base_path.exists():
            logger.warning(f"Directory {directory} does not exist")
            return [], 0, 0

        # Track indexed files (read even on force_reindex to reuse persisted classification)
        index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
        indexed_files: Dict[str, Any] = {}

        if index_metadata_path.exists():
            with open(index_metadata_path, "r", encoding="utf-8") as f:
                indexed_files = json.load(f)

        all_documents = []
        files_processed = 0
        total_chunks = 0

        # Discover all files
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith(".") and self.should_index_file(file_path):
                logger.info(f"Processing file: {file_path}")
                file_hash = self.compute_file_hash(file_path)

                # Skip if already indexed and unchanged
                should_skip = self.should_skip_file(file_path, file_hash, indexed_files, force_reindex)
                if should_skip:
                    logger.info(f"Skipping {file_path} - already indexed (force_reindex={force_reindex})")
                    continue
                else:
                    logger.info(f"Will process {file_path} (force_reindex={force_reindex})")

                # Load and process the document
                try:
                    docs = load_doc(file_path)
                    if not docs:
                        logger.info(f"No documents loaded from {file_path}")
                        continue

                    # Use appropriate splitter based on file type
                    splitter = splitter_for_ext(file_path.suffix)
                    chunks = splitter.split_documents(docs)

                    # Phase 1: compute once-per-file classification (startup_llm/hybrid) and reuse
                    precomputed: Optional[Dict[str, Any]] = None
                    if (
                        self.use_per_file_classification
                        and (self.classification_mode in ("startup_llm", "hybrid"))
                        and self.startup_classifier is not None
                    ):
                        cached = self._file_classification_cache.get(file_hash)
                        # Phase 3: check persisted classification for same hash
                        persisted_entry = indexed_files.get(str(file_path))
                        if isinstance(persisted_entry, dict) and persisted_entry.get("hash") == file_hash:
                            persisted_class = persisted_entry.get("classification")
                            if isinstance(persisted_class, dict) and persisted_class:
                                cached = persisted_class
                                logger.info(
                                    f"Using persisted file-level classification for {file_path.name} (hash match)."
                                )
                        if cached is None:
                            representative_doc = self._build_representative_document(docs, file_path)
                            try:
                                cached = self.startup_classifier.classify_content_with_llm(
                                    representative_doc, file_path
                                )
                            except Exception as e:
                                logger.error(
                                    f"File-level classification failed for {file_path.name}: {e}. Falling back to per-chunk path."
                                )
                                cached = None
                            if cached is not None:
                                self._file_classification_cache[file_hash] = cached
                                # Telemetry: count one LLM classification per file
                                self._metrics["llm_classifications_performed"] += 1
                        precomputed = cached

                    # Phase 2: detect heterogeneity and optionally enable per-chunk fallback
                    use_per_chunk_fallback = False
                    # Forced include by glob patterns
                    if self._path_in_include(file_path):
                        use_per_chunk_fallback = True
                        logger.info(f"Per-chunk LLM classification forced by include list for {file_path.name}.")
                    # Heuristic detection (when enabled)
                    elif self.enable_heterogeneity_fallback and precomputed is not None and len(chunks) >= 2:
                        try:
                            use_per_chunk_fallback = self._is_file_heterogeneous(chunks)
                            if use_per_chunk_fallback:
                                logger.info(
                                    f"Heterogeneity detected for {file_path.name}; using per-chunk LLM classification."
                                )
                        except Exception as e:
                            logger.debug(f"Heterogeneity detection failed for {file_path.name}: {e}")

                    # Add rich metadata to each chunk including enhanced RAG metadata
                    for chunk_index, chunk in enumerate(chunks):
                        if use_per_chunk_fallback:
                            base_metadata = self.extract_content_metadata(chunk, file_path, precomputed=None)
                            # Telemetry: count chunk-level fallbacks
                            self._metrics["llm_classifications_fallback_chunk"] += 1
                        else:
                            base_metadata = self.extract_content_metadata(chunk, file_path, precomputed=precomputed)

                        # Add enhanced metadata for RAG best practices
                        enhanced_metadata = {
                            "chunk_index": chunk_index,
                            "chunk_size": len(chunk.page_content),
                            "file_hash": file_hash,
                            "total_chunks": len(chunks),
                        }

                        # Add deterministic chunk ID for better vector store management
                        file_hash_short = file_hash[:8]
                        chunk_id = f"{file_hash_short}-c{chunk_index}"
                        enhanced_metadata["chunk_id"] = chunk_id

                        # Merge all metadata
                        chunk.metadata.update(base_metadata)
                        chunk.metadata.update(enhanced_metadata)

                    all_documents.extend(chunks)
                    files_processed += 1
                    total_chunks += len(chunks)
                    # Persist Phase 3 payload (hash + minimal classification block)
                    record: Dict[str, Any] = {"hash": file_hash}
                    if precomputed is not None:
                        record["classification"] = precomputed
                    indexed_files[str(file_path)] = record
                    logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")

                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")

        # Save index metadata
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        with open(index_metadata_path, "w", encoding="utf-8") as f:
            json.dump(indexed_files, f)

        logger.info(
            "Indexing metrics: files_processed=%d, total_chunks=%d, llm_classifications_performed=%d",
            files_processed,
            total_chunks,
            self._metrics.get("llm_classifications_performed", 0),
        )

        return all_documents, files_processed, total_chunks

    def _build_representative_document(self, docs: List[Document], file_path: Path) -> Document:
        """Construct a representative Document for per-file classification.

        Strategy:
        - For JSON and known special files, use the first loader doc (often the full object).
        - For others, merge with a fixed separator and sample head/middle/tail windows
          within `_MAX_TEXT_LENGTH_FOR_TOPICS` to reduce topic bias.
        """
        ext = file_path.suffix.lower()

        # Prefer full-object doc for JSON and special cases
        if ext == ".json" or file_path.name == "illustrations.json":
            base_doc = docs[0]
            return Document(page_content=base_doc.page_content, metadata=base_doc.metadata)

        # Merge documents with a clear break to avoid semantic bleed
        separator = "\n\n# --- DOC BREAK ---\n\n"
        merged = separator.join(d.page_content for d in docs if d and d.page_content)

        # If small enough, return as-is
        if len(merged) <= _MAX_TEXT_LENGTH_FOR_TOPICS:
            return Document(page_content=merged, metadata={"source": str(file_path)})

        # Deterministic head/middle/tail sampling
        limit = _MAX_TEXT_LENGTH_FOR_TOPICS
        window = max(limit // 3, 1)
        n = len(merged)
        head = merged[:window]
        mid_start = max(min((n // 2) - (window // 2), n - window), 0)
        middle = merged[mid_start : mid_start + window]
        tail = merged[-window:]

        sample = separator.join([head, middle, tail])
        return Document(page_content=sample, metadata={"source": str(file_path)})

    def _is_file_heterogeneous(self, chunks: List[Document]) -> bool:
        """Detect mixed-topic files using lightweight token Jaccard similarity.

        - Tokenize chunks into lowercase words >=4 chars, strip stopwords.
        - Compute top-K tokens per chunk and for the whole file.
        - Compute Jaccard similarity between each chunk's token set and the file token set.
        - Trigger heterogeneity if average similarity < threshold and
          fraction of chunks below per-chunk threshold exceeds configured fraction.
        """
        if not chunks:
            return False

        def tokenize(text: str) -> List[str]:
            from .constants import CONTENT_INDEXER_STOP_WORDS

            words = re.findall(r"\b[a-z]{4,}\b", text.lower())
            return [w for w in words if w not in CONTENT_INDEXER_STOP_WORDS]

        def topk(tokens: List[str], k: int = 20) -> List[str]:
            freq: Dict[str, int] = {}
            for t in tokens:
                freq[t] = freq.get(t, 0) + 1
            return [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:k]]

        # File-level token set from all chunks
        all_tokens: List[str] = []
        chunk_token_sets: List[set[str]] = []
        for c in chunks:
            tks = tokenize(c.page_content)
            chunk_set = set(topk(tks))
            chunk_token_sets.append(chunk_set)
            all_tokens.extend(tks)

        file_set = set(topk(all_tokens, k=40)) or set()
        if not file_set:
            return False

        def jaccard(a: set[str], b: set[str]) -> float:
            if not a and not b:
                return 1.0
            inter = len(a & b)
            union = len(a | b)
            return inter / union if union else 0.0

        sims = [jaccard(s, file_set) for s in chunk_token_sets]
        avg_sim = sum(sims) / len(sims)
        low_count = sum(1 for s in sims if s < self._heterogeneity_per_chunk_threshold)
        frac_low = low_count / len(sims)

        return avg_sim < self._heterogeneity_threshold and frac_low >= self._heterogeneity_chunk_fraction

    def _path_in_include(self, file_path: Path) -> bool:
        if not self._hetero_include_globs:
            return False
        s = str(file_path)
        return any(fnmatch.fnmatch(s, pat) for pat in self._hetero_include_globs)

    def generate_document_context(self, documents: List[Document], file_path: Path) -> str:
        """Generate or retrieve cached document context using fast method or LLM."""
        file_key = str(file_path)

        # Return cached context if available
        if file_key in self._document_contexts:
            return self._document_contexts[file_key]

        # Use fast context generation if available
        if self.use_fast_classifier:
            context = self._generate_lightweight_context(documents, file_path)
        else:
            # Fallback to LLM-based context generation (slower)
            if documents:
                # Combine content from all documents for this file
                combined_content = " ".join(doc.page_content for doc in documents)
                context = generate_document_context(
                    self.llm, combined_content, file_path.name, file_path.suffix.lstrip(".")
                )
            else:
                # Fallback for empty documents
                context = f"This is content from {file_path.name}, a {file_path.suffix} document."

        # Cache the context
        self._document_contexts[file_key] = context

        return context

    def _generate_lightweight_context(self, documents: List[Document], file_path: Path) -> str:
        """Generate context without LLM - fast string operations only."""
        if not documents:
            return f"Content from {file_path.name}"

        # Use first chunk + file metadata for context (no LLM)
        first_chunk = documents[0].page_content[:200]  # First 200 chars
        file_type = file_path.suffix.lstrip(".")

        # Get content type from first document's metadata if available
        content_type = "content"
        if documents[0].metadata and "content_type" in documents[0].metadata:
            content_type = documents[0].metadata["content_type"].replace(",", "/")

        # Create meaningful context based on file type and content
        if file_type in ["json"]:
            return f"Data from {file_path.name} ({content_type}): {first_chunk}..."
        elif file_type in ["md", "txt"]:
            return f"Documentation from {file_path.name} ({content_type}): {first_chunk}..."
        elif file_type in ["pdf"]:
            return f"PDF document {file_path.name} ({content_type}): {first_chunk}..."
        else:
            return f"File {file_path.name} ({file_type}, {content_type}): {first_chunk}..."

    def enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
        """Enhance a document chunk with contextual information."""
        enhanced_content = f"DOCUMENT CONTEXT: {document_context}\n\nCONTENT: {chunk.page_content}"

        # Create new metadata with context info
        enhanced_metadata = chunk.metadata.copy()
        enhanced_metadata.update(
            {
                "has_document_context": True,
                "original_content_length": len(chunk.page_content),
                "document_context": document_context,
            }
        )

        return Document(page_content=enhanced_content, metadata=enhanced_metadata)
