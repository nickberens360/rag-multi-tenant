"""
Unified retriever orchestrator using component-based architecture.

This module provides a clean facade over the specialized components:
- ContentIndexer: File processing and metadata extraction
- SemanticSearcher: Vector store operations and similarity search
- ContentRouter: Query routing and content type detection

The UnifiedRetriever now acts as a coordinator/facade that maintains backward compatibility
while delegating responsibilities to focused components.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

from .config_v2 import AppConfig
from .content_indexer import ContentIndexer
from .content_router import ContentRouter
from .db_session import get_db_session_sync
from .semantic_searcher import SemanticSearcher

logger = logging.getLogger(__name__)


class UnifiedRetriever:
    """
    Orchestrates content indexing, semantic search, and intelligent routing.

    This class acts as a facade over specialized components, maintaining backward
    compatibility while providing a clean separation of concerns.
    """

    def __init__(
        self,
        embeddings: Any,
        llm: BaseLanguageModel,
        persist_dir: str = "backend/.unified_chroma",
        use_fast_classifier: bool = True,
        classification_mode: str = "hybrid",
    ):
        self.embeddings = embeddings
        self.llm = llm
        self.persist_dir = persist_dir
        self.use_fast_classifier = use_fast_classifier
        self.classification_mode = classification_mode

        # Initialize component-based architecture with hybrid classification
        self.content_indexer = ContentIndexer(
            llm, persist_dir, use_fast_classifier=use_fast_classifier, classification_mode=classification_mode
        )
        self.semantic_searcher = SemanticSearcher(embeddings, persist_dir)
        self.content_router = ContentRouter(self.semantic_searcher)

        logger.info("UnifiedRetriever initialized with component-based architecture")

    def index_directory(self, directory: str, force_reindex: bool = False) -> Tuple[int, int]:
        """
        Automatically discover and index all content in a directory.

        Returns:
            Tuple of (files_indexed, total_chunks)
        """
        logger.info(f"Indexing directory: {directory} (force_reindex={force_reindex})")

        # Process directory using ContentIndexer
        documents, files_processed, total_chunks = self.content_indexer.process_directory(directory, force_reindex)

        # Stamp tenant metadata based on file paths and add to vector store
        if documents:
            shared_docs: List[Document] = []
            per_tenant: DefaultDict[Tuple[str, Optional[str]], List[Document]] = defaultdict(list)

            for doc in documents:
                src = doc.metadata.get("source") or doc.metadata.get("file_path") or doc.metadata.get("path") or ""
                src_str = str(src)

                tenant_slug = self._parse_tenant_slug_from_path(src_str)
                if tenant_slug:
                    tid = self._resolve_tenant_id(tenant_slug)
                    # Stamp scope + tenant metadata
                    doc.metadata["scope"] = "tenant"
                    if tid:
                        doc.metadata["tenant_id"] = tid
                        doc.metadata["tenant_slug"] = tenant_slug
                        per_tenant[(tid, tenant_slug)].append(doc)
                        logger.debug(f"Stamped tenant metadata: {tenant_slug} ({tid[:8]}...) on {src_str[:60]}")
                    else:
                        # SECURITY: NEVER fall back to shared for tenant-scoped documents!
                        # This prevents cross-tenant data leakage.
                        logger.error(
                            f"SECURITY VIOLATION PREVENTED: Tenant slug '{tenant_slug}' not found in database. "
                            f"Document REJECTED to prevent data leakage: {src_str}"
                        )
                        # Skip this document entirely - do NOT index it
                        continue
                else:
                    # Only truly shared documents (no /tenants/ in path) go here
                    logger.debug(f"No tenant slug found in path, adding to shared: {src_str[:60]}")
                    shared_docs.append(doc)

            # Add shared docs
            if shared_docs:
                logger.info(f"Adding {len(shared_docs)} shared documents (no tenant scoping)")
                self.semantic_searcher.add_documents(shared_docs)

            # Add tenant docs grouped by tenant_id
            for (tenant_id, tslug), docs in per_tenant.items():
                try:
                    logger.info(f"Adding {len(docs)} documents for tenant {tslug} ({tenant_id[:8]}...)")
                    self.semantic_searcher.add_documents_for_tenant(docs, tenant_id=tenant_id, tenant_slug=tslug)
                except Exception as e:
                    logger.error(f"Failed to add documents for tenant {tenant_id}: {e}")

        logger.info(f"Indexing complete: {files_processed} files, {total_chunks} chunks")
        return files_processed, total_chunks

    def reindex_file(self, file_path: str) -> bool:
        """
        Reindex a specific file by removing existing entries and re-adding it.

        Args:
            file_path: Path to the file to reindex

        Returns:
            bool: True if reindexing was successful, False otherwise
        """
        try:
            import json
            from pathlib import Path

            from ..ingest.chunking import splitter_for_ext
            from ..ingest.loaders import load_doc

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File does not exist: {file_path}")
                return False

            logger.info(f"Reindexing file: {file_path}")

            # Remove existing documents with this file path from vector store
            try:
                self.semantic_searcher.delete_where({"source": str(file_path_obj)})
                logger.info(f"Removed existing entries for: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove existing entries: {e}")

            # Process the file like in process_directory
            docs = load_doc(file_path_obj)
            if not docs:
                logger.warning(f"No documents loaded from {file_path}")
                return False

            # Use appropriate splitter based on file type
            splitter = splitter_for_ext(file_path_obj.suffix)
            chunks = splitter.split_documents(docs)

            # Phase 1: compute once-per-file classification and reuse if enabled
            precomputed: Dict[str, Any] | None = None
            if (
                getattr(self.content_indexer, "use_per_file_classification", False)
                and (self.classification_mode in ("startup_llm", "hybrid"))
                and getattr(self.content_indexer, "startup_classifier", None) is not None
            ):
                file_hash = self.content_indexer.compute_file_hash(file_path_obj)
                cached = self.content_indexer._file_classification_cache.get(file_hash)
                # Phase 3: try persisted classification if available
                try:
                    index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
                    if index_metadata_path.exists():
                        with open(index_metadata_path, "r", encoding="utf-8") as f:
                            indexed_files = json.load(f)
                        entry = indexed_files.get(str(file_path_obj))
                        if isinstance(entry, dict) and entry.get("hash") == file_hash:
                            persisted_class = entry.get("classification")
                            if isinstance(persisted_class, dict) and persisted_class:
                                cached = persisted_class
                                logger.info(
                                    f"Using persisted file-level classification for {file_path_obj.name} (hash match)."
                                )
                except Exception as e:
                    logger.debug(f"Failed to use persisted classification: {e}")
                if cached is None:
                    representative_doc = self.content_indexer._build_representative_document(docs, file_path_obj)
                    try:
                        cached = self.content_indexer.startup_classifier.classify_content_with_llm(
                            representative_doc, file_path_obj
                        )
                    except Exception as e:
                        logger.error(
                            f"File-level classification failed for {file_path_obj.name}: {e}. Proceeding without precompute."
                        )
                        cached = None
                    if cached is not None:
                        self.content_indexer._file_classification_cache[file_hash] = cached
                        # Telemetry: count one LLM classification per file
                        if hasattr(self.content_indexer, "_metrics"):
                            self.content_indexer._metrics["llm_classifications_performed"] = (
                                self.content_indexer._metrics.get("llm_classifications_performed", 0) + 1
                            )
                precomputed = cached

            # Phase 2: heterogeneity detection and optional per-chunk fallback
            use_per_chunk_fallback = False
            # Forced include by glob patterns
            try:
                if self.content_indexer._path_in_include(file_path_obj):
                    use_per_chunk_fallback = True
                    logger.info(f"Per-chunk LLM classification forced by include list for {file_path_obj.name}.")
            except Exception:
                pass
            # Heuristic detection (when enabled)
            if (
                not use_per_chunk_fallback
                and getattr(self.content_indexer, "enable_heterogeneity_fallback", False)
                and precomputed is not None
                and len(chunks) >= 2
            ):
                try:
                    use_per_chunk_fallback = self.content_indexer._is_file_heterogeneous(chunks)
                    if use_per_chunk_fallback:
                        logger.info(
                            f"Heterogeneity detected for {file_path_obj.name}; using per-chunk LLM classification."
                        )
                except Exception as e:
                    logger.debug(f"Heterogeneity detection failed for {file_path_obj.name}: {e}")

            # Add rich metadata to each chunk (aligned with ContentIndexer.process_directory)
            file_hash = self.content_indexer.compute_file_hash(file_path_obj)

            # Fetch effective metadata from knowledge_files table for propagation
            effective_metadata_dict = {}
            try:
                from .knowledge_index_db import KnowledgeIndexDB

                # Extract tenant_id from file path for proper metadata lookup
                src_path = str(file_path_obj)
                tenant_slug = self._parse_tenant_slug_from_path(src_path)
                tenant_id = self._resolve_tenant_id(tenant_slug) if tenant_slug else None

                db = KnowledgeIndexDB()
                file_metadata = db.get_file_metadata(src_path, tenant_id=tenant_id)
                if file_metadata:
                    # Extract effective metadata for propagation to chunks
                    effective_metadata_dict = {
                        "effective_content_type": file_metadata.get("effective_content_type"),
                        "effective_tags": file_metadata.get("effective_tags", []),
                        "metadata_provenance": file_metadata.get("metadata_provenance", "inferred"),
                    }
                    logger.debug(
                        f"Propagating effective metadata to chunks: "
                        f"content_type={effective_metadata_dict['effective_content_type']}, "
                        f"tags={effective_metadata_dict['effective_tags']}, "
                        f"provenance={effective_metadata_dict['metadata_provenance']}"
                    )
            except Exception as e:
                logger.warning(f"Could not fetch effective metadata for {file_path_obj}: {e}")

            for chunk_index, chunk in enumerate(chunks):
                if use_per_chunk_fallback:
                    base_metadata = self.content_indexer.extract_content_metadata(
                        chunk, file_path_obj, precomputed=None
                    )
                    if hasattr(self.content_indexer, "_metrics"):
                        self.content_indexer._metrics["llm_classifications_fallback_chunk"] = (
                            self.content_indexer._metrics.get("llm_classifications_fallback_chunk", 0) + 1
                        )
                else:
                    base_metadata = self.content_indexer.extract_content_metadata(
                        chunk, file_path_obj, precomputed=precomputed
                    )

                enhanced_metadata = {
                    "chunk_index": chunk_index,
                    "chunk_size": len(chunk.page_content),
                    "file_hash": file_hash,
                    "total_chunks": len(chunks),
                }
                file_hash_short = file_hash[:8]
                chunk_id = f"{file_hash_short}-c{chunk_index}"
                enhanced_metadata["chunk_id"] = chunk_id

                chunk.metadata.update(base_metadata)
                chunk.metadata.update(enhanced_metadata)

                # Propagate effective metadata from knowledge_files to chunk
                if effective_metadata_dict:
                    chunk.metadata.update(effective_metadata_dict)

            # Stamp tenant metadata and add to vector store
            if chunks:
                src_path = str(file_path_obj)
                tenant_slug = self._parse_tenant_slug_from_path(src_path)
                if tenant_slug:
                    tenant_id = self._resolve_tenant_id(tenant_slug)
                    for ch in chunks:
                        ch.metadata["scope"] = "tenant"
                        ch.metadata["tenant_slug"] = tenant_slug
                        if tenant_id:
                            ch.metadata["tenant_id"] = tenant_id

                    if tenant_id:
                        self.semantic_searcher.add_documents_for_tenant(
                            chunks, tenant_id=tenant_id, tenant_slug=tenant_slug
                        )
                    else:
                        # SECURITY: NEVER fall back to shared for tenant-scoped documents!
                        logger.error(
                            f"SECURITY VIOLATION PREVENTED: Tenant slug '{tenant_slug}' found in path but not in database. "
                            f"Document REJECTED to prevent data leakage: {file_path}"
                        )
                        raise ValueError(
                            f"Tenant '{tenant_slug}' not found in database. Cannot index tenant document without valid tenant ID."
                        )
                else:
                    # No tenant context; index without shared scope
                    self.semantic_searcher.add_documents(chunks)
                logger.info(f"Successfully reindexed {file_path}: {len(chunks)} chunks")

                # Update the index metadata to mark as processed
                index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
                metadata_index: Dict[str, Any] = {}
                if index_metadata_path.exists():
                    with open(index_metadata_path, "r", encoding="utf-8") as f:
                        metadata_index = json.load(f)

                # Update hash
                file_hash = self.content_indexer.compute_file_hash(file_path_obj)
                record: Dict[str, Any] = {"hash": file_hash}
                if precomputed is not None:
                    record["classification"] = precomputed
                metadata_index[str(file_path_obj)] = record

                # Save updated metadata
                Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
                with open(index_metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata_index, f)

                # Best-effort: update KnowledgeIndexDB status for this file
                try:
                    from .knowledge_index_db import KnowledgeIndexDB

                    db = KnowledgeIndexDB()
                    # Recompute vector_count precisely from the store
                    try:
                        vcount = self.semantic_searcher.get_count(where={"source": str(file_path_obj)})
                    except Exception:
                        vcount = None
                    db.update_indexed(
                        str(file_path_obj), file_hash=file_hash, chunk_count=len(chunks), vector_count=vcount
                    )
                except Exception as _e:
                    logger.debug(f"KnowledgeIndexDB update skipped: {_e}")

                return True
            else:
                logger.warning(f"No chunks created from {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to reindex file {file_path}: {e}")
            return False

    def get_retriever(
        self, search_kwargs: Optional[Dict[str, Any]] = None, filter_content_types: Optional[List[str]] = None
    ) -> BaseRetriever:
        """
        Get a retriever with optional filtering.

        Args:
            search_kwargs: Additional search parameters (e.g., k=5)
            filter_content_types: Filter by content types (e.g., ['technical', 'experience'])
        """
        return self.semantic_searcher.get_retriever(search_kwargs, filter_content_types)

    def get_relevant_documents(
        self, query: str, k: Optional[int] = None, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query=query, k=k, filter_content_types=filter_content_types)

    def semantic_search(
        self,
        query: str,
        k: Optional[int] = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        return self.semantic_searcher.semantic_search(query, k, filter_content_types, score_threshold)

    def semantic_search_for_tenant(
        self,
        query: str,
        tenant_id: str,
        k: Optional[int] = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """
        Tenant-scoped semantic search with strict isolation - NO shared documents.

        SECURITY: This method ONLY returns documents belonging to the specified tenant.
        There is NO option to include shared documents to prevent cross-tenant data leakage.
        """
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            # Use 1.5 threshold for tenant searches to be more permissive (distance metric)
            # This ensures we don't filter out relevant docs with slightly higher distances
            score_threshold = 1.5

        if self.semantic_searcher.vector_store is None:
            raise ValueError("Vector store not initialized")

        # SECURITY: Tenant-only search - NO shared documents allowed (include_shared parameter removed)
        docs_and_scores = self.semantic_searcher.similarity_search_with_score_for_tenant(
            query, tenant_id, k=k * AppConfig.SEARCH_EXPANSION_MULTIPLIER
        )

        # Score threshold filtering (distance; lower is better)
        if score_threshold == 0.0:
            filtered_docs = [doc for doc, _ in docs_and_scores]
        else:
            filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
            logger.info(
                f"Score filtering: {len(docs_and_scores)} docs -> {len(filtered_docs)} after threshold {score_threshold} "
                f"(scores: {[round(s, 3) for _, s in docs_and_scores[:5]]})"
            )

        # Content-type filtering
        if filter_content_types:
            cfiltered: List[Document] = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_cts = str(doc.metadata["content_types"]).split(",")
                    if any(ct.strip() in filter_content_types for ct in doc_cts):
                        cfiltered.append(doc)
            filtered_docs = cfiltered

        return filtered_docs[:k]

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!

        Uses ContentRouter for intelligent routing based on query analysis.
        """
        return self.content_router.auto_route_query(query)

    def get_search_strategy(self, query: str) -> Dict[str, Any]:
        """
        Get the optimal search strategy for a query.

        Delegates to ContentRouter for strategy determination.
        """
        return self.content_router.get_search_strategy(query)

    def route_with_strategy(self, query: str, custom_strategy: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Route query using a specific strategy.

        Delegates to ContentRouter for strategy-based routing.
        """
        return self.content_router.route_with_strategy(query, custom_strategy)

    # Convenience methods for accessing component functionality

    def enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
        """Enhance a document chunk with contextual information."""
        return self.content_indexer.enhance_chunk_with_context(chunk, document_context)

    def generate_document_context(self, documents: List[Document], file_path: Path) -> str:
        """Generate or retrieve cached document context using LLM."""
        return self.content_indexer.generate_document_context(documents, file_path)

    def get_collection_count(self) -> int:
        """Get the number of documents in the vector store."""
        return self.semantic_searcher.get_collection_count()

    def reset_store(self) -> None:
        """Reset and reinitialize the vector store."""
        self.semantic_searcher.reset_store()
        logger.info("UnifiedRetriever vector store reset")

    # Legacy compatibility methods (deprecated but maintained for backward compatibility)

    def _initialize_store(self):
        """Legacy method - now handled by SemanticSearcher."""
        logger.warning("_initialize_store is deprecated - initialization handled automatically")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Legacy method - delegates to ContentIndexer."""
        logger.warning("_compute_file_hash is deprecated - use content_indexer.compute_file_hash")
        return self.content_indexer.compute_file_hash(file_path)

    def _extract_content_metadata(self, doc: Document, file_path: Path) -> Dict:
        """Legacy method - delegates to ContentIndexer."""
        logger.warning("_extract_content_metadata is deprecated - use content_indexer.extract_content_metadata")
        return self.content_indexer.extract_content_metadata(doc, file_path)

    @property
    def vector_store(self):
        """Legacy property access to vector store."""
        return self.semantic_searcher.vector_store

    # Component access for advanced usage

    @property
    def indexer(self) -> ContentIndexer:
        """Access to the content indexer component."""
        return self.content_indexer

    @property
    def searcher(self) -> SemanticSearcher:
        """Access to the semantic searcher component."""
        return self.semantic_searcher

    @property
    def router(self) -> ContentRouter:
        """Access to the content router component."""
        return self.content_router

    # --- Internal helpers for tenant stamping ---

    @staticmethod
    def _parse_tenant_slug_from_path(path: str) -> Optional[str]:
        """Extract tenant slug from a knowledge file path if present."""
        try:
            # Expect segments like "/knowledge/tenants/{slug}/documents/..."
            parts = path.replace("\\", "/").split("/")
            for i, p in enumerate(parts):
                if p == "tenants" and i + 1 < len(parts):
                    slug = parts[i + 1]
                    if slug and slug not in {"shared", "documents"}:
                        return slug
            return None
        except Exception:
            return None

    @staticmethod
    def _resolve_tenant_id(tenant_slug: str) -> Optional[str]:
        """Resolve a tenant slug to its UUID string using the database if available."""
        try:
            from sqlalchemy import text

            with get_db_session_sync() as session:
                if session is None:
                    # Fallback to env default if DB unavailable
                    import os

                    fallback_id = os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"
                    logger.warning(
                        f"Database unavailable during tenant resolution for '{tenant_slug}', using fallback: {fallback_id}"
                    )
                    return fallback_id
                row = session.execute(
                    text("SELECT id FROM tenants WHERE slug = :slug AND deleted_at IS NULL"),
                    {"slug": tenant_slug},
                ).first()
                if row and row[0]:
                    return str(row[0])
                else:
                    logger.warning(f"Tenant slug '{tenant_slug}' not found in database during indexing")
                    return None
        except Exception as e:
            logger.error(f"Error resolving tenant ID for slug '{tenant_slug}': {e}")
            return None
