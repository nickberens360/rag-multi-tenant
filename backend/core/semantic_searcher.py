"""
Semantic searcher component for handling vector store operations and similarity search.

This module provides focused functionality for:
- Vector store initialization and management
- Semantic similarity search with filtering
- Document retrieval and scoring
- LangChain retriever interface compatibility
- Metadata-aware filtering (strict vs soft)
"""

import json
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from langchain.docstore.document import Document
from langchain_core.retrievers import BaseRetriever

# Prefer the newer Chroma package
try:
    from langchain_chroma import Chroma  # type: ignore
except ImportError:
    # Fallback to community version if new package not available
    from langchain_community.vectorstores import Chroma  # type: ignore

# Chroma error type (optional import, we will fall back to string-matching)
try:
    from chromadb.errors import InternalError as ChromaInternalError  # type: ignore
except Exception:  # pragma: no cover - not present in all environments
    ChromaInternalError = Exception  # type: ignore

from ..models.filter_models import MetadataFilter, RetrievalFilters
from .config_v2 import AppConfig

logger = logging.getLogger(__name__)

# Import settings manager for dynamic RAG configuration
try:
    from .settings_manager import get_settings_manager

    SETTINGS_MANAGER_AVAILABLE = True
except ImportError:
    SETTINGS_MANAGER_AVAILABLE = False


class SemanticSearcher:
    """Handles vector store operations and semantic similarity search."""

    def __init__(self, embeddings: Any, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        self._initialize_store()

    @staticmethod
    def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool, None]]:
        """Sanitize metadata to ensure compatibility with ChromaDB's primitive type requirements.

        ChromaDB only accepts str, int, float, bool, or None as metadata values.
        This method converts complex types (lists, dicts) to JSON strings for robust storage.

        Args:
            meta: Raw metadata dictionary that may contain complex types

        Returns:
            Sanitized metadata dictionary with only primitive types
        """
        compatible: Dict[str, Union[str, int, float, bool, None]] = {}
        for k, v in (meta or {}).items():
            # Allow primitives as-is
            if isinstance(v, (str, int, float, bool)) or v is None:
                compatible[k] = v
                continue
            # Convert lists and dicts to JSON strings for robust storage
            if isinstance(v, (list, dict)):
                compatible[k] = json.dumps(v, ensure_ascii=False)
                continue
            # Fallback for other non-primitive types
            compatible[k] = str(v)
        return compatible

    def _get_rag_config_settings(self):
        """Get RAG configuration settings dynamically from the settings manager."""
        if not SETTINGS_MANAGER_AVAILABLE:
            logger.debug("Settings manager not available, using static config")
            return None

        try:
            settings_manager = get_settings_manager()
            rag_settings = settings_manager.get_rag_config_settings()
            logger.debug(f"Retrieved RAG settings: score_threshold={rag_settings.rag_score_threshold}")
            return rag_settings
        except Exception as e:
            logger.warning(f"Failed to get RAG settings, falling back to static config: {e}")
            return None

    def _get_search_retrieval_settings(self):
        """Get SearchRetrievalSettings dynamically (max results, timeout, fuzzy toggles, etc.)."""
        if not SETTINGS_MANAGER_AVAILABLE:
            return None
        try:
            from .settings_manager import get_settings_manager

            settings_manager = get_settings_manager()
            return settings_manager.get_search_retrieval_settings()
        except Exception as e:
            logger.debug(f"Failed to get search retrieval settings: {e}")
            return None

    def _build_where_clause(self, filters: RetrievalFilters) -> Optional[Dict[str, Any]]:
        """
        Build ChromaDB where clause for strict filters.

        Only applies filters with provenance='manual' to ensure we're filtering
        on authoritative metadata, not inferred metadata.

        Args:
            filters: RetrievalFilters object with filter specifications

        Returns:
            ChromaDB where clause dictionary, or None if no strict filters
        """
        strict_filters = filters.get_strict_filters()
        if not strict_filters:
            return None

        # Build where clause that checks both metadata_provenance='manual' AND filter conditions
        conditions = []

        for filter_spec in strict_filters:
            if filter_spec.field == "effective_content_type":
                # Strict content type filter: ONLY manual metadata with matching value
                conditions.append(
                    {"$and": [{"metadata_provenance": "manual"}, {"effective_content_type": filter_spec.value}]}
                )
            elif filter_spec.field == "effective_tags":
                # Strict tag filter: ONLY manual metadata containing the tag
                # Tags are stored as JSON array string, need to check if value is in the array
                conditions.append(
                    {"$and": [{"metadata_provenance": "manual"}, {"effective_tags": {"$contains": filter_spec.value}}]}
                )

        if not conditions:
            return None

        # If multiple strict filters, combine with AND
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _apply_soft_reranking(
        self, docs_and_scores: List[tuple[Document, float]], filters: RetrievalFilters
    ) -> List[tuple[Document, float]]:
        """
        Apply soft reranking based on metadata filters.

        Boosts scores for documents that match filter criteria, with higher
        boost for manual metadata than inferred metadata.

        Args:
            docs_and_scores: List of (document, distance_score) tuples
            filters: RetrievalFilters with soft filter specifications

        Returns:
            List of (document, adjusted_distance_score) tuples, sorted by adjusted score
        """
        soft_filters = filters.get_soft_filters()
        if not soft_filters:
            return docs_and_scores

        reranked = []
        for doc, distance_score in docs_and_scores:
            # Start with original distance (lower is better)
            adjusted_score = distance_score
            boost_applied = 0.0

            for filter_spec in soft_filters:
                metadata_value = doc.metadata.get(filter_spec.field)
                provenance = doc.metadata.get("metadata_provenance", "inferred")

                # Check if metadata matches filter
                matches = False
                if filter_spec.field == "effective_content_type":
                    matches = metadata_value == filter_spec.value
                elif filter_spec.field == "effective_tags":
                    # Tags stored as JSON string, need to parse
                    try:
                        if isinstance(metadata_value, str):
                            import json

                            tags = json.loads(metadata_value) if metadata_value.startswith("[") else [metadata_value]
                        elif isinstance(metadata_value, list):
                            tags = metadata_value
                        else:
                            tags = []
                        matches = filter_spec.value in tags
                    except Exception:
                        matches = False

                if matches:
                    # Apply boost (reduce distance score since lower is better)
                    # Higher boost for manual metadata (authoritative)
                    if provenance == "manual":
                        boost = filter_spec.boost_weight * 1.5  # 50% more boost for manual
                        logger.debug(f"Applying MANUAL boost {boost:.2f} for {filter_spec.field}={filter_spec.value}")
                    else:
                        boost = filter_spec.boost_weight
                        logger.debug(f"Applying INFERRED boost {boost:.2f} for {filter_spec.field}={filter_spec.value}")

                    boost_applied += boost

            # Apply accumulated boost (reduce distance for matches)
            adjusted_score = max(0.0, distance_score - boost_applied)
            reranked.append((doc, adjusted_score))

        # Sort by adjusted score (lower is better)
        reranked.sort(key=lambda x: x[1])
        return reranked

    def _initialize_store(self):
        """Initialize or load the unified vector store.

        Handles known migration issues in ChromaDB 0.5 when opening a store
        created with older versions (KeyError: '_type'). In that case, we
        safely reset the persist directory if allowed and reinitialize.
        """
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # Try to disable telemetry explicitly via client settings when available
        # and bind the client to our persist directory to avoid "ephemeral" conflicts.
        client_settings = None
        try:  # Optional import; not all versions expose Settings in the same place
            from chromadb.config import Settings  # type: ignore

            # Newer chromadb versions support persist_directory in Settings; prefer it when available.
            try:
                client_settings = Settings(
                    anonymized_telemetry=False,
                    persist_directory=str(Path(self.persist_dir).resolve()),  # type: ignore[arg-type]
                )
            except TypeError:
                # Older versions may not accept persist_directory here; fall back to disabling telemetry only.
                client_settings = Settings(anonymized_telemetry=False)  # type: ignore[call-arg]
            except Exception:
                client_settings = None
        except Exception:
            client_settings = None

        def _create_store():
            if client_settings is not None:
                return Chroma(
                    collection_name="unified_knowledge",
                    persist_directory=self.persist_dir,
                    embedding_function=self.embeddings,
                    client_settings=client_settings,
                )
            # Fallback path when Settings is unavailable
            return Chroma(
                collection_name="unified_knowledge",
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
            )

        auto_reset = os.getenv("CHROMA_AUTO_RESET_ON_CONFIG_ERROR", "true").lower() in {"1", "true", "yes"}

        try:
            self.vector_store = _create_store()
        except KeyError as e:
            # Typical when opening a DB from older Chroma versions: KeyError('_type')
            if auto_reset and e.args and e.args[0] == "_type":
                logger.error(
                    "Chroma collection configuration looks incompatible (missing '_type'). "
                    "Resetting store at %s and rebuilding.",
                    self.persist_dir,
                )
                self._reset_store()
                self.vector_store = _create_store()
            else:
                raise
        except Exception as e:
            # Handle the same signature wrapped in other exceptions
            msg = str(e)
            if auto_reset and "_type" in msg and "config" in msg:
                logger.error(
                    "Chroma configuration error detected (%s). Resetting store at %s and rebuilding.",
                    msg,
                    self.persist_dir,
                )
                self._reset_store()
                self.vector_store = _create_store()
            else:
                raise

    def _reset_store(self) -> None:
        """Safely reset the persistent vector store directory with backup and audit logging."""
        try:
            persist_path = Path(self.persist_dir)
            backup_path = None

            # Safety check: ensure we only ever delete within the project tree
            if not (persist_path.is_dir() and str(persist_path).startswith("backend/")):
                logger.error(f"Invalid persist path for reset: {persist_path}")
                raise ValueError(f"Refusing to reset invalid path: {persist_path}")

            # Create backup if data exists
            if persist_path.exists() and any(persist_path.iterdir()):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = persist_path.parent / f"chroma_backup_{timestamp}"
                try:
                    shutil.copytree(persist_path, backup_path)
                    logger.info(f"Created backup of ChromaDB at: {backup_path}")
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup before reset: {backup_error}")
                    backup_path = None

            # Log audit event for the reset
            try:
                from .audit_logger import audit_logger

                audit_logger.log_system_event(
                    event_type="chromadb_reset",
                    details={
                        "persist_dir": str(persist_path),
                        "backup_created": backup_path is not None,
                        "backup_path": str(backup_path) if backup_path else None,
                        "reason": "Configuration error or corruption detected",
                    },
                    severity="high",
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log ChromaDB reset audit event: {audit_error}")

            # Perform the reset
            shutil.rmtree(persist_path, ignore_errors=True)
            logger.warning(f"Reset ChromaDB vector store at {persist_path}")

            # Recreate directory (reinitialize will be handled by caller)
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

            # Log successful reset
            logger.info(f"Successfully reset ChromaDB directory")

        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            raise

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        if not documents or self.vector_store is None:
            return
        try:
            # Chroma only accepts primitive metadata types. Sanitize before upsert.
            sanitized_docs: List[Document] = []
            for doc in documents:
                sanitized_meta = self._sanitize_metadata(doc.metadata)
                # Reuse the same content, replace metadata with sanitized version
                sanitized_docs.append(Document(page_content=doc.page_content, metadata=sanitized_meta))

            self.vector_store.add_documents(sanitized_docs)
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            # Detect malformed underlying DB and auto-recover when allowed
            message = str(e).lower()
            force_rebuild = os.getenv("FORCE_REBUILD_DATA", "false").lower() in {"1", "true", "yes"}
            is_malformed = "database disk image is malformed" in message or "is malformed" in message
            if (isinstance(e, ChromaInternalError) and is_malformed) or (is_malformed and force_rebuild):
                logger.error(f"Chroma store appears corrupted: {e}. Force rebuild: {force_rebuild}")
                if force_rebuild:
                    # Reset the store and retry once
                    self._reset_store()
                    self.vector_store.add_documents(documents)
                    logger.info(f"Recovered vector store and added {len(documents)} documents after reset")
                    return
            # If not recoverable, re-raise
            raise

    def add_documents_for_tenant(
        self, documents: List[Document], tenant_id: str, tenant_slug: Optional[str] = None
    ) -> None:
        """Add documents to the vector store with tenant metadata.

        Args:
            documents: List of documents to add
            tenant_id: UUID string identifying the tenant
            tenant_slug: Optional human-readable tenant identifier
        """
        if not documents or self.vector_store is None:
            return

        # Stamp tenant metadata on all documents
        tenant_docs = []
        for doc in documents:
            metadata = dict(doc.metadata or {})
            metadata["tenant_id"] = tenant_id
            if tenant_slug:
                metadata["tenant_slug"] = tenant_slug
            tenant_docs.append(Document(page_content=doc.page_content, metadata=metadata))

        # Use the standard add_documents method which handles sanitization
        self.add_documents(tenant_docs)

    def get_retriever(
        self, search_kwargs: Optional[Dict] = None, filter_content_types: Optional[List[str]] = None
    ) -> BaseRetriever:
        """
        Get a retriever with optional filtering.

        Args:
            search_kwargs: Additional search parameters (e.g., k=5)
            filter_content_types: Filter by content types (e.g., ['technical', 'experience'])
        """
        if search_kwargs is None:
            search_kwargs = {"k": AppConfig.DEFAULT_SEARCH_K}

        # Note: We'll do filtering at retrieval time instead of at the vector store level
        # This is more compatible across different Chroma versions

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)  # type: ignore[no-any-return]

    def get_relevant_documents(
        self, query: str, k: int = None, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query=query, k=k, filter_content_types=filter_content_types)

    def semantic_search(
        self,
        query: str,
        k: int = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: float = None,
        use_mmr: bool = None,
        metadata_filters: Optional[RetrievalFilters] = None,
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by (legacy parameter, prefer metadata_filters)
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)
            use_mmr: Whether to use MMR (Maximum Marginal Relevance) for diversity (defaults to AppConfig.RAG_USE_MMR)
                           - ChromaDB returns DISTANCE scores (lower = better similarity)
                           - Typical range: 0.0-2.0 with L2 distance
                           - Use 0.0 for no filtering, 0.5-1.0 for good matches, 1.0+ for broader results
            metadata_filters: RetrievalFilters object with strict/soft filter specifications

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        # Apply defaults from config (with dynamic RAG settings support)
        rag_settings = self._get_rag_config_settings()
        sr_settings = self._get_search_retrieval_settings()

        # Derive desired number of results from SearchRetrievalSettings.max_search_results when available
        if k is None:
            if sr_settings and getattr(sr_settings, "max_search_results", None):
                k = int(sr_settings.max_search_results)
            else:
                k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            if rag_settings:
                score_threshold = rag_settings.rag_score_threshold
                logger.debug(f"Using dynamic score threshold: {score_threshold}")
            else:
                score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD
        if use_mmr is None:
            if rag_settings:
                use_mmr = rag_settings.rag_use_mmr
                logger.debug(f"Using dynamic MMR setting: {use_mmr}")
            else:
                use_mmr = AppConfig.get_rag_use_mmr()

        # Get more results than needed for filtering and reranking
        search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        # Build ChromaDB where clause for strict filters
        where_clause = None
        if metadata_filters and metadata_filters.has_filters():
            where_clause = self._build_where_clause(metadata_filters)
            if where_clause:
                logger.info(f"Applying strict metadata filter: {where_clause}")

        def _run_retrieval() -> List[tuple[Document, float]]:
            # Perform search with MMR or standard similarity search
            if use_mmr:
                try:
                    # Use MMR search for diversity (with dynamic settings support)
                    if rag_settings:
                        fetch_k = max(search_k, rag_settings.rag_mmr_fetch_k)
                        lambda_mult = rag_settings.rag_mmr_lambda_mult
                        logger.debug(f"Using dynamic MMR params: fetch_k={fetch_k}, lambda_mult={lambda_mult}")
                    else:
                        fetch_k = max(search_k, AppConfig.RAG_MMR_FETCH_K)
                        lambda_mult = AppConfig.RAG_MMR_LAMBDA_MULT

                    # Note: MMR doesn't support filter parameter in LangChain, so we'll need to fall back
                    if where_clause:
                        logger.warning("MMR search with filters not supported, falling back to similarity search")
                        return self.vector_store.similarity_search_with_score(query, k=search_k, filter=where_clause)

                    docs = self.vector_store.max_marginal_relevance_search(
                        query, k=search_k, fetch_k=fetch_k, lambda_mult=lambda_mult
                    )
                    # Convert to docs_and_scores format for consistent processing
                    return [(doc, 0.0) for doc in docs]  # MMR doesn't return scores
                except Exception as e:
                    logger.warning(f"MMR search failed, falling back to similarity search: {e}")
                    if where_clause:
                        return self.vector_store.similarity_search_with_score(query, k=search_k, filter=where_clause)
                    else:
                        return self.vector_store.similarity_search_with_score(query, k=search_k)
            else:
                # Standard similarity search with optional where clause
                if where_clause:
                    return self.vector_store.similarity_search_with_score(query, k=search_k, filter=where_clause)
                else:
                    return self.vector_store.similarity_search_with_score(query, k=search_k)

        # Enforce retrieval timeout if configured
        docs_and_scores: List[tuple[Document, float]] = []
        timeout_seconds: Optional[int] = None
        if sr_settings and getattr(sr_settings, "search_timeout_seconds", None):
            timeout_seconds = int(sr_settings.search_timeout_seconds)

        if timeout_seconds and timeout_seconds > 0:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_retrieval)
                try:
                    docs_and_scores = future.result(timeout=timeout_seconds)
                except TimeoutError:
                    logger.warning(f"Semantic search timed out after {timeout_seconds}s; returning empty results")
                    docs_and_scores = []
                except Exception as e:
                    logger.error(f"Semantic search failed: {e}")
                    docs_and_scores = []
        else:
            docs_and_scores = _run_retrieval()

        logger.debug(f"Raw search returned {len(docs_and_scores)} documents")
        if docs_and_scores:
            logger.debug(
                f"Score range: {min(score for _, score in docs_and_scores):.3f} - "
                f"{max(score for _, score in docs_and_scores):.3f}"
            )

        # Apply soft reranking for metadata filters
        if metadata_filters and metadata_filters.has_filters() and docs_and_scores:
            logger.debug("Applying soft reranking based on metadata filters")
            docs_and_scores = self._apply_soft_reranking(docs_and_scores, metadata_filters)
            if docs_and_scores:
                logger.debug(
                    f"After soft reranking: {min(score for _, score in docs_and_scores):.3f} - "
                    f"{max(score for _, score in docs_and_scores):.3f}"
                )

        # Filter by distance score threshold
        # IMPORTANT: ChromaDB's similarity_search_with_score returns DISTANCE scores where:
        # - LOWER scores = HIGHER similarity (closer vectors in embedding space)
        # - Typical L2 distance range: 0.0-2.0 (with normalization)
        # - Good matches usually have scores < 1.0
        # - We use <= because we want documents with distance AT OR BELOW the threshold

        if score_threshold == 0.0:
            # Special case: threshold=0.0 means "get all results" (no filtering)
            filtered_docs = [doc for doc, score in docs_and_scores]
        else:
            # Normal case: filter by distance threshold (keep documents with distance <= threshold)
            filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
        logger.debug(f"After score threshold ({score_threshold}): {len(filtered_docs)} documents")

        # Apply additional post-filter by semantic similarity threshold if provided
        # (convert distance to pseudo-similarity)
        # We map distance d to similarity s = 1 / (1 + d), ensuring s in (0,1].
        try:
            if sr_settings and getattr(sr_settings, "semantic_similarity_threshold", None) is not None:
                sim_thr = float(sr_settings.semantic_similarity_threshold)
                if sim_thr > 0.0:

                    def _sim_from_distance(d: float) -> float:
                        try:
                            return 1.0 / (1.0 + float(d))
                        except Exception:
                            return 0.0

                    # Recompute docs_and_scores to include distance for filtering
                    if score_threshold == 0.0:
                        # We didn't keep scores when MMR path used; rebuild with similarity_search_with_score if needed
                        # Only if we have no scores at all
                        if use_mmr and self.vector_store is not None and filtered_docs:
                            # Skip re-query to avoid extra cost; approximate by keeping filtered_docs
                            pass
                        else:
                            pass
                    filtered_docs = [doc for (doc, dist) in docs_and_scores if _sim_from_distance(dist) >= sim_thr]
        except Exception as e:
            logger.debug(f"Similarity post-filter skipped: {e}")

        # Apply content type filtering if specified
        if filter_content_types:
            content_filtered_docs = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_content_types = doc.metadata["content_types"].split(",")
                    logger.debug(f"Doc content types: {doc_content_types}, looking for: {filter_content_types}")
                    # Check if any of the document's content types match our filter
                    if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                        content_filtered_docs.append(doc)
                        logger.debug(f"✅ Match found: {doc_content_types}")
                    else:
                        logger.debug(f"❌ No match: {doc_content_types}")
            filtered_docs = content_filtered_docs
            logger.debug(f"After content type filtering: {len(filtered_docs)} documents")

        # Return top k results
        return filtered_docs[:k]

    def similarity_search_with_score(self, query: str, k: Optional[int] = None) -> List[tuple]:
        """
        Perform similarity search and return documents with scores.

        Args:
            query: Search query text
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        return self.vector_store.similarity_search_with_score(query, k=k)

    def similarity_search_with_score_for_tenant(
        self, query: str, tenant_id: str, k: Optional[int] = None
    ) -> List[tuple]:
        """
        Perform tenant-scoped similarity search and return documents with scores.

        SECURITY: This method ONLY returns documents belonging to the specified tenant.
        There is NO option to include shared documents to prevent cross-tenant data leakage.

        Args:
            query: Search query text
            tenant_id: UUID string identifying the tenant
            k: Number of results to return

        Returns:
            List of (document, score) tuples filtered by tenant (NEVER includes shared documents)
        """
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        # SECURITY: ONLY query for tenant-specific documents - NO shared documents allowed
        tenant_where = {"tenant_id": tenant_id}
        logger.info(f"Searching for tenant {tenant_id[:8]}... with filter: {tenant_where}")
        tenant_results = self.vector_store.similarity_search_with_score(query, k=k * 2, filter=tenant_where)
        logger.info(f"Tenant search returned {len(tenant_results)} results for tenant {tenant_id[:8]}...")

        # Sort by distance score (lower is better)
        tenant_results.sort(key=lambda x: x[1])

        logger.info(f"Returning {len(tenant_results[:k])} tenant-only results")
        return tenant_results[:k]

    def get_collection_count(self) -> int:
        """Get the number of documents in the vector store."""
        if self.vector_store is None:
            return 0
        try:
            return self.vector_store._collection.count()
        except Exception as e:
            logger.warning(f"Could not get collection count: {e}")
            return 0

    def get_count(self, where: Optional[Dict[str, Any]] = None) -> int:
        """Get the number of documents in the vector store with optional filtering."""
        if self.vector_store is None:
            return 0
        try:
            if where:
                # ChromaDB get() no longer accepts 'ids' in include list; request nothing and read returned ids.
                # Fallback to counting returned metadatas if ids are not present.
                try:
                    results = self.vector_store._collection.get(where=where, include=[])
                    ids = results.get("ids", []) if isinstance(results, dict) else getattr(results, "ids", [])
                    if ids is not None:
                        return len(ids)
                except Exception:
                    pass
                try:
                    res2 = self.vector_store._collection.get(where=where, include=["metadatas"])
                    metas = res2.get("metadatas", []) if isinstance(res2, dict) else getattr(res2, "metadatas", [])
                    return len(metas or [])
                except Exception:
                    # Final fallback: fetch documents and count length
                    docs = self.get_documents(where=where, limit=100000, offset=0)
                    return len(docs or [])
            else:
                return self.vector_store._collection.count()
        except AttributeError:
            # Fallback: fetch documents and count them
            docs = self.get_documents(where=where, limit=100000, offset=0)
            return len(docs or [])

    def get_count_for_tenant(self, tenant_id: str) -> int:
        """
        Get the number of documents for a specific tenant.

        SECURITY: ONLY counts documents belonging to the tenant - NO shared documents.
        """
        if self.vector_store is None:
            return 0

        try:
            # SECURITY: ONLY count tenant-specific documents
            tenant_count = self.get_count(where={"tenant_id": tenant_id})
            return tenant_count
        except Exception as e:
            logger.error(f"Error counting documents for tenant {tenant_id}: {e}")
            return 0

    def get_documents(
        self, where: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get documents from the vector store with optional filtering.

        Args:
            where: Optional filter conditions for metadata
            limit: Maximum number of documents to return
            offset: Number of documents to skip (for pagination)

        Returns:
            List of document dictionaries with metadata and content
        """
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        try:
            # Use ChromaDB's get() method which is the proper public interface
            collection = self.vector_store._collection

            # Convert empty where clause to None for ChromaDB compatibility
            where_clause = where if where else None

            result = collection.get(where=where_clause, limit=limit, offset=offset, include=["metadatas", "documents"])

            # Get IDs separately since ChromaDB requires them to be requested explicitly
            ids_result = collection.get(where=where_clause, limit=limit, offset=offset, include=[])

            # Format the results consistently
            documents = []
            ids = ids_result.get("ids", [])
            docs = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            for i in range(len(docs)):
                doc = {
                    "id": ids[i] if i < len(ids) else f"doc_{i}",
                    "content": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
                documents.append(doc)

            return documents
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    def delete_collection(self) -> None:
        """Delete the vector store collection (for testing/cleanup)."""
        if self.vector_store is not None:
            try:
                self.vector_store.delete_collection()
                logger.info("Vector store collection deleted")
            except Exception as e:
                logger.warning(f"Could not delete collection: {e}")

    def delete_where(self, where: Dict[str, Any]) -> None:
        """Delete documents from the underlying store by metadata filter."""
        # Try to access the underlying ChromaDB collection directly
        if hasattr(self.vector_store, "_collection"):
            try:
                # ChromaDB's delete requires at least one of: ids, where, or where_document
                # The where parameter should work for metadata filtering
                self.vector_store._collection.delete(where=where)  # type: ignore[attr-defined]
                logger.info(f"Deleted documents matching filter: {where}")
                return
            except Exception as e:
                logger.warning("Chroma _collection.delete failed: %s", e, exc_info=True)

        # Fallback: Query for matching documents and delete by ID
        if hasattr(self.vector_store, "get") and hasattr(self.vector_store, "delete"):
            try:
                # First get documents matching the filter
                results = self.vector_store.get(where=where)  # type: ignore[attr-defined]
                if results and "ids" in results and results["ids"]:
                    # Delete by IDs
                    self.vector_store.delete(ids=results["ids"])  # type: ignore[attr-defined]
                    logger.info(f"Deleted {len(results['ids'])} documents matching filter: {where}")
                    return
            except Exception as e:
                logger.warning("Fallback delete by ID failed: %s", e, exc_info=True)

        # If no delete mechanism works, log but don't fail
        logger.warning(f"Could not delete documents with filter {where} - continuing anyway")

    def reset_store(self) -> None:
        """Reset and reinitialize the vector store."""
        self.delete_collection()
        self._initialize_store()
        logger.info("Vector store reset and reinitialized")

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by its ID."""
        if self.vector_store is None:
            return None

        try:
            # Use the public get method instead of _collection
            result = self.vector_store._collection.get(ids=[document_id], include=["metadatas", "documents"])

            if result["ids"] and len(result["ids"]) > 0:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID {document_id}: {e}")
            return None

    def update_document_metadata(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a document."""
        if self.vector_store is None:
            return False

        try:
            # Use the standardized sanitization for consistent metadata handling
            sanitized_metadata = self._sanitize_metadata(metadata)
            self.vector_store._collection.update(ids=[document_id], metadatas=[sanitized_metadata])
            return True
        except Exception as e:
            logger.error(f"Error updating document metadata for {document_id}: {e}")
            return False

    def delete_document_by_id(self, document_id: str) -> bool:
        """Delete a document by its ID."""
        if self.vector_store is None:
            return False

        try:
            self.vector_store._collection.delete(ids=[document_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def get_documents_by_source(self, source_path: str) -> List[Dict[str, Any]]:
        """Get all documents from a specific source."""
        if self.vector_store is None:
            return []

        try:
            result = self.vector_store._collection.get(
                where={"source": source_path}, include=["metadatas", "documents"]
            )
            # Get IDs separately
            ids_result = self.vector_store._collection.get(where={"source": source_path}, include=[])

            documents = []
            ids = ids_result.get("ids", [])
            docs = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            for i in range(len(docs)):
                doc = {
                    "id": ids[i] if i < len(ids) else f"doc_{i}",
                    "content": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
                documents.append(doc)
            return documents
        except Exception as e:
            logger.error(f"Error getting documents by source {source_path}: {e}")
            return []

    def update_documents_metadata(self, document_ids: List[str], metadatas: List[Dict[str, Any]]) -> bool:
        """Update metadata for multiple documents."""
        if self.vector_store is None:
            return False

        try:
            # Use the standardized sanitization for consistent metadata handling
            compatible_metadatas = [self._sanitize_metadata(metadata) for metadata in metadatas]
            self.vector_store._collection.update(ids=document_ids, metadatas=compatible_metadatas)  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error updating multiple document metadata: {e}")
            return False

    def delete_documents_by_source(self, source_path: str) -> bool:
        """Delete all documents from a specific source."""
        if self.vector_store is None:
            return False

        try:
            # First get the documents to find their IDs
            documents = self.get_documents_by_source(source_path)
            if not documents:
                return True  # Nothing to delete

            document_ids = [doc["id"] for doc in documents]
            self.vector_store._collection.delete(ids=document_ids)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents by source {source_path}: {e}")
            return False
