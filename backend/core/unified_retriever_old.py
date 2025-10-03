"""
Unified retriever system with automatic content discovery and intelligent routing.

This module provides a single, intelligent retriever that automatically:
- Discovers and indexes all content
- Adds rich metadata for filtering
- Routes queries based on semantic similarity
- Maintains performance through smart caching
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

# Prefer the newer Chroma package
try:
    from langchain_chroma import Chroma  # type: ignore
except ImportError:
    # Fallback to community version if new package not available
    from langchain_community.vectorstores import Chroma  # type: ignore

from ..ingest.chunking import splitter_for_ext
from ..ingest.loaders import load_doc
from .config_v2 import AppConfig
from .llm_utils import extract_topics_with_llm

logger = logging.getLogger(__name__)


class UnifiedRetriever:
    """A single retriever that intelligently handles all content types."""

    def __init__(self, embeddings: Any, llm: BaseLanguageModel, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.llm = llm
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        self._document_contexts: Dict[str, str] = {}  # Cache for document contexts
        self._initialize_store()

    def _initialize_store(self):
        """Initialize or load the unified vector store."""
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.vector_store = Chroma(
            collection_name="unified_knowledge",
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
        )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_content_metadata(
        self, doc: Document, file_path: Path, tenant_id: Optional[str] = None, tenant_slug: Optional[str] = None
    ) -> Dict:
        """Extract metadata using LLM topics plus deterministic fallbacks.

        Heuristics ensure key content remains discoverable even if LLM topic extraction fails.
        """
        content = doc.page_content

        # Use LLM to extract topics for dynamic content tagging (may fallback to ["general"])
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

        # Determine scope based on file path
        scope = "shared"  # Default scope for shared content
        if tenant_id:
            # Check if this is tenant-specific content based on path
            if "/tenants/" in str(file_path) or "tenant" in str(file_path).lower():
                scope = "tenant"
            else:
                scope = "shared"

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_types": ",".join(merged_types),
            "content_length": len(content),
            "has_code": "```" in doc.page_content or "function" in text_lc,
            "is_illustration_data": is_illustration_data,
            "scope": scope,
            "source": str(file_path),  # Add explicit source for tenant filtering
        }

        # Add tenant metadata if provided
        if tenant_id:
            metadata["tenant_id"] = tenant_id
        if tenant_slug:
            metadata["tenant_slug"] = tenant_slug

        # Add illustration file path for frontend display
        if illustration_file:
            metadata["illustration_file"] = illustration_file
            metadata["display_path"] = f"/illustrations/{illustration_file}"

        return metadata

    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed based on its name and type."""
        # Skip system/config files that aren't content
        skip_files = {"robots.txt", "sitemap.xml", ".htaccess", "favicon.ico", "manifest.json"}

        if file_path.name.lower() in skip_files:
            logger.debug(f"Skipping system file: {file_path}")
            return False

        return True

    def _should_skip_file(
        self, file_path: Path, file_hash: str, indexed_files: Dict[str, str], force_reindex: bool
    ) -> bool:
        """Check if a file should be skipped during indexing."""
        return str(file_path) in indexed_files and indexed_files[str(file_path)] == file_hash and not force_reindex

    def index_directory(
        self,
        directory: str,
        force_reindex: bool = False,
        tenant_id: Optional[str] = None,
        tenant_slug: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Automatically discover and index all content in a directory.

        Args:
            directory: Directory path to index
            force_reindex: Whether to force reindexing of existing files
            tenant_id: Optional tenant UUID for tenant-scoped content
            tenant_slug: Optional tenant slug for tenant-scoped content

        Returns:
            Tuple of (files_indexed, total_chunks)
        """
        base_path = Path(directory)
        if not base_path.exists():
            logger.warning(f"Directory {directory} does not exist")
            return 0, 0

        # Track indexed files
        index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
        indexed_files = {}

        if index_metadata_path.exists() and not force_reindex:
            with open(index_metadata_path, "r") as f:
                indexed_files = json.load(f)

        files_indexed = 0
        total_chunks = 0

        # Discover all files
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith(".") and self._should_index_file(file_path):
                logger.info(f"Processing file: {file_path}")
                file_hash = self._compute_file_hash(file_path)

                # Skip if already indexed and unchanged
                should_skip = self._should_skip_file(file_path, file_hash, indexed_files, force_reindex)
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

                    # Add rich metadata to each chunk including tenant information
                    for chunk in chunks:
                        base_metadata = self._extract_content_metadata(chunk, file_path, tenant_id, tenant_slug)
                        chunk.metadata.update(base_metadata)

                    # Add to vector store using tenant-aware method if tenant specified
                    if chunks and self.vector_store is not None:
                        if tenant_id:
                            # Use SemanticSearcher's tenant-aware method if available
                            if hasattr(self.vector_store, "add_documents_for_tenant"):
                                self.vector_store.add_documents_for_tenant(chunks, tenant_id, tenant_slug)
                            else:
                                # Fallback: ensure chunks already have tenant metadata stamped
                                self.vector_store.add_documents(chunks)
                        else:
                            # Standard indexing for shared content
                            self.vector_store.add_documents(chunks)
                        files_indexed += 1
                        total_chunks += len(chunks)
                        indexed_files[str(file_path)] = file_hash
                        logger.info(f"Indexed {file_path.name}: {len(chunks)} chunks (tenant_id: {tenant_id})")

                except Exception as e:
                    logger.error(f"Failed to index {file_path}: {e}")

        # Save index metadata
        with open(index_metadata_path, "w") as f:
            json.dump(indexed_files, f)

        return files_indexed, total_chunks

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
        self, query: str, k: int = 8, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query=query, k=k, filter_content_types=filter_content_types)

    def semantic_search(
        self, query: str, k: int = None, filter_content_types: Optional[List[str]] = None, score_threshold: float = None
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)
                           - ChromaDB returns DISTANCE scores (lower = better similarity)
                           - Typical range: 0.0-2.0 with L2 distance
                           - Use 0.0 for no filtering, 0.5-1.0 for good matches, 1.0+ for broader results

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        # Apply defaults from config
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD

        # Get more results than needed for filtering and reranking
        search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=search_k)

        logger.debug(f"Raw search returned {len(docs_and_scores)} documents")
        if docs_and_scores:
            logger.debug(
                f"Score range: {min(score for _, score in docs_and_scores):.3f} - "
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

    def semantic_search_for_tenant(
        self,
        query: str,
        tenant_id: str,
        k: int = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: float = None,
        include_shared: bool = True,
    ) -> List[Document]:
        """
        Perform tenant-scoped semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            tenant_id: UUID string identifying the tenant
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results
            include_shared: Whether to include shared content in results

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        # Apply defaults from config
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD

        # Use the vector store's tenant-aware method if available
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        if hasattr(self.vector_store, "similarity_search_with_score_for_tenant"):
            docs_and_scores = self.vector_store.similarity_search_with_score_for_tenant(
                query, tenant_id, k=k * AppConfig.SEARCH_EXPANSION_MULTIPLIER, include_shared=include_shared
            )
        else:
            # Fallback: use regular search but filter results by tenant
            docs_and_scores = self.vector_store.similarity_search_with_score(
                query, k=k * AppConfig.SEARCH_EXPANSION_MULTIPLIER
            )
            # Filter by tenant_id in metadata
            filtered_results = []
            for doc, score in docs_and_scores:
                doc_tenant_id = doc.metadata.get("tenant_id")
                doc_scope = doc.metadata.get("scope", "tenant")
                if doc_tenant_id == tenant_id or (include_shared and doc_scope == "shared"):
                    filtered_results.append((doc, score))
            docs_and_scores = filtered_results

        logger.debug(f"Tenant search returned {len(docs_and_scores)} documents for tenant {tenant_id}")
        if docs_and_scores:
            logger.debug(
                f"Score range: {min(score for _, score in docs_and_scores):.3f} - "
                f"{max(score for _, score in docs_and_scores):.3f}"
            )

        # Apply score threshold filtering
        if score_threshold == 0.0:
            filtered_docs = [doc for doc, score in docs_and_scores]
        else:
            filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
        logger.debug(f"After score threshold ({score_threshold}): {len(filtered_docs)} documents")

        # Apply content type filtering if specified
        if filter_content_types:
            content_filtered_docs = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_content_types = doc.metadata["content_types"].split(",")
                    if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                        content_filtered_docs.append(doc)
            filtered_docs = content_filtered_docs
            logger.debug(f"After content type filtering: {len(filtered_docs)} documents")

        return filtered_docs[:k]

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!
        """
        query_lower = query.lower()

        # Intelligent content type detection based on query
        content_type_hints = []

        if any(term in query_lower for term in ["experience", "work", "job", "role", "company", "resume", "cv"]):
            content_type_hints.append("experience")

        if any(term in query_lower for term in ["skill", "technology", "expertise", "know"]):
            content_type_hints.append("skills")

        if any(term in query_lower for term in ["about", "who", "background", "interest"]):
            content_type_hints.append("about")

        # Creative/inspiration queries
        if any(
            term in query_lower for term in ["illustration", "art", "design", "creative", "inspiration", "artistic"]
        ):
            content_type_hints.append("creative")
        if "inspiration" in query_lower or "artistic" in query_lower:
            # Inspiration often overlaps with bio/about content
            content_type_hints.append("about")

        if any(term in query_lower for term in ["project", "built", "created", "developed"]):
            content_type_hints.append("project")

        # Perform search with intelligent filtering
        if content_type_hints:
            # Use generous distance thresholds to ensure good coverage
            # Since ChromaDB returns distance scores (lower=better), higher threshold = more inclusive
            initial_threshold = AppConfig.INCLUSIVE_DISTANCE_THRESHOLD  # Include good to fair matches
            k_value = AppConfig.EXPANDED_SEARCH_K  # Get more results to ensure comprehensive coverage

            # First try filtered search
            results = self.semantic_search(
                query, k=k_value, filter_content_types=content_type_hints, score_threshold=initial_threshold
            )

            # If not enough results, broaden the search with even higher threshold
            if len(results) < (AppConfig.EXPANDED_SEARCH_K // 2):
                additional_results = self.semantic_search(
                    query,
                    k=AppConfig.EXPANDED_SEARCH_K - len(results),
                    score_threshold=AppConfig.BROAD_DISTANCE_THRESHOLD,
                )
                results.extend(additional_results)
        else:
            # No specific type detected, do general search with generous distance threshold
            results = self.semantic_search(
                query, k=AppConfig.EXPANDED_SEARCH_K, score_threshold=AppConfig.INCLUSIVE_DISTANCE_THRESHOLD
            )

        return results

    def _enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
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

    def _generate_document_context(self, documents: List[Document], file_path: Path) -> str:
        """Generate or retrieve cached document context using LLM."""
        from .llm_utils import generate_document_context

        file_key = str(file_path)

        # Return cached context if available
        if file_key in self._document_contexts:
            return self._document_contexts[file_key]

        # Use document content to generate meaningful context
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
