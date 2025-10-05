"""
Smart query handler that uses unified retriever for intelligent responses.

This module provides intelligent query handling without manual configuration:
- Automatic query understanding
- Smart content routing
- Performance optimization through caching
- Better context selection
"""

import logging
import time
from typing import Any, Dict, List, Optional

from langchain.schema import Document
from langchain_core.language_models import BaseLanguageModel

from .config_v2 import AppConfig
from .fast_query_classifier import FastQueryClassifier
from .llm_utils import analyze_query_with_llm
from .performance_config import PerformanceConfig, performance_monitor
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartQueryHandler:
    """Handles queries intelligently using the unified retriever."""

    def __init__(self, unified_retriever: UnifiedRetriever, llm: BaseLanguageModel, use_fast_classifier: bool = True):
        self.unified_retriever = unified_retriever
        self.llm = llm
        self._query_cache: Dict[str, List[Document]] = {}  # Simple cache for repeated queries
        self.use_fast_classifier = use_fast_classifier
        self.fast_classifier = FastQueryClassifier() if use_fast_classifier else None

    def analyze_query_fast(self, query: str) -> Dict[str, Any]:
        """Fast query analysis without LLM - 10-50ms instead of 1-2 seconds."""
        start_time = time.time()

        # Check if fast classifier is enabled and available
        if self.use_fast_classifier and self.fast_classifier and PerformanceConfig.ENABLE_FAST_QUERY_CLASSIFIER:

            result = self.fast_classifier.classify(query)
            duration_ms = (time.time() - start_time) * 1000

            # Record performance metrics
            performance_monitor.record_query_analysis_time(duration_ms)
            performance_monitor.record_llm_call_count(0)  # No LLM calls used

            logger.debug(f"Fast query analysis completed in {duration_ms:.1f}ms")
            return result
        else:
            # Fallback to LLM analysis (slower)
            logger.warning("Fast classifier not available or disabled, falling back to LLM analysis")
            result = analyze_query_with_llm(self.llm, query)

            duration_ms = (time.time() - start_time) * 1000
            performance_monitor.record_query_analysis_time(duration_ms)
            performance_monitor.record_llm_call_count(1)  # One LLM call used

            return result

    async def get_relevant_context_async(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        max_context_length: int = None,
        tenant_id: Optional[str] = None,
    ) -> List[Document]:
        """
        Async version of get_relevant_context with enhanced performance and tenant support.
        """
        # Apply default from config
        if max_context_length is None:
            max_context_length = AppConfig.DEFAULT_MAX_CONTEXT_LENGTH

        # Include tenant_id in cache key to prevent cross-tenant data leakage
        cache_key = f"{query}:{len(chat_history) if chat_history else 0}:tenant:{tenant_id or 'none'}"
        if cache_key in self._query_cache:
            logger.info("Using cached results for query")
            return self._query_cache[cache_key]

        # SECURITY: Use tenant-aware routing if tenant_id provided (tenant-only, NO shared)
        if tenant_id and hasattr(self.unified_retriever, "semantic_search_for_tenant"):
            docs = self.unified_retriever.semantic_search_for_tenant(query, tenant_id)
        else:
            # Fallback to standard routing for non-tenant queries or unsupported retrievers
            docs = self.unified_retriever.auto_route_query(query)

        # Post-process documents for quality
        processed_docs = self._post_process_documents(docs, query, max_context_length)

        # Cache results
        self._query_cache[cache_key] = processed_docs

        # Limit cache size
        if len(self._query_cache) > AppConfig.MAX_CACHE_SIZE:
            # Remove oldest entries
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        return processed_docs

    def get_relevant_context(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        max_context_length: int = None,
        tenant_id: Optional[str] = None,
        explicit_filters=None,
    ) -> List[Document]:
        """
        Get the most relevant context for a query with tenant support.

        This method:
        1. Analyzes the query to understand intent
        2. Retrieves relevant documents (tenant-scoped if tenant_id provided)
        3. Ranks and filters for quality
        4. Ensures context fits within token limits

        Args:
            query: Search query text
            chat_history: Optional chat history for context
            max_context_length: Maximum context length in characters
            tenant_id: Optional tenant ID for tenant-scoped search
            explicit_filters: Optional RetrievalFilters object for metadata filtering
        """
        # Apply default from config
        if max_context_length is None:
            max_context_length = AppConfig.DEFAULT_MAX_CONTEXT_LENGTH

        # Include tenant_id and filters in cache key to prevent cross-tenant data leakage
        filter_key = str(explicit_filters) if explicit_filters else "none"
        cache_key = f"{query}:{len(chat_history) if chat_history else 0}:tenant:{tenant_id or 'none'}:filters:{filter_key}"
        if cache_key in self._query_cache:
            logger.info("Using cached results for query")
            return self._query_cache[cache_key]

        # SECURITY: Use tenant-aware routing if tenant_id provided (tenant-only, NO shared)
        if tenant_id and hasattr(self.unified_retriever, "semantic_search_for_tenant"):
            docs = self.unified_retriever.semantic_search_for_tenant(query, tenant_id)
        else:
            # Fallback to standard routing for non-tenant queries or unsupported retrievers
            docs = self.unified_retriever.auto_route_query(query, explicit_filters=explicit_filters)

        # Post-process documents for quality
        processed_docs = self._post_process_documents(docs, query, max_context_length)

        # Cache results
        self._query_cache[cache_key] = processed_docs

        # Limit cache size
        if len(self._query_cache) > AppConfig.MAX_CACHE_SIZE:
            # Remove oldest entries
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        return processed_docs

    def _post_process_documents(self, docs: List[Document], query: str, max_context_length: int) -> List[Document]:
        """
        Post-process documents to ensure quality and fit within limits.
        Optimized for speed and context efficiency.
        """
        if not docs:
            return []

        # Quick deduplication based on content similarity
        unique_docs = []
        seen_content = set()

        for doc in docs:
            # Create a content fingerprint
            content_fingerprint = doc.page_content[: AppConfig.CONTENT_FINGERPRINT_LENGTH].lower().strip()
            if content_fingerprint not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_fingerprint)

        # Skip expensive LLM re-ranking for speed - use simple relevance scoring instead
        # This saves 1-2 seconds per request
        scored_docs = []
        query_words = set(query.lower().split())

        for doc in unique_docs:
            # Simple relevance score based on query word overlap
            doc_words = set(doc.page_content.lower().split())
            overlap_score = len(query_words.intersection(doc_words))

            # Boost score for shorter, more focused documents
            length_penalty = len(doc.page_content) / AppConfig.LENGTH_PENALTY_DIVISOR  # Penalty for very long docs
            relevance_score = overlap_score - (length_penalty * 0.1)

            scored_docs.append((relevance_score, doc))

        # Sort by relevance score (highest first)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        reranked_docs = [doc for _, doc in scored_docs]

        # Smart context selection - prioritize quality over quantity
        selected_docs = []
        current_length = 0
        target_docs = min(AppConfig.MAX_CONTEXT_DOCUMENTS, len(reranked_docs))  # Limit to top N most relevant docs

        for doc in reranked_docs[:target_docs]:
            doc_length = len(doc.page_content)

            if current_length + doc_length <= max_context_length:
                selected_docs.append(doc)
                current_length += doc_length
            elif (
                current_length < max_context_length * AppConfig.CONTEXT_FILL_RATIO
            ):  # If we have less than configured ratio filled
                # Intelligently truncate the document to essential parts
                remaining_space = max_context_length - current_length

                # Try to keep the most relevant parts (first and last parts often most important)
                if doc_length > remaining_space:
                    first_half = remaining_space // 2
                    second_half = remaining_space - first_half

                    truncated_content = doc.page_content[:first_half] + "\n...\n" + doc.page_content[-second_half:]

                    truncated_doc = Document(
                        page_content=truncated_content, metadata={**doc.metadata, "truncated": True}
                    )
                    selected_docs.append(truncated_doc)
                    break
            else:
                # We have enough context
                break

        return selected_docs

    def analyze_query_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to understand user intent using an LLM.
        """
        return analyze_query_with_llm(self.llm, query)
