"""
Public knowledge base API routes (read-only).

Provides public endpoints for:
- Viewing indexed documents
- Document statistics and analytics
- Read-only access to knowledge base content

NO write operations are exposed through these endpoints.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class IndexedDocument(BaseModel):
    """Model for indexed document data."""

    id: str
    source: str
    content_preview: str
    content_type: str
    metadata: dict
    word_count: int


class IndexedDocumentsResponse(BaseModel):
    """Response model for indexed documents listing."""

    documents: List[IndexedDocument]
    total_count: int
    collection_name: str
    embedding_model: str


class KnowledgeStats(BaseModel):
    """Model for knowledge base statistics."""

    total_documents: int
    total_chunks: int
    unique_sources: int
    content_types: dict
    last_updated: Optional[str] = None


@router.get("/knowledge/documents", response_model=IndexedDocumentsResponse)
async def get_indexed_documents(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    source_filter: Optional[str] = Query(None, description="Filter by source path"),
):
    """
    Get indexed documents from the knowledge base (read-only).

    Args:
        limit: Maximum number of documents to return
        offset: Offset for pagination
        content_type: Optional filter by content type
        source_filter: Optional filter by source path
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Build query filter
        where_clause = {}
        if content_type:
            where_clause["content_type"] = content_type
        if source_filter:
            where_clause["source"] = {"$contains": source_filter}

        # Get documents using proper encapsulated method
        try:
            result_docs = retriever.semantic_searcher.get_documents(
                where=where_clause if where_clause else None, limit=limit, offset=offset
            )
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            raise HTTPException(status_code=503, detail="Failed to retrieve documents")

        # Format documents for response
        documents = []
        for doc in result_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", "")

            # Create content preview (first 200 characters)
            preview = content[:200] + "..." if len(content) > 200 else content

            documents.append(
                IndexedDocument(
                    id=doc_id,
                    source=metadata.get("source", "unknown"),
                    content_preview=preview,
                    content_type=metadata.get("content_type", "unknown"),
                    metadata=metadata,
                    word_count=len(content.split()) if content else 0,
                )
            )

        # Get total count using filtered count if applicable
        total_count = retriever.semantic_searcher.get_count(where=where_clause or None)

        # Get collection info
        collection_name = "unified_knowledge"  # This is hardcoded in SemanticSearcher
        embedding_model = "text-embedding-3-small"  # Default embedding model from config

        return IndexedDocumentsResponse(
            documents=documents,
            total_count=total_count,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_indexed_documents: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(request: Request):
    """
    Get statistics about the knowledge base (read-only).
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get all documents metadata using encapsulated method
        all_docs = retriever.semantic_searcher.get_documents(limit=100000)  # Get all documents

        if not all_docs:
            return KnowledgeStats(total_documents=0, total_chunks=0, unique_sources=0, content_types={})

        # Calculate statistics
        total_chunks = len(all_docs)

        # Count unique sources and content types
        sources = set()
        content_types = {}

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            if metadata:
                source = metadata.get("source", "unknown")
                sources.add(source)

                ct = metadata.get("content_type", "unknown")
                if ct and ct != "unknown":
                    # Split comma-separated content types and process individually
                    individual_types = [
                        t.strip()
                        for t in ct.split(",")
                        if t.strip()
                        and not t.strip().startswith("based on")
                        and not t.strip().startswith("the main topics")
                    ]
                    for content_type in individual_types:
                        # Skip overly descriptive text, keep only core content type words
                        if (
                            len(content_type) > 50
                            or "based on" in content_type.lower()
                            or "main topics" in content_type.lower()
                        ):
                            continue
                        content_types[content_type] = content_types.get(content_type, 0) + 1
                else:
                    content_types["unknown"] = content_types.get("unknown", 0) + 1

        return KnowledgeStats(
            total_documents=total_chunks,
            total_chunks=total_chunks,
            unique_sources=len(sources),
            content_types=content_types,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/sources")
async def get_knowledge_sources(request: Request):
    """
    Get list of all unique sources in the knowledge base (read-only).
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get all documents metadata using encapsulated method
        all_docs = retriever.semantic_searcher.get_documents(limit=100000)  # Get all documents

        if not all_docs:
            return {"sources": [], "total": 0}

        # Collect unique sources with counts
        source_counts = {}

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            if metadata:
                source = metadata.get("source", "unknown")
                content_type = metadata.get("content_type", "unknown")

                if source not in source_counts:
                    # Provide both full path and display path for frontend
                    display_path = source
                    if source.startswith("backend/knowledge/"):
                        display_path = source.replace("backend/knowledge/", "")
                    elif source.startswith("public/"):
                        display_path = source.replace("public/", "")

                    source_counts[source] = {
                        "display_path": display_path,  # Clean path for frontend display
                        "content_type": content_type,
                        "chunk_count": 0,
                    }
                source_counts[source]["chunk_count"] += 1

        # Convert to list and sort by display_path
        sources = list(source_counts.values())
        sources.sort(key=lambda x: x["display_path"])

        return {"sources": sources, "total_count": len(sources)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_sources: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/documents/{document_id}")
async def get_document_content(request: Request, document_id: str):
    """
    Get full content of a specific document by ID (read-only).

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        Document with full content and metadata
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the document using encapsulated method
        document_data = retriever.semantic_searcher.get_document_by_id(document_id)

        if not document_data:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Extract document data
        metadata = document_data.get("metadata", {})
        content = document_data.get("content", "")

        # Count words
        word_count = len(content.split()) if content else 0

        return {
            "id": document_id,
            "source": metadata.get("source", "Unknown"),
            "content": content,
            "content_type": metadata.get("content_type", "unknown"),
            "metadata": metadata,
            "word_count": word_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document content: {str(e)}")
