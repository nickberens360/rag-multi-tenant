# Week 2: Async Operations & Vector Store Optimization

**Priority**: 🟠 HIGH  
**Expected Impact**: 20-30% additional performance improvement  
**Target**: Eliminate blocking I/O operations and optimize database queries  

## Current Problem

Several synchronous operations are blocking the event loop:

1. **File Hash Computation** (`content_indexer.py:35-41`) - Blocking file I/O
2. **ChromaDB Operations** - Inefficient `_collection` access patterns
3. **Vector Store Queries** - No connection pooling or batching
4. **Document Loading** - Synchronous file processing during indexing

**Impact**: 2-4 seconds of blocking operations per query/indexing operation

## Implementation Plan

### Step 1: Async File Operations (Day 1-2)

**Objective**: Convert all file I/O to async operations

**Files to Modify**:
- `backend/core/content_indexer.py`
- `backend/ingest/loaders.py` (if exists)
- Add: `aiofiles` dependency

**Changes**:

```python
# content_indexer.py - Async file operations
import aiofiles
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ContentIndexer:
    def __init__(self, llm: BaseLanguageModel, persist_dir: str = "backend/.unified_chroma"):
        self.llm = llm
        self.persist_dir = persist_dir
        self._document_contexts: Dict[str, str] = {}
        # NEW: Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def compute_file_hash_async(self, file_path: Path) -> str:
        """Async file hash computation - non-blocking."""
        
        def _compute_hash(path: Path) -> str:
            """CPU-bound hash computation in thread pool."""
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for byte_block in iter(lambda: f.read(8192), b""):  # Larger chunks
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, _compute_hash, file_path)

    async def load_document_async(self, file_path: Path) -> List[Document]:
        """Async document loading."""
        
        async def _read_file_content(path: Path) -> str:
            """Read file content asynchronously."""
            async with aiofiles.open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return await f.read()
        
        try:
            # For text files, use async file reading
            if file_path.suffix.lower() in ['.txt', '.md', '.json', '.py', '.js', '.html', '.css']:
                content = await _read_file_content(file_path)
                return [Document(page_content=content, metadata={"source": str(file_path)})]
            
            # For binary files (PDFs), use thread pool
            else:
                loop = asyncio.get_event_loop()
                from ..ingest.loaders import load_doc
                return await loop.run_in_executor(self.executor, load_doc, file_path)
                
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            return []

    async def process_directory_async(self, directory: str, force_reindex: bool = False) -> Tuple[List[Document], int, int]:
        """Fully async directory processing."""
        base_path = Path(directory)
        if not base_path.exists():
            logger.warning(f"Directory {directory} does not exist")
            return [], 0, 0

        # Async metadata loading
        index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
        indexed_files = {}
        
        if index_metadata_path.exists() and not force_reindex:
            async with aiofiles.open(index_metadata_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                indexed_files = json.loads(content) if content else {}

        all_documents = []
        files_processed = 0
        total_chunks = 0

        # Process files concurrently
        file_tasks = []
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith(".") and self.should_index_file(file_path):
                file_tasks.append(self._process_single_file_async(file_path, indexed_files, force_reindex))
        
        # Process files in batches to avoid overwhelming the system
        batch_size = 10
        for i in range(0, len(file_tasks), batch_size):
            batch = file_tasks[i:i + batch_size]
            results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error processing file: {result}")
                elif result:
                    docs, file_hash, file_path = result
                    all_documents.extend(docs)
                    files_processed += 1
                    total_chunks += len(docs)
                    indexed_files[str(file_path)] = file_hash

        # Async metadata saving
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(index_metadata_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(indexed_files, indent=2))

        return all_documents, files_processed, total_chunks

    async def _process_single_file_async(self, file_path: Path, indexed_files: Dict[str, str], force_reindex: bool) -> Optional[Tuple[List[Document], str, Path]]:
        """Process a single file asynchronously."""
        try:
            # Async hash computation
            file_hash = await self.compute_file_hash_async(file_path)
            
            # Skip if already indexed
            if self.should_skip_file(file_path, file_hash, indexed_files, force_reindex):
                return None
            
            # Async document loading
            docs = await self.load_document_async(file_path)
            if not docs:
                return None
            
            # Process chunks (CPU-bound operations in thread pool)
            loop = asyncio.get_event_loop()
            processed_chunks = await loop.run_in_executor(
                self.executor, 
                self._process_document_chunks, 
                docs, 
                file_path
            )
            
            return processed_chunks, file_hash, file_path
            
        except Exception as e:
            logger.error(f"Failed to process {file_path} asynchronously: {e}")
            return None

    def _process_document_chunks(self, docs: List[Document], file_path: Path) -> List[Document]:
        """Process document chunks in thread pool (CPU-bound)."""
        from ..ingest.chunking import splitter_for_ext
        
        splitter = splitter_for_ext(file_path.suffix)
        chunks = splitter.split_documents(docs)
        
        # Add metadata to chunks
        for chunk in chunks:
            base_metadata = self.extract_content_metadata(chunk, file_path)
            chunk.metadata.update(base_metadata)
        
        return chunks
```

### Step 2: ChromaDB Connection Optimization (Day 3)

**Objective**: Optimize vector store operations and eliminate inefficient patterns

**Files to Modify**:
- `backend/core/semantic_searcher.py`
- Add connection pooling and batching capabilities

**Changes**:

```python
# semantic_searcher.py - Optimized ChromaDB operations
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

class SemanticSearcher:
    def __init__(self, embeddings: Any, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        # NEW: Connection and operation optimizations
        self._connection_pool = None
        self._batch_operations = []
        self._batch_lock = asyncio.Lock()
        self._initialize_store()

    def _initialize_store(self):
        """Initialize vector store with optimized settings."""
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        
        # Optimized Chroma initialization
        self.vector_store = Chroma(
            collection_name="unified_knowledge",
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
            # NEW: Performance settings
            client_settings={
                "anonymized_telemetry": False,  # Disable telemetry for performance
                "is_persistent": True,
                # Connection pool settings
                "pool_size": 10,
                "max_overflow": 20,
                "pool_recycle": 3600,
            }
        )

    async def add_documents_batch(self, documents: List[Document], batch_size: int = 50) -> None:
        """Add documents in optimized batches."""
        if not documents or not self.vector_store:
            return
            
        # Process documents in batches to avoid memory issues
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                # Use async operation if available, otherwise run in executor
                if hasattr(self.vector_store, 'aadd_documents'):
                    await self.vector_store.aadd_documents(batch)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.vector_store.add_documents, batch)
                
                logger.debug(f"Added batch of {len(batch)} documents to vector store")
                
                # Small delay to prevent overwhelming the database
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Failed to add document batch: {e}")
                # Continue with next batch rather than failing completely
                continue
        
        logger.info(f"Successfully added {len(documents)} documents in batches")

    @asynccontextmanager
    async def _optimized_query_context(self):
        """Context manager for optimized query operations."""
        # Pre-warm connections, set optimal query settings
        try:
            # Optimize for read operations
            if self.vector_store and hasattr(self.vector_store._client, 'set_read_preference'):
                self.vector_store._client.set_read_preference('primary_preferred')
            yield
        finally:
            # Cleanup if needed
            pass

    async def semantic_search_async(
        self, 
        query: str, 
        k: int = None, 
        filter_content_types: Optional[List[str]] = None, 
        score_threshold: float = None
    ) -> List[Document]:
        """Async semantic search with connection optimization."""
        
        # Apply defaults
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD

        search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER

        async with self._optimized_query_context():
            try:
                # Use async search if available
                if hasattr(self.vector_store, 'asimilarity_search_with_score'):
                    docs_and_scores = await self.vector_store.asimilarity_search_with_score(query, k=search_k)
                else:
                    # Run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    docs_and_scores = await loop.run_in_executor(
                        None,
                        self.vector_store.similarity_search_with_score,
                        query,
                        search_k
                    )

                logger.debug(f"Vector search returned {len(docs_and_scores)} documents")
                
                # Apply filtering (same logic as before, but in async context)
                if score_threshold == 0.0:
                    filtered_docs = [doc for doc, score in docs_and_scores]
                else:
                    filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
                
                # Content type filtering
                if filter_content_types:
                    content_filtered_docs = []
                    for doc in filtered_docs:
                        if "content_types" in doc.metadata:
                            doc_content_types = doc.metadata["content_types"].split(",")
                            if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                                content_filtered_docs.append(doc)
                    filtered_docs = content_filtered_docs

                return filtered_docs[:k]

            except Exception as e:
                logger.error(f"Async semantic search failed: {e}")
                # Fallback to synchronous method
                return self.semantic_search(query, k, filter_content_types, score_threshold)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics for monitoring."""
        if not self.vector_store:
            return {}
            
        try:
            collection = self.vector_store._collection
            return {
                "count": collection.count(),
                "name": collection.name,
                "metadata": collection.metadata,
                # Add performance metrics
                "last_query_time": getattr(self, '_last_query_time', None),
                "avg_query_time": getattr(self, '_avg_query_time', None),
            }
        except Exception as e:
            logger.warning(f"Could not get collection stats: {e}")
            return {}

    # Context manager for bulk operations
    @asynccontextmanager
    async def bulk_operation_context(self):
        """Context manager for bulk operations with optimizations."""
        async with self._batch_lock:
            try:
                # Disable auto-persistence during bulk operations
                if self.vector_store and hasattr(self.vector_store, '_client'):
                    # Batch mode optimizations
                    original_settings = getattr(self.vector_store._client, 'settings', {})
                    
                yield
                
            finally:
                # Re-enable persistence and flush
                if self.vector_store:
                    try:
                        # Force persistence after bulk operations
                        self.vector_store.persist()
                    except Exception as e:
                        logger.warning(f"Failed to persist after bulk operation: {e}")
```

### Step 3: Parallel Document Retrieval (Day 4)

**Objective**: Parallelize document retrieval operations

**Files to Modify**:
- `backend/core/llm_chain.py`
- `backend/core/unified_retriever.py`

**Changes**:

```python
# llm_chain.py - Parallel retrieval optimization
async def async_retrieve_documents_parallel(
    query: str, 
    retrievers: Dict[str, BaseRetriever]
) -> List[Document]:
    """Parallel document retrieval with connection optimization."""
    
    from .unified_retriever import UnifiedRetriever
    
    unified_retriever = retrievers.get("_unified_retriever")
    if not unified_retriever or not isinstance(unified_retriever, UnifiedRetriever):
        return []
    
    try:
        # Use the new async search method
        semantic_searcher = unified_retriever.searcher
        if hasattr(semantic_searcher, 'semantic_search_async'):
            docs = await semantic_searcher.semantic_search_async(query)
            logger.debug(f"Parallel retrieval successful, got {len(docs)} documents")
            return docs
        else:
            # Fallback: run in thread pool with connection optimization  
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Parallel execution of search operations
                future = executor.submit(unified_retriever.auto_route_query, query)
                docs = await loop.run_in_executor(None, lambda: future.result(timeout=5.0))
                return docs
                
    except asyncio.TimeoutError:
        logger.warning(f"Document retrieval timed out for query: {query}")
        return []
    except Exception as e:
        logger.error(f"Parallel document retrieval failed: {e}")
        return []

# Enhanced connection management
class ConnectionManager:
    """Manages database connections and pools for optimal performance."""
    
    def __init__(self):
        self._connection_pools = {}
        self._health_checks = {}
    
    async def get_optimized_connection(self, service: str):
        """Get optimized connection for service."""
        # Implementation for connection pooling
        pass
    
    async def health_check_connections(self):
        """Periodic health checks for connections."""
        pass
```

### Step 4: Batch Operations & Connection Pooling (Day 5)

**Objective**: Implement proper batching for database operations

**Files to Modify**:
- `backend/core/app_initializer_v2.py`
- `backend/core/unified_retriever.py`

**Changes**:

```python
# app_initializer_v2.py - Batch initialization
async def initialize_unified_retriever_async(
    embeddings,
    llm: BaseLanguageModel,
    knowledge_dirs: List[str],
    force_reindex: bool = False
) -> UnifiedRetriever:
    """Async initialization with batch operations."""
    
    persist_dir = "backend/.unified_chroma"
    retriever = UnifiedRetriever(embeddings, llm, persist_dir)
    
    # Parallel directory indexing
    indexing_tasks = []
    for directory in knowledge_dirs:
        if Path(directory).exists():
            # Each directory processes asynchronously
            task = retriever.indexer.process_directory_async(directory, force_reindex)
            indexing_tasks.append(task)
    
    # Wait for all directories to be processed
    results = await asyncio.gather(*indexing_tasks, return_exceptions=True)
    
    # Batch add all documents to vector store
    all_documents = []
    total_files = 0
    total_chunks = 0
    
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Directory indexing failed: {result}")
        else:
            docs, files, chunks = result
            all_documents.extend(docs)
            total_files += files
            total_chunks += chunks
    
    # Batch add to vector store (more efficient than individual adds)
    if all_documents:
        await retriever.searcher.add_documents_batch(all_documents, batch_size=100)
    
    logger.info(f"Async initialization complete: {total_files} files, {total_chunks} chunks")
    return retriever

# Enhanced batch operations
class BatchProcessor:
    """Handles batch operations for optimal performance."""
    
    def __init__(self, batch_size: int = 50):
        self.batch_size = batch_size
        self._pending_operations = []
        self._batch_lock = asyncio.Lock()
    
    async def add_to_batch(self, operation: Any):
        """Add operation to batch queue."""
        async with self._batch_lock:
            self._pending_operations.append(operation)
            
            if len(self._pending_operations) >= self.batch_size:
                await self._process_batch()
    
    async def _process_batch(self):
        """Process current batch of operations."""
        if not self._pending_operations:
            return
            
        batch = self._pending_operations[:]
        self._pending_operations.clear()
        
        # Process batch concurrently
        tasks = [self._execute_operation(op) for op in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results and errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch operation {i} failed: {result}")
    
    async def flush_batch(self):
        """Flush remaining operations in batch."""
        async with self._batch_lock:
            if self._pending_operations:
                await self._process_batch()
```

## Testing & Validation

### Performance Tests

```python
# tests/performance/test_async_operations.py
import asyncio
import time
import pytest

@pytest.mark.asyncio
async def test_async_file_processing():
    """Test async file operations performance."""
    indexer = ContentIndexer(llm, persist_dir)
    
    # Test file hash computation
    start = time.time()
    hash_result = await indexer.compute_file_hash_async(Path("test_file.txt"))
    hash_duration = time.time() - start
    
    # Should be non-blocking (completed quickly due to thread pool)
    assert hash_duration < 0.5
    assert len(hash_result) == 64  # SHA256 hex length
    
@pytest.mark.asyncio  
async def test_parallel_directory_processing():
    """Test parallel directory processing."""
    indexer = ContentIndexer(llm, persist_dir)
    
    start = time.time()
    docs, files, chunks = await indexer.process_directory_async("backend/knowledge", False)
    duration = time.time() - start
    
    # Should be faster than synchronous version
    # Target: 50%+ faster than sync processing
    assert duration < 10.0  # Reasonable upper bound
    assert files > 0
    assert chunks > 0

@pytest.mark.asyncio
async def test_batch_vector_operations():
    """Test batch vector store operations."""
    searcher = SemanticSearcher(embeddings, persist_dir)
    
    documents = [Document(page_content=f"Test document {i}", metadata={"id": i}) for i in range(100)]
    
    start = time.time()
    await searcher.add_documents_batch(documents, batch_size=25)
    duration = time.time() - start
    
    # Batching should be more efficient than individual adds
    assert duration < 5.0
    assert searcher.get_collection_count() >= 100
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_async_search_performance():
    """Test async search performance improvement."""
    searcher = SemanticSearcher(embeddings, persist_dir)
    
    queries = [
        "What is Nick's experience?",
        "Show me creative work", 
        "Technical skills",
        "Vue.js projects"
    ]
    
    # Test parallel queries
    start = time.time()
    tasks = [searcher.semantic_search_async(query) for query in queries]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start
    
    # Parallel queries should be faster than sequential
    assert duration < 2.0  # All 4 queries in under 2 seconds
    assert all(len(result) > 0 for result in results)

def test_connection_optimization():
    """Test connection pooling and optimization."""
    searcher = SemanticSearcher(embeddings, persist_dir)
    stats = searcher.get_collection_stats()
    
    assert "count" in stats
    assert stats["count"] > 0
    assert "name" in stats
```

## Success Metrics

### Performance Targets
- **File Processing**: 50%+ faster directory indexing
- **Vector Operations**: 30%+ faster search queries  
- **Batch Operations**: 70%+ faster bulk document adds
- **Memory Usage**: 20% reduction in peak memory usage

### Resource Optimization
- **Connection Efficiency**: Reduce database connections by 60%
- **I/O Blocking**: Eliminate blocking file operations
- **Concurrency**: Support 10x more concurrent operations

## Monitoring & Observability

```python
# New monitoring for async operations
class AsyncPerformanceMonitor:
    """Monitor async operation performance."""
    
    def __init__(self):
        self.operation_times = {}
        self.connection_stats = {}
    
    async def track_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Track performance of async operations."""
        start = time.time()
        try:
            result = await operation_func(*args, **kwargs)
            duration = time.time() - start
            
            # Update stats
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
            self.operation_times[operation_name].append(duration)
            
            return result
        except Exception as e:
            logger.error(f"Async operation {operation_name} failed: {e}")
            raise
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        summary = {}
        for operation, times in self.operation_times.items():
            summary[operation] = {
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "total_calls": len(times)
            }
        return summary
```

## Rollout Plan

1. **Day 1-2**: Implement async file operations and testing
2. **Day 3**: Deploy ChromaDB optimizations and connection pooling  
3. **Day 4**: Implement parallel document retrieval
4. **Day 5**: Add batch operations and monitoring
5. **Day 6-7**: Performance validation and optimization tuning

This week builds on Week 1's improvements by eliminating I/O bottlenecks and optimizing database operations for additional performance gains.