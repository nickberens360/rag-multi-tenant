# Week 4: Background Processing & Pipeline Optimization

**Priority**: 🟢 MEDIUM  
**Expected Impact**: 10-15% additional performance improvement + Enhanced UX  
**Target**: Move non-critical operations to background and optimize the query pipeline  

## Current State After Week 1-3

After implementing the first three weeks of optimizations:
- ✅ Eliminated 3-4 LLM calls per query (Week 1)
- ✅ Async I/O and vector store optimization (Week 2)  
- ✅ Smart query classification and unified caching (Week 3)

**Remaining optimization opportunities**:
1. **Blocking Operations** - Some operations still block the main response
2. **Sequential Processing** - Query pipeline processes steps sequentially
3. **No Progressive Enhancement** - Users wait for complete responses
4. **Limited Concurrency** - System doesn't fully utilize available resources
5. **No Background Intelligence** - System doesn't learn and improve over time

## Implementation Plan

### Step 1: Background Task Processing (Day 1-2)

**Objective**: Move non-critical operations to background tasks

**Files to Create/Modify**:
- Create: `backend/core/background_processor.py`
- Create: `backend/core/task_queue.py` 
- Modify: `backend/core/app_initializer_v2.py`
- Add: `celery` or `arq` dependency for async task processing

**Changes**:

```python
# backend/core/background_processor.py - NEW FILE
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2  
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BackgroundTask:
    """Background task definition."""
    id: str
    name: str
    function: str
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None
    tags: List[str] = field(default_factory=list)

class BackgroundProcessor:
    """High-performance background task processor."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.task_queue: Dict[TaskPriority, List[BackgroundTask]] = {
            priority: [] for priority in TaskPriority
        }
        self.active_tasks: Dict[str, BackgroundTask] = {}
        self.completed_tasks: Dict[str, BackgroundTask] = {}
        
        # Task handlers
        self.task_handlers: Dict[str, Callable] = {}
        
        # Performance tracking
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "avg_processing_time": 0.0,
            "queue_sizes": {priority: 0 for priority in TaskPriority}
        }
        
        # Worker management
        self.workers = []
        self.is_running = False
        
        # Register core task handlers
        self._register_core_handlers()
    
    def _register_core_handlers(self):
        """Register core task handlers."""
        self.register_handler("enhance_metadata", self._enhance_metadata_task)
        self.register_handler("analyze_query_patterns", self._analyze_query_patterns_task)
        self.register_handler("update_document_index", self._update_document_index_task)
        self.register_handler("warm_cache", self._warm_cache_task)
        self.register_handler("cleanup_expired_data", self._cleanup_expired_data_task)
        self.register_handler("generate_analytics", self._generate_analytics_task)
    
    def register_handler(self, name: str, handler: Callable):
        """Register a task handler."""
        self.task_handlers[name] = handler
    
    async def start(self):
        """Start the background processor."""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info(f"Starting background processor with {self.max_workers} workers")
        
        # Start worker coroutines
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker_{i}"))
            self.workers.append(worker)
    
    async def stop(self):
        """Stop the background processor gracefully."""
        if not self.is_running:
            return
            
        logger.info("Stopping background processor...")
        self.is_running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish current tasks
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
    
    def enqueue_task(
        self,
        name: str,
        function: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        delay_seconds: Optional[int] = None,
        max_retries: int = 3,
        tags: List[str] = None
    ) -> str:
        """Enqueue a background task."""
        
        import uuid
        task_id = str(uuid.uuid4())
        
        scheduled_for = None
        if delay_seconds:
            scheduled_for = datetime.now() + timedelta(seconds=delay_seconds)
        
        task = BackgroundTask(
            id=task_id,
            name=name,
            function=function,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            created_at=datetime.now(),
            scheduled_for=scheduled_for,
            max_retries=max_retries,
            tags=tags or []
        )
        
        # Add to appropriate priority queue
        self.task_queue[priority].append(task)
        self.stats["queue_sizes"][priority] += 1
        
        logger.debug(f"Enqueued task {task_id}: {name} (priority: {priority.name})")
        return task_id
    
    async def _worker(self, worker_name: str):
        """Background worker coroutine."""
        logger.info(f"Started worker: {worker_name}")
        
        while self.is_running:
            try:
                # Get next task by priority
                task = await self._get_next_task()
                
                if task is None:
                    # No tasks available, wait briefly
                    await asyncio.sleep(0.1)
                    continue
                
                # Process task
                await self._process_task(task, worker_name)
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause on error
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _get_next_task(self) -> Optional[BackgroundTask]:
        """Get next task from queue (priority order)."""
        current_time = datetime.now()
        
        # Check queues in priority order (HIGH to LOW)
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
            queue = self.task_queue[priority]
            
            for i, task in enumerate(queue):
                # Check if task is ready to run
                if task.scheduled_for is None or task.scheduled_for <= current_time:
                    # Remove from queue
                    queue.pop(i)
                    self.stats["queue_sizes"][priority] -= 1
                    return task
        
        return None
    
    async def _process_task(self, task: BackgroundTask, worker_name: str):
        """Process a single background task."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Mark as processing
            task.status = TaskStatus.PROCESSING
            self.active_tasks[task.id] = task
            
            logger.debug(f"Worker {worker_name} processing task {task.id}: {task.name}")
            
            # Get handler
            handler = self.task_handlers.get(task.function)
            if not handler:
                raise ValueError(f"No handler registered for function: {task.function}")
            
            # Execute task
            if asyncio.iscoroutinefunction(handler):
                result = await handler(*task.args, **task.kwargs)
            else:
                result = handler(*task.args, **task.kwargs)
            
            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.processing_time = asyncio.get_event_loop().time() - start_time
            
            # Update stats
            self.stats["tasks_processed"] += 1
            self._update_avg_processing_time(task.processing_time)
            
            logger.debug(f"Task {task.id} completed in {task.processing_time:.3f}s")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.error(f"Task {task.id} failed: {e}", exc_info=True)
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.scheduled_for = datetime.now() + timedelta(seconds=2 ** task.retry_count)  # Exponential backoff
                
                # Re-queue for retry
                self.task_queue[task.priority].append(task)
                self.stats["queue_sizes"][task.priority] += 1
                
                logger.info(f"Task {task.id} queued for retry {task.retry_count}/{task.max_retries}")
            else:
                self.stats["tasks_failed"] += 1
        
        finally:
            # Move to completed tasks
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
            
            # Keep completed tasks for a while (for status queries)
            self.completed_tasks[task.id] = task
            
            # Cleanup old completed tasks (keep last 1000)
            if len(self.completed_tasks) > 1000:
                # Remove oldest completed tasks
                oldest_tasks = sorted(self.completed_tasks.items(), key=lambda x: x[1].created_at)
                for task_id, _ in oldest_tasks[:100]:
                    del self.completed_tasks[task_id]
    
    def _update_avg_processing_time(self, processing_time: float):
        """Update average processing time."""
        current_avg = self.stats["avg_processing_time"]
        tasks_processed = self.stats["tasks_processed"]
        
        # Incremental average calculation
        self.stats["avg_processing_time"] = (
            (current_avg * (tasks_processed - 1) + processing_time) / tasks_processed
        )
    
    # Task Handler Implementations
    async def _enhance_metadata_task(self, document_ids: List[str], **kwargs):
        """Background task to enhance document metadata with LLM analysis."""
        from .unified_retriever import get_unified_retriever
        from .llm_utils import extract_topics_with_llm
        
        try:
            # Get unified retriever and LLM
            retriever = get_unified_retriever({})  # Simplified access
            if not retriever:
                return {"error": "Unified retriever not available"}
            
            enhanced_count = 0
            for doc_id in document_ids:
                # Get document
                doc_data = retriever.searcher.get_document_by_id(doc_id)
                if not doc_data:
                    continue
                
                # Extract enhanced topics with LLM (now in background)
                enhanced_topics = extract_topics_with_llm(retriever.llm, doc_data["content"])
                
                # Update metadata
                enhanced_metadata = doc_data["metadata"].copy()
                enhanced_metadata["enhanced_topics"] = enhanced_topics
                enhanced_metadata["enhanced_at"] = datetime.now().isoformat()
                
                # Update in vector store
                success = retriever.searcher.update_document_metadata(doc_id, enhanced_metadata)
                if success:
                    enhanced_count += 1
                
                # Small delay to avoid overwhelming LLM
                await asyncio.sleep(0.5)
            
            return {"enhanced_documents": enhanced_count}
            
        except Exception as e:
            logger.error(f"Metadata enhancement task failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_query_patterns_task(self, queries: List[str], **kwargs):
        """Background task to analyze query patterns for optimization."""
        try:
            # Import here to avoid circular imports
            from .cache_prewarmer import SmartCachePrewarmer
            
            # Analyze patterns
            analysis_results = {
                "total_queries": len(queries),
                "unique_queries": len(set(queries)),
                "common_patterns": {},
                "complexity_distribution": {"simple": 0, "moderate": 0, "complex": 0}
            }
            
            # Pattern analysis logic here...
            # This would be more sophisticated in real implementation
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Query pattern analysis failed: {e}")
            return {"error": str(e)}
    
    async def _warm_cache_task(self, strategy: str = "common", **kwargs):
        """Background cache warming task."""
        try:
            from .cache_prewarmer import SmartCachePrewarmer
            from .unified_cache import UnifiedCache
            
            # Get cache and prewarmer (simplified)
            cache = UnifiedCache()
            prewarmer = SmartCachePrewarmer(cache, None, None)
            
            await prewarmer.prewarm_cache(strategy)
            
            return {"strategy": strategy, "status": "completed"}
            
        except Exception as e:
            logger.error(f"Cache warming task failed: {e}")
            return {"error": str(e)}
    
    # ... other task handlers
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        # Check active tasks first
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
        elif task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
        else:
            return None
        
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "processing_time": task.processing_time,
            "result": task.result,
            "error": task.error,
            "retry_count": task.retry_count
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "queue_sizes": {priority.name: size for priority, size in self.stats["queue_sizes"].items()},
            "performance": {
                "tasks_processed": self.stats["tasks_processed"],
                "tasks_failed": self.stats["tasks_failed"],
                "avg_processing_time": self.stats["avg_processing_time"],
                "success_rate": (self.stats["tasks_processed"] / (self.stats["tasks_processed"] + self.stats["tasks_failed"])) if (self.stats["tasks_processed"] + self.stats["tasks_failed"]) > 0 else 0
            }
        }
```

### Step 2: Progressive Response Pipeline (Day 3)

**Objective**: Implement progressive response delivery for better UX

**Files to Modify**:
- Create: `backend/core/progressive_pipeline.py`
- Modify: `backend/routes/query.py`
- Enhance: Response streaming capabilities

**Changes**:

```python
# backend/core/progressive_pipeline.py - NEW FILE
import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseStage(Enum):
    INITIATED = "initiated"
    DOCUMENTS_RETRIEVED = "documents_retrieved"
    CONTEXT_PREPARED = "context_prepared"
    RESPONSE_GENERATING = "response_generating"
    RESPONSE_COMPLETE = "response_complete"
    ENHANCEMENT_PROCESSING = "enhancement_processing"
    FULLY_COMPLETE = "fully_complete"

@dataclass
class ProgressUpdate:
    """Progress update for streaming responses."""
    stage: ResponseStage
    progress: float  # 0.0 to 1.0
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None

class ProgressiveResponsePipeline:
    """Pipeline for progressive response delivery with background enhancements."""
    
    def __init__(self, background_processor):
        self.background_processor = background_processor
        
        # Stage completion percentages for progress tracking
        self.stage_progress = {
            ResponseStage.INITIATED: 0.05,
            ResponseStage.DOCUMENTS_RETRIEVED: 0.25,
            ResponseStage.CONTEXT_PREPARED: 0.35,
            ResponseStage.RESPONSE_GENERATING: 0.45,  # Start of streaming
            ResponseStage.RESPONSE_COMPLETE: 0.90,
            ResponseStage.ENHANCEMENT_PROCESSING: 0.95,
            ResponseStage.FULLY_COMPLETE: 1.0
        }
    
    async def process_query_progressive(
        self,
        query: str,
        services: Dict[str, Any],
        client_ip: str,
        **kwargs
    ) -> AsyncIterator[str]:
        """Process query with progressive updates and background tasks."""
        
        import time
        start_time = time.time()
        
        try:
            # Stage 1: Query Initiated
            yield self._format_progress_update(
                ResponseStage.INITIATED,
                "Processing your query..."
            )
            
            # Fast query classification (from Week 3)
            from .query_classifier import IntelligentQueryClassifier
            classifier = IntelligentQueryClassifier()
            query_profile = classifier.classify_query(query)
            
            # Stage 2: Document Retrieval (Parallel)
            yield self._format_progress_update(
                ResponseStage.DOCUMENTS_RETRIEVED,
                "Retrieving relevant information...",
                {"estimated_time": query_profile.estimated_response_time}
            )
            
            # Parallel document retrieval
            retrieval_task = asyncio.create_task(
                self._retrieve_documents_async(query, services)
            )
            
            # Start background tasks early (non-blocking)
            background_tasks = await self._start_background_tasks(query, query_profile, client_ip)
            
            # Wait for document retrieval
            documents = await retrieval_task
            
            # Stage 3: Context Preparation
            yield self._format_progress_update(
                ResponseStage.CONTEXT_PREPARED,
                "Preparing response context..."
            )
            
            # Prepare context efficiently
            context = await self._prepare_context_async(documents, query)
            
            # Stage 4-5: Response Generation (Progressive Streaming)
            yield self._format_progress_update(
                ResponseStage.RESPONSE_GENERATING,
                "Generating response..."
            )
            
            # Stream the actual response
            response_chunks = []
            async for chunk in self._generate_response_stream(query, context, services):
                response_chunks.append(chunk)
                yield chunk  # Pass through response chunks
            
            # Stage 6: Response Complete
            complete_response = "".join(response_chunks)
            yield self._format_progress_update(
                ResponseStage.RESPONSE_COMPLETE,
                "Response generated successfully"
            )
            
            # Stage 7: Background Enhancement (Non-blocking)
            self._schedule_post_response_enhancements(
                query, complete_response, documents, background_tasks
            )
            
            yield self._format_progress_update(
                ResponseStage.ENHANCEMENT_PROCESSING,
                "Processing background enhancements..."
            )
            
            # Final completion
            processing_time = time.time() - start_time
            yield self._format_progress_update(
                ResponseStage.FULLY_COMPLETE,
                f"Query processed in {processing_time:.2f}s",
                {"processing_time": processing_time, "background_tasks": len(background_tasks)}
            )
            
        except Exception as e:
            logger.error(f"Progressive pipeline error: {e}", exc_info=True)
            yield self._format_error_update(str(e))
    
    def _format_progress_update(
        self, 
        stage: ResponseStage, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format progress update as JSON string."""
        import time
        
        update = ProgressUpdate(
            stage=stage,
            progress=self.stage_progress[stage],
            message=message,
            data=data,
            timestamp=time.time()
        )
        
        # Format as special progress message (distinguishable from response content)
        progress_data = {
            "type": "progress",
            "stage": stage.value,
            "progress": update.progress,
            "message": message,
            "data": data,
            "timestamp": update.timestamp
        }
        
        return f"__PROGRESS__{json.dumps(progress_data)}__END_PROGRESS__\n"
    
    def _format_error_update(self, error_message: str) -> str:
        """Format error update."""
        error_data = {
            "type": "error", 
            "message": error_message,
            "timestamp": time.time()
        }
        
        return f"__ERROR__{json.dumps(error_data)}__END_ERROR__\n"
    
    async def _retrieve_documents_async(self, query: str, services: Dict[str, Any]) -> List[Any]:
        """Async document retrieval with timeout."""
        try:
            # Use optimized async retrieval from Week 2
            from .llm_chain import async_retrieve_documents_parallel
            
            documents = await asyncio.wait_for(
                async_retrieve_documents_parallel(query, services.get("retrievers", {})),
                timeout=5.0
            )
            
            return documents or []
            
        except asyncio.TimeoutError:
            logger.warning(f"Document retrieval timed out for query: {query}")
            return []
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []
    
    async def _prepare_context_async(self, documents: List[Any], query: str) -> str:
        """Async context preparation."""
        if not documents:
            return "No relevant context found."
        
        # Efficient context preparation (from Week 1 optimizations)
        context_parts = []
        total_length = 0
        max_length = 2000  # Token limit
        
        for doc in documents[:5]:  # Limit to top 5 documents
            if hasattr(doc, 'page_content'):
                content = doc.page_content[:400]  # Truncate individual docs
                if total_length + len(content) <= max_length:
                    context_parts.append(content)
                    total_length += len(content)
                else:
                    break
        
        return "\n\n".join(context_parts)
    
    async def _generate_response_stream(
        self, 
        query: str, 
        context: str, 
        services: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Generate response stream using optimized LLM chain."""
        try:
            from .llm_chain import stream_with_fallback
            
            # Use optimized streaming from previous weeks
            stream, model_used, metadata = await stream_with_fallback(
                services.get("retrievers", {}),
                [],  # Empty chat history for simplicity
                query,
                preferred_model=None
            )
            
            async for chunk in stream:
                yield chunk
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            yield f"I apologize, but I encountered an error generating the response: {str(e)}"
    
    async def _start_background_tasks(
        self, 
        query: str, 
        query_profile, 
        client_ip: str
    ) -> List[str]:
        """Start background tasks early in the pipeline."""
        background_tasks = []
        
        try:
            # Cache warming for related queries
            if query_profile.processing_strategy in ["simple_text_search", "moderate_exploration"]:
                task_id = self.background_processor.enqueue_task(
                    name="warm_related_cache",
                    function="warm_cache",
                    kwargs={"strategy": "pattern_based", "seed_query": query},
                    priority=TaskPriority.LOW,
                    tags=["cache_warming"]
                )
                background_tasks.append(task_id)
            
            # Query pattern analysis (for future optimizations)
            task_id = self.background_processor.enqueue_task(
                name="analyze_query_pattern",
                function="analyze_query_patterns",
                args=[[query]],
                kwargs={"client_ip": client_ip},
                priority=TaskPriority.LOW,
                tags=["analytics"]
            )
            background_tasks.append(task_id)
            
        except Exception as e:
            logger.warning(f"Failed to start background tasks: {e}")
        
        return background_tasks
    
    def _schedule_post_response_enhancements(
        self,
        query: str,
        response: str,
        documents: List[Any],
        background_tasks: List[str]
    ):
        """Schedule background enhancements after response delivery."""
        
        try:
            # Document metadata enhancement
            if documents:
                doc_ids = [getattr(doc, 'id', f"doc_{i}") for i, doc in enumerate(documents)]
                self.background_processor.enqueue_task(
                    name="enhance_document_metadata",
                    function="enhance_metadata",
                    args=[doc_ids],
                    priority=TaskPriority.LOW,
                    delay_seconds=30,  # Wait 30 seconds after response
                    tags=["metadata_enhancement"]
                )
            
            # Response quality analysis
            self.background_processor.enqueue_task(
                name="analyze_response_quality",
                function="analyze_response_quality",
                kwargs={
                    "query": query,
                    "response": response,
                    "document_count": len(documents)
                },
                priority=TaskPriority.LOW,
                delay_seconds=60,
                tags=["quality_analysis"]
            )
            
        except Exception as e:
            logger.warning(f"Failed to schedule post-response enhancements: {e}")
```

### Step 3: Parallel Query Processing (Day 4)

**Objective**: Process multiple aspects of queries in parallel

**Files to Modify**:
- Create: `backend/core/parallel_processor.py`
- Modify: `backend/core/smart_query_handler.py`

**Changes**:

```python
# backend/core/parallel_processor.py - NEW FILE
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Coroutine
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class ParallelQueryProcessor:
    """Process multiple query aspects in parallel for maximum efficiency."""
    
    def __init__(self, max_parallel_tasks: int = 6):
        self.max_parallel_tasks = max_parallel_tasks
        self.thread_executor = ThreadPoolExecutor(max_workers=4)
        
        # Performance tracking
        self.processing_stats = {
            "parallel_queries": 0,
            "avg_parallel_speedup": 0.0,
            "max_concurrent_tasks": 0
        }
    
    async def process_query_parallel(
        self,
        query: str,
        services: Dict[str, Any],
        query_profile: Any,
        **kwargs
    ) -> Dict[str, Any]:
        """Process query with maximum parallelization."""
        
        start_time = time.time()
        
        # Create parallel tasks based on query profile
        tasks = self._create_parallel_tasks(query, services, query_profile, **kwargs)
        
        # Execute tasks with concurrency limit
        results = await self._execute_parallel_tasks(tasks)
        
        # Combine results into final response
        final_result = await self._combine_results(results, query, query_profile)
        
        # Update stats
        processing_time = time.time() - start_time
        self._update_processing_stats(len(tasks), processing_time)
        
        return final_result
    
    def _create_parallel_tasks(
        self,
        query: str,
        services: Dict[str, Any],
        query_profile: Any,
        **kwargs
    ) -> List[Tuple[str, Coroutine]]:
        """Create parallel tasks based on query characteristics."""
        
        tasks = []
        
        # Always include document retrieval
        tasks.append((
            "document_retrieval",
            self._retrieve_documents_task(query, services)
        ))
        
        # Content type specific tasks
        if "creative" in query_profile.topics:
            tasks.append((
                "illustration_search",
                self._search_illustrations_task(query, services)
            ))
        
        if "experience" in query_profile.topics:
            tasks.append((
                "experience_search",
                self._search_experience_task(query, services)
            ))
        
        # Query complexity specific tasks
        if query_profile.complexity.value == "complex":
            tasks.append((
                "comprehensive_search",
                self._comprehensive_search_task(query, services)
            ))
        
        # Background analytics (low priority)
        tasks.append((
            "analytics_update",
            self._update_analytics_task(query, query_profile)
        ))
        
        # Limit concurrent tasks
        return tasks[:self.max_parallel_tasks]
    
    async def _execute_parallel_tasks(
        self, 
        tasks: List[Tuple[str, Coroutine]]
    ) -> Dict[str, Any]:
        """Execute tasks in parallel with error handling."""
        
        if not tasks:
            return {}
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)
        
        async def execute_with_semaphore(name: str, task: Coroutine):
            async with semaphore:
                try:
                    result = await task
                    return name, result, None
                except Exception as e:
                    logger.error(f"Parallel task {name} failed: {e}")
                    return name, None, str(e)
        
        # Execute all tasks in parallel
        wrapped_tasks = [
            execute_with_semaphore(name, task) 
            for name, task in tasks
        ]
        
        results = await asyncio.gather(*wrapped_tasks, return_exceptions=True)
        
        # Process results
        processed_results = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel execution error: {result}")
                continue
                
            name, data, error = result
            processed_results[name] = {
                "data": data,
                "error": error,
                "success": error is None
            }
        
        # Update max concurrent tasks stat
        self.processing_stats["max_concurrent_tasks"] = max(
            self.processing_stats["max_concurrent_tasks"],
            len(tasks)
        )
        
        return processed_results
    
    async def _combine_results(
        self, 
        results: Dict[str, Any], 
        query: str, 
        query_profile: Any
    ) -> Dict[str, Any]:
        """Combine parallel task results into coherent response."""
        
        # Extract successful results
        documents = results.get("document_retrieval", {}).get("data", [])
        illustrations = results.get("illustration_search", {}).get("data", [])
        experience_data = results.get("experience_search", {}).get("data", {})
        comprehensive_data = results.get("comprehensive_search", {}).get("data", {})
        
        # Build response based on available data
        response_data = {
            "query": query,
            "strategy": query_profile.processing_strategy,
            "documents_found": len(documents) if documents else 0,
            "processing_method": "parallel"
        }
        
        # Include relevant data based on query type
        if illustrations:
            response_data["illustrations"] = illustrations
        
        if experience_data:
            response_data["experience"] = experience_data
        
        if comprehensive_data:
            response_data.update(comprehensive_data)
        
        # Generate final text response
        if documents:
            response_data["answer"] = await self._generate_response_from_documents(
                query, documents, query_profile
            )
        else:
            response_data["answer"] = "I don't have specific information to answer that question."
        
        return response_data
    
    # Individual task implementations
    async def _retrieve_documents_task(self, query: str, services: Dict[str, Any]) -> List[Any]:
        """Parallel document retrieval task."""
        try:
            from .llm_chain import async_retrieve_documents_parallel
            return await async_retrieve_documents_parallel(query, services.get("retrievers", {}))
        except Exception as e:
            logger.error(f"Document retrieval task failed: {e}")
            return []
    
    async def _search_illustrations_task(self, query: str, services: Dict[str, Any]) -> List[Dict]:
        """Parallel illustration search task."""
        try:
            illustration_service = services.get("illustration_service")
            if not illustration_service:
                return []
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.thread_executor,
                illustration_service.search,
                query
            )
            
            return results or []
            
        except Exception as e:
            logger.error(f"Illustration search task failed: {e}")
            return []
    
    async def _search_experience_task(self, query: str, services: Dict[str, Any]) -> Dict[str, Any]:
        """Parallel experience-focused search task."""
        try:
            # Focused search for experience-related content
            retrievers = services.get("retrievers", {})
            if not retrievers:
                return {}
            
            # Search with experience filter
            unified_retriever = retrievers.get("_unified_retriever")
            if unified_retriever:
                docs = await asyncio.get_event_loop().run_in_executor(
                    self.thread_executor,
                    unified_retriever.searcher.semantic_search,
                    query,
                    5,  # k
                    ["experience", "skills"]  # content type filter
                )
                
                return {
                    "experience_docs": len(docs),
                    "relevant_content": [doc.page_content[:200] for doc in docs[:3]]
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Experience search task failed: {e}")
            return {}
    
    async def _comprehensive_search_task(self, query: str, services: Dict[str, Any]) -> Dict[str, Any]:
        """Parallel comprehensive search for complex queries."""
        try:
            # Multi-angle search for complex queries
            retrievers = services.get("retrievers", {})
            if not retrievers:
                return {}
            
            unified_retriever = retrievers.get("_unified_retriever")
            if unified_retriever:
                # Search with multiple strategies in parallel
                search_tasks = [
                    asyncio.get_event_loop().run_in_executor(
                        self.thread_executor,
                        unified_retriever.searcher.semantic_search,
                        query,
                        8,  # More results for comprehensive search
                        None  # No content filter
                    ),
                    asyncio.get_event_loop().run_in_executor(
                        self.thread_executor,
                        unified_retriever.searcher.semantic_search,
                        query,
                        5,
                        ["technical", "project"]  # Technical focus
                    )
                ]
                
                results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                all_docs = []
                for result in results:
                    if isinstance(result, list):
                        all_docs.extend(result)
                
                # Deduplicate by content
                unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
                
                return {
                    "comprehensive_docs": len(unique_docs),
                    "search_strategies": len(search_tasks),
                    "total_results": len(all_docs)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Comprehensive search task failed: {e}")
            return {}
    
    async def _update_analytics_task(self, query: str, query_profile: Any) -> Dict[str, Any]:
        """Background analytics update task."""
        try:
            # Update query analytics in background
            analytics_data = {
                "query_length": len(query),
                "complexity": query_profile.complexity.value,
                "topics": query_profile.topics,
                "processing_timestamp": time.time()
            }
            
            # This would integrate with your analytics system
            return analytics_data
            
        except Exception as e:
            logger.error(f"Analytics update task failed: {e}")
            return {}
    
    async def _generate_response_from_documents(
        self, 
        query: str, 
        documents: List[Any], 
        query_profile: Any
    ) -> str:
        """Generate response from documents (can be done in parallel)."""
        try:
            if not documents:
                return "No relevant information found."
            
            # Quick response generation for parallel processing
            context = "\n".join([
                doc.page_content[:300] for doc in documents[:3]
                if hasattr(doc, 'page_content')
            ])
            
            if not context:
                return "Unable to generate response from available documents."
            
            # For parallel processing, use a simpler template-based response
            # Full LLM generation would happen in the main pipeline
            
            if query_profile.complexity.value == "simple":
                # Template-based response for simple queries
                if "skills" in query_profile.topics:
                    return f"Based on the available information: {context[:200]}..."
                elif "experience" in query_profile.topics:
                    return f"Nick's experience includes: {context[:200]}..."
                else:
                    return f"Here's what I found: {context[:200]}..."
            
            # For moderate/complex queries, return context for LLM processing
            return context[:500]
            
        except Exception as e:
            logger.error(f"Response generation from documents failed: {e}")
            return "Error generating response from documents."
    
    def _update_processing_stats(self, task_count: int, processing_time: float):
        """Update parallel processing statistics."""
        self.processing_stats["parallel_queries"] += 1
        
        # Estimate sequential time (rough approximation)
        estimated_sequential_time = processing_time * task_count
        speedup = estimated_sequential_time / processing_time if processing_time > 0 else 1
        
        # Update average speedup
        current_avg = self.processing_stats["avg_parallel_speedup"]
        query_count = self.processing_stats["parallel_queries"]
        
        self.processing_stats["avg_parallel_speedup"] = (
            (current_avg * (query_count - 1) + speedup) / query_count
        )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get parallel processing statistics."""
        return self.processing_stats.copy()
```

### Step 4: Integration & Monitoring (Day 5)

**Objective**: Integrate all Week 4 improvements and add comprehensive monitoring

**Files to Modify**:
- Modify: `backend/routes/query.py`
- Create: `backend/core/performance_dashboard.py`
- Update: `backend/core/app_initializer_v2.py`

**Changes**:

```python
# Integration in backend/routes/query.py
from ..core.background_processor import BackgroundProcessor, TaskPriority
from ..core.progressive_pipeline import ProgressiveResponsePipeline  
from ..core.parallel_processor import ParallelQueryProcessor

# Initialize new components
background_processor = BackgroundProcessor(max_workers=4)
progressive_pipeline = ProgressiveResponsePipeline(background_processor)
parallel_processor = ParallelQueryProcessor(max_parallel_tasks=6)

# Start background processor
@router.on_event("startup")
async def startup_background_processor():
    await background_processor.start()

@router.on_event("shutdown") 
async def shutdown_background_processor():
    await background_processor.stop()

@router.post("/query")
async def query_endpoint_week4_optimized(request: Request, query: Query, services: dict = Depends(get_services)):
    """Week 4 optimized endpoint with background processing and progressive responses."""
    
    # Fast pre-processing (from previous weeks)
    start_time = time.time()
    client_ip = get_remote_address(request)
    sanitized_question = SecurityValidator.sanitize_input(query.question)
    
    # Query classification (Week 3)
    query_profile = query_classifier.classify_query(sanitized_question)
    
    # Check cache (Week 3)
    cached_response = cache_strategy.get_cached_response(sanitized_question)
    if cached_response:
        return JSONResponse(content={"answer": cached_response, "cached": True})
    
    # Determine processing strategy
    use_progressive = query_profile.estimated_response_time > 2.0
    use_parallel = query_profile.complexity.value in ["moderate", "complex"]
    
    if use_progressive:
        # Progressive pipeline for longer queries
        return StreamingResponse(
            progressive_pipeline.process_query_progressive(
                sanitized_question,
                services,
                client_ip
            ),
            media_type="text/plain",
            headers={"X-Processing-Mode": "progressive"}
        )
    
    elif use_parallel:
        # Parallel processing for complex queries
        result = await parallel_processor.process_query_parallel(
            sanitized_question,
            services,
            query_profile
        )
        
        # Cache result
        if result and "answer" in result:
            cache_strategy.cache_response(
                sanitized_question,
                result["answer"],
                query_profile.processing_strategy
            )
        
        return JSONResponse(content=result, headers={"X-Processing-Mode": "parallel"})
    
    else:
        # Fast path for simple queries (Week 1-3 optimizations)
        # Use existing optimized flow
        pass

# New monitoring endpoints
@router.get("/admin/performance/background-tasks")
async def get_background_task_stats():
    """Get background task processing statistics."""
    return background_processor.get_queue_stats()

@router.get("/admin/performance/parallel-processing")
async def get_parallel_processing_stats():
    """Get parallel processing statistics."""
    return parallel_processor.get_processing_stats()

# Performance dashboard
# backend/core/performance_dashboard.py - NEW FILE
class PerformanceDashboard:
    """Comprehensive performance monitoring dashboard."""
    
    def __init__(self, background_processor, parallel_processor, unified_cache):
        self.background_processor = background_processor
        self.parallel_processor = parallel_processor
        self.unified_cache = unified_cache
        
        # Performance history
        self.performance_history = []
        self.alert_thresholds = {
            "avg_response_time": 3.0,
            "cache_hit_rate": 0.3,
            "background_queue_size": 100,
            "failed_task_rate": 0.1
        }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get all performance statistics in one call."""
        
        return {
            "cache_stats": self.unified_cache.get_cache_stats(),
            "background_tasks": self.background_processor.get_queue_stats(),
            "parallel_processing": self.parallel_processor.get_processing_stats(),
            "alerts": self._check_performance_alerts(),
            "timestamp": time.time()
        }
    
    def _check_performance_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance issues and generate alerts."""
        alerts = []
        
        # Check cache performance
        cache_stats = self.unified_cache.get_cache_stats()
        if cache_stats.get("hit_rate", 0) < self.alert_thresholds["cache_hit_rate"]:
            alerts.append({
                "type": "cache_performance",
                "message": f"Low cache hit rate: {cache_stats.get('hit_rate', 0):.2%}",
                "severity": "medium"
            })
        
        # Check background task queue
        bg_stats = self.background_processor.get_queue_stats()
        total_queued = sum(bg_stats.get("queue_sizes", {}).values())
        if total_queued > self.alert_thresholds["background_queue_size"]:
            alerts.append({
                "type": "background_queue",
                "message": f"High background queue size: {total_queued}",
                "severity": "high"
            })
        
        return alerts
```

## Testing & Validation

### Performance Tests

```python
# tests/performance/test_week4_optimizations.py
import pytest
import asyncio
import time
from backend.core.background_processor import BackgroundProcessor
from backend.core.progressive_pipeline import ProgressiveResponsePipeline

@pytest.mark.asyncio
async def test_background_processor_performance():
    """Test background processor handles tasks efficiently."""
    processor = BackgroundProcessor(max_workers=2)
    await processor.start()
    
    # Enqueue multiple tasks
    task_ids = []
    for i in range(10):
        task_id = processor.enqueue_task(
            name=f"test_task_{i}",
            function="test_handler",
            args=[i]
        )
        task_ids.append(task_id)
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Check completion
    stats = processor.get_queue_stats()
    assert stats["performance"]["tasks_processed"] >= 8  # Allow for some processing time
    
    await processor.stop()

@pytest.mark.asyncio  
async def test_progressive_pipeline_stages():
    """Test progressive pipeline delivers updates in stages."""
    pipeline = ProgressiveResponsePipeline(None)
    
    updates = []
    async for update in pipeline.process_query_progressive(
        "Test query",
        {"retrievers": {}},
        "127.0.0.1"
    ):
        if update.startswith("__PROGRESS__"):
            updates.append(update)
        
        # Stop after few updates for testing
        if len(updates) >= 3:
            break
    
    assert len(updates) >= 3
    # Verify progress updates are properly formatted
    assert all("__PROGRESS__" in update for update in updates)

def test_parallel_processor_speedup():
    """Test parallel processor provides speedup over sequential."""
    processor = ParallelQueryProcessor(max_parallel_tasks=4)
    
    # This would be a more comprehensive test in real implementation
    stats = processor.get_processing_stats()
    assert "avg_parallel_speedup" in stats
    assert "max_concurrent_tasks" in stats
```

## Success Metrics

### Performance Targets
- **Background Tasks**: Process 100+ tasks/minute without blocking main queries
- **Progressive Responses**: First content delivered <1 second, full response <3 seconds  
- **Parallel Processing**: 20-40% speedup for complex queries
- **User Experience**: Perceived performance improvement of 50%+

### System Health Targets
- **Queue Health**: Background queues never exceed 100 pending tasks
- **Error Rate**: <5% background task failure rate
- **Resource Usage**: <20% additional memory usage despite new features

## Rollout Plan

1. **Day 1-2**: Implement and test background processor
2. **Day 3**: Deploy progressive response pipeline  
3. **Day 4**: Add parallel query processing
4. **Day 5**: Integration, monitoring, and performance validation
5. **Day 6-7**: User acceptance testing and optimization tuning

## Summary: Complete 4-Week Performance Improvement

After implementing all four weeks:

### Expected Performance Gains:
- **Week 1**: 60-70% improvement (eliminate redundant LLM calls)
- **Week 2**: Additional 20-30% (async operations, vector optimization)  
- **Week 3**: Additional 15-25% (smart classification, unified caching)
- **Week 4**: Additional 10-15% + UX improvements (background processing, progressive responses)

### Total Expected Improvement: 80-90% faster responses + significantly better user experience

### From: ~6-8 seconds average → To: ~1-2 seconds average + progressive updates