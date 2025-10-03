# Week 3: Smart Query Classification & Streamlined Caching

**Priority**: 🟡 MEDIUM-HIGH  
**Expected Impact**: 15-25% additional performance improvement  
**Target**: Intelligent query routing and optimal caching strategy  

## Current Problem

After Week 1-2 optimizations, remaining performance issues:

1. **Over-Engineering Query Analysis** - Still doing unnecessary work for simple queries
2. **Multi-Layer Cache Complexity** - 3 separate caches causing overhead
3. **Inefficient Cache Key Generation** - SHA256 hashing adds latency
4. **No Query Intelligence** - Treating all queries equally
5. **Cache Miss Penalties** - No smart pre-warming or prediction

**Impact**: 1-3 seconds of unnecessary processing for common query patterns

## Implementation Plan

### Step 1: Intelligent Query Classification System (Day 1-2)

**Objective**: Route queries to optimal processing paths based on complexity and type

**Files to Modify**:
- Create: `backend/core/query_classifier.py`
- Modify: `backend/core/smart_query_handler.py`
- Modify: `backend/routes/query.py`

**Changes**:

```python
# backend/core/query_classifier.py - NEW FILE
import re
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

class QueryComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate" 
    COMPLEX = "complex"

class QueryIntent(Enum):
    FACTUAL = "factual"          # "What is X?"
    EXPLORATORY = "exploratory"  # "Tell me about X"
    CREATIVE = "creative"        # "Show me illustrations"
    COMPARATIVE = "comparative"  # "Compare X and Y"
    ANALYTICAL = "analytical"    # "How does X work?"

@dataclass
class QueryProfile:
    """Fast query classification result."""
    complexity: QueryComplexity
    intent: QueryIntent
    topics: List[str]
    confidence: float
    processing_strategy: str
    estimated_response_time: float

class IntelligentQueryClassifier:
    """Lightning-fast query classification with routing optimization."""
    
    def __init__(self):
        self.classification_cache: Dict[str, QueryProfile] = {}
        self.performance_stats = {
            "total_classifications": 0,
            "cache_hits": 0,
            "avg_classification_time": 0.0
        }
        
        # Optimized regex patterns (compiled once)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for maximum speed."""
        
        # Simple factual patterns
        self.simple_patterns = [
            re.compile(r'^(what|who|when|where)\s+(is|are|was|were)\s+', re.I),
            re.compile(r'^(list|show me|give me)\s+', re.I),
            re.compile(r'\b(skills?|technologies?|experience with)\b', re.I),
            re.compile(r'^(can you tell me|tell me)\s+(about|what)\s+', re.I),
        ]
        
        # Complex analytical patterns  
        self.complex_patterns = [
            re.compile(r'\b(how does|why does|explain|analyze|compare|evaluate)\b', re.I),
            re.compile(r'\b(approach|methodology|philosophy|strategy|architecture)\b', re.I),
            re.compile(r'\b(best practices?|design patterns?|pros and cons)\b', re.I),
            re.compile(r'\b(difference between|advantages of|benefits of)\b', re.I),
        ]
        
        # Topic detection patterns
        self.topic_patterns = {
            "experience": re.compile(r'\b(experience|work|job|career|role|company|resume|cv)\b', re.I),
            "skills": re.compile(r'\b(skills?|technologies?|tools?|expertise|proficient|languages?)\b', re.I),
            "creative": re.compile(r'\b(illustration|art|design|creative|artwork|visual|gallery)\b', re.I),
            "projects": re.compile(r'\b(project|built|created|developed|portfolio|github)\b', re.I),
            "about": re.compile(r'\b(about|who|background|bio|person|interest|hobby)\b', re.I),
        }
        
        # Intent detection patterns
        self.intent_patterns = {
            QueryIntent.FACTUAL: re.compile(r'^(what|who|when|where|which)\s+', re.I),
            QueryIntent.EXPLORATORY: re.compile(r'^(tell me|describe|talk about|explain)\s+', re.I),
            QueryIntent.CREATIVE: re.compile(r'\b(show|display|illustrations?|artwork|visual|gallery)\b', re.I),
            QueryIntent.COMPARATIVE: re.compile(r'\b(compare|versus|vs|difference|better|prefer)\b', re.I),
            QueryIntent.ANALYTICAL: re.compile(r'\b(how|why|analyze|approach|methodology)\b', re.I),
        }
    
    def classify_query(self, query: str) -> QueryProfile:
        """Ultra-fast query classification (target: <10ms)."""
        start_time = time.time()
        
        # Check cache first (fastest path)
        cache_key = query.lower().strip()
        if cache_key in self.classification_cache:
            self.performance_stats["cache_hits"] += 1
            return self.classification_cache[cache_key]
        
        # Fast pattern-based classification
        query_lower = query.lower().strip()
        
        # Determine complexity (fastest checks first)
        complexity = self._classify_complexity(query, query_lower)
        
        # Determine intent
        intent = self._classify_intent(query_lower)
        
        # Extract topics  
        topics = self._extract_topics(query_lower)
        
        # Calculate confidence based on pattern matches
        confidence = self._calculate_confidence(query_lower, complexity, intent, topics)
        
        # Determine processing strategy
        processing_strategy = self._determine_strategy(complexity, intent, topics)
        
        # Estimate response time
        estimated_time = self._estimate_response_time(complexity, intent, len(topics))
        
        # Create profile
        profile = QueryProfile(
            complexity=complexity,
            intent=intent, 
            topics=topics,
            confidence=confidence,
            processing_strategy=processing_strategy,
            estimated_response_time=estimated_time
        )
        
        # Cache result (limit cache size)
        if len(self.classification_cache) < 1000:
            self.classification_cache[cache_key] = profile
        
        # Update stats
        classification_time = time.time() - start_time
        self.performance_stats["total_classifications"] += 1
        self.performance_stats["avg_classification_time"] = (
            (self.performance_stats["avg_classification_time"] * (self.performance_stats["total_classifications"] - 1) + classification_time) 
            / self.performance_stats["total_classifications"]
        )
        
        return profile
    
    def _classify_complexity(self, query: str, query_lower: str) -> QueryComplexity:
        """Fast complexity classification."""
        
        # Simple query indicators (check first - most common)
        if any(pattern.search(query) for pattern in self.simple_patterns):
            return QueryComplexity.SIMPLE
            
        # Very short queries are usually simple
        if len(query.split()) <= 5:
            return QueryComplexity.SIMPLE
            
        # Complex query indicators
        if any(pattern.search(query) for pattern in self.complex_patterns):
            return QueryComplexity.COMPLEX
            
        # Questions with multiple clauses
        if query.count('?') > 1 or ' and ' in query_lower or ' or ' in query_lower:
            return QueryComplexity.COMPLEX
            
        # Default to moderate
        return QueryComplexity.MODERATE
    
    def _classify_intent(self, query_lower: str) -> QueryIntent:
        """Fast intent classification."""
        
        # Check patterns in order of likelihood
        for intent, pattern in self.intent_patterns.items():
            if pattern.search(query_lower):
                return intent
                
        # Default based on other indicators
        if '?' in query_lower:
            return QueryIntent.FACTUAL
        else:
            return QueryIntent.EXPLORATORY
    
    def _extract_topics(self, query_lower: str) -> List[str]:
        """Fast topic extraction using compiled patterns."""
        topics = []
        
        for topic, pattern in self.topic_patterns.items():
            if pattern.search(query_lower):
                topics.append(topic)
        
        return topics if topics else ["general"]
    
    def _calculate_confidence(self, query_lower: str, complexity: QueryComplexity, intent: QueryIntent, topics: List[str]) -> float:
        """Calculate classification confidence score."""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for strong pattern matches
        pattern_matches = 0
        for patterns in [self.simple_patterns, self.complex_patterns]:
            pattern_matches += sum(1 for p in patterns if p.search(query_lower))
        
        if pattern_matches > 0:
            confidence += min(0.3, pattern_matches * 0.1)
        
        # Boost for topic matches
        confidence += min(0.2, len(topics) * 0.1)
        
        return min(1.0, confidence)
    
    def _determine_strategy(self, complexity: QueryComplexity, intent: QueryIntent, topics: List[str]) -> str:
        """Determine optimal processing strategy."""
        
        # Fast strategies for simple queries
        if complexity == QueryComplexity.SIMPLE:
            if intent == QueryIntent.CREATIVE:
                return "simple_image_search"
            elif intent == QueryIntent.FACTUAL and len(topics) == 1:
                return "single_topic_factual"
            else:
                return "simple_text_search"
        
        # Optimized strategies for moderate queries
        elif complexity == QueryComplexity.MODERATE:
            if intent == QueryIntent.EXPLORATORY:
                return "moderate_exploration"
            else:
                return "moderate_comprehensive"
        
        # Full processing for complex queries
        else:
            return "complex_full_analysis"
    
    def _estimate_response_time(self, complexity: QueryComplexity, intent: QueryIntent, topic_count: int) -> float:
        """Estimate response time for planning and user feedback."""
        
        base_times = {
            QueryComplexity.SIMPLE: 0.5,
            QueryComplexity.MODERATE: 1.5,
            QueryComplexity.COMPLEX: 3.0
        }
        
        base_time = base_times[complexity]
        
        # Adjust for intent
        intent_multipliers = {
            QueryIntent.FACTUAL: 0.8,
            QueryIntent.EXPLORATORY: 1.0,
            QueryIntent.CREATIVE: 0.6,  # Image searches are faster
            QueryIntent.COMPARATIVE: 1.2,
            QueryIntent.ANALYTICAL: 1.4
        }
        
        adjusted_time = base_time * intent_multipliers.get(intent, 1.0)
        
        # Adjust for topic complexity
        topic_factor = 1 + (topic_count * 0.1)
        
        return adjusted_time * topic_factor

# Integration with existing systems
class OptimizedQueryRouter:
    """Route queries using intelligent classification."""
    
    def __init__(self):
        self.classifier = IntelligentQueryClassifier()
        self.strategy_handlers = {
            "simple_image_search": self._handle_simple_image_search,
            "single_topic_factual": self._handle_single_topic_factual,
            "simple_text_search": self._handle_simple_text_search,
            "moderate_exploration": self._handle_moderate_exploration,
            "moderate_comprehensive": self._handle_moderate_comprehensive,
            "complex_full_analysis": self._handle_complex_full_analysis,
        }
    
    async def route_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Route query to optimal processing strategy."""
        
        # Fast classification
        profile = self.classifier.classify_query(query)
        
        # Route to appropriate handler
        handler = self.strategy_handlers.get(profile.processing_strategy)
        if handler:
            return await handler(query, profile, **kwargs)
        else:
            # Fallback to default processing
            return await self._handle_complex_full_analysis(query, profile, **kwargs)
    
    async def _handle_simple_image_search(self, query: str, profile: QueryProfile, **kwargs):
        """Optimized handler for simple image searches."""
        # Skip LLM analysis, use direct image service
        # Fast keyword matching for image search
        pass
    
    async def _handle_single_topic_factual(self, query: str, profile: QueryProfile, **kwargs):
        """Optimized handler for single-topic factual queries."""
        # Use targeted search with topic filtering
        # Skip complex analysis
        pass
    
    # ... other handlers
```

### Step 2: Streamlined Single-Layer Caching (Day 3)

**Objective**: Replace multi-layer caching with optimized single-layer system

**Files to Modify**:
- Create: `backend/core/unified_cache.py`
- Modify: `backend/core/llm_chain.py`
- Remove: Redundant caching layers

**Changes**:

```python
# backend/core/unified_cache.py - NEW FILE
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import asyncio

@dataclass
class CacheEntry:
    """Optimized cache entry with metadata."""
    key: str
    value: Any
    timestamp: float
    access_count: int
    size_bytes: int
    ttl: float
    tags: List[str]
    
class UnifiedCache:
    """High-performance unified caching system."""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: float = 3600):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.current_size = 0
        self.stats = {
            "hits": 0,
            "misses": 0, 
            "evictions": 0,
            "total_requests": 0
        }
        
        # Fast key generation (avoid SHA256 overhead)
        self.key_cache: Dict[str, str] = {}
        
        # Background cleanup task
        self._cleanup_task = None
        self._start_background_cleanup()
    
    def _generate_fast_key(self, data: Union[str, Dict, List]) -> str:
        """Generate cache key optimized for speed over security."""
        
        if isinstance(data, str):
            # For strings, use simple hash (much faster than SHA256)
            raw_key = data.lower().strip()
        else:
            # For complex data, use JSON with sorted keys
            raw_key = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        # Check key cache first
        if raw_key in self.key_cache:
            return self.key_cache[raw_key]
        
        # Use Python's built-in hash (much faster than SHA256)
        # Add prefix to avoid collisions
        fast_key = f"cache_{abs(hash(raw_key))}"
        
        # Cache the key (limit key cache size)
        if len(self.key_cache) < 10000:
            self.key_cache[raw_key] = fast_key
        
        return fast_key
    
    def get(self, key_data: Union[str, Dict, List]) -> Optional[Any]:
        """Get item from cache with fast key generation."""
        cache_key = self._generate_fast_key(key_data)
        self.stats["total_requests"] += 1
        
        if cache_key not in self.cache:
            self.stats["misses"] += 1
            return None
        
        entry = self.cache[cache_key]
        
        # Check TTL
        if time.time() - entry.timestamp > entry.ttl:
            self._remove_entry(cache_key)
            self.stats["misses"] += 1
            return None
        
        # Update access stats
        entry.access_count += 1
        self.stats["hits"] += 1
        
        return entry.value
    
    def set(
        self, 
        key_data: Union[str, Dict, List], 
        value: Any, 
        ttl: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set cache entry with size management."""
        cache_key = self._generate_fast_key(key_data)
        
        # Calculate entry size
        entry_size = self._calculate_size(value)
        
        # Check if entry would exceed max size
        if entry_size > self.max_size_bytes:
            return False
        
        # Ensure space available
        self._ensure_space(entry_size)
        
        # Remove existing entry if updating
        if cache_key in self.cache:
            self._remove_entry(cache_key)
        
        # Create new entry
        entry = CacheEntry(
            key=cache_key,
            value=value,
            timestamp=time.time(),
            access_count=1,
            size_bytes=entry_size,
            ttl=ttl or self.default_ttl,
            tags=tags or []
        )
        
        self.cache[cache_key] = entry
        self.current_size += entry_size
        
        return True
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate object size in bytes."""
        if isinstance(value, str):
            return len(value.encode('utf-8'))
        elif isinstance(value, (list, dict)):
            # Rough estimate for JSON serialization
            return len(json.dumps(value, separators=(',', ':')).encode('utf-8'))
        else:
            # Fallback estimate
            return len(str(value).encode('utf-8'))
    
    def _ensure_space(self, needed_bytes: int):
        """Ensure sufficient space by evicting entries."""
        while self.current_size + needed_bytes > self.max_size_bytes:
            if not self.cache:
                break
                
            # LRU eviction based on access count and age
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: (self.cache[k].access_count, self.cache[k].timestamp)
            )
            
            self._remove_entry(oldest_key)
            self.stats["evictions"] += 1
    
    def _remove_entry(self, cache_key: str):
        """Remove entry and update size tracking."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            self.current_size -= entry.size_bytes
            del self.cache[cache_key]
    
    def _start_background_cleanup(self):
        """Start background cleanup task."""
        async def cleanup_expired():
            while True:
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                await self.cleanup_expired_entries()
        
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(cleanup_expired())
        except RuntimeError:
            # No event loop running, skip background cleanup
            pass
    
    async def cleanup_expired_entries(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total_requests) if total_requests > 0 else 0
        
        return {
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "total_size_mb": self.current_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "utilization": self.current_size / self.max_size_bytes,
            **self.stats
        }
    
    def clear_by_tags(self, tags: List[str]):
        """Clear entries matching any of the provided tags."""
        keys_to_remove = []
        for key, entry in self.cache.items():
            if any(tag in entry.tags for tag in tags):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self._remove_entry(key)

# Integration with existing cache users
class CacheStrategy:
    """Smart caching strategies based on query classification."""
    
    def __init__(self, unified_cache: UnifiedCache):
        self.cache = unified_cache
        self.strategy_configs = {
            "simple_image_search": {"ttl": 7200, "tags": ["images"]},  # 2 hours
            "single_topic_factual": {"ttl": 1800, "tags": ["factual"]},  # 30 minutes  
            "simple_text_search": {"ttl": 3600, "tags": ["simple"]},  # 1 hour
            "moderate_exploration": {"ttl": 1800, "tags": ["moderate"]},  # 30 minutes
            "complex_full_analysis": {"ttl": 900, "tags": ["complex"]},  # 15 minutes
        }
    
    def cache_response(self, query: str, response: str, strategy: str) -> bool:
        """Cache response with strategy-specific settings."""
        config = self.strategy_configs.get(strategy, {"ttl": 3600, "tags": ["default"]})
        
        cache_key = {"query": query, "type": "response"}
        return self.cache.set(cache_key, response, ttl=config["ttl"], tags=config["tags"])
    
    def get_cached_response(self, query: str) -> Optional[str]:
        """Get cached response."""
        cache_key = {"query": query, "type": "response"}
        return self.cache.get(cache_key)
    
    def cache_documents(self, query: str, documents: List[Any], strategy: str) -> bool:
        """Cache retrieved documents."""
        config = self.strategy_configs.get(strategy, {"ttl": 1800, "tags": ["documents"]})
        
        # Serialize documents for caching
        doc_data = [{"content": doc.page_content, "metadata": doc.metadata} for doc in documents]
        
        cache_key = {"query": query, "type": "documents"}
        return self.cache.set(cache_key, doc_data, ttl=config["ttl"], tags=config["tags"])
    
    def get_cached_documents(self, query: str) -> Optional[List[Any]]:
        """Get cached documents."""
        cache_key = {"query": query, "type": "documents"}
        return self.cache.get(cache_key)
```

### Step 3: Smart Cache Pre-warming (Day 4)

**Objective**: Predict and pre-cache likely queries

**Files to Modify**:
- Create: `backend/core/cache_prewarmer.py`
- Modify: `backend/core/app_initializer_v2.py`

**Changes**:

```python
# backend/core/cache_prewarmer.py - NEW FILE
import asyncio
import logging
from typing import Dict, List, Set
from collections import Counter, defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SmartCachePrewarmer:
    """Intelligent cache pre-warming based on usage patterns."""
    
    def __init__(self, unified_cache, query_classifier, query_router):
        self.cache = unified_cache
        self.classifier = query_classifier
        self.router = query_router
        
        # Query pattern analysis
        self.query_patterns = defaultdict(int)
        self.query_frequency = Counter()
        self.session_patterns = []
        
        # Pre-warming strategies
        self.common_queries = [
            "What is Nick's experience?",
            "What skills does Nick have?",
            "Tell me about Nick's background",
            "Show me illustrations",
            "What projects has Nick worked on?",
            "What programming languages does Nick know?",
            "What is Nick's experience with Vue.js?",
            "What companies has Nick worked for?",
        ]
        
        self.seasonal_queries = {
            "hiring_season": [
                "What is Nick's resume?",
                "What is Nick's professional experience?", 
                "What technologies does Nick use?",
                "Nick's previous roles and responsibilities",
            ],
            "portfolio_review": [
                "Show me Nick's creative work",
                "What projects has Nick built?",
                "Examples of Nick's coding projects",
                "Nick's design and illustration portfolio",
            ]
        }
    
    async def analyze_query_patterns(self, queries: List[str]):
        """Analyze query patterns to improve pre-warming."""
        for query in queries:
            # Classify and track patterns
            profile = self.classifier.classify_query(query)
            
            pattern_key = f"{profile.complexity.value}_{profile.intent.value}_{len(profile.topics)}"
            self.query_patterns[pattern_key] += 1
            
            # Track query frequency (normalized)
            normalized_query = self._normalize_query(query)
            self.query_frequency[normalized_query] += 1
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for pattern matching."""
        # Remove specific names, dates, etc., keep the query structure
        normalized = query.lower().strip()
        
        # Replace specific tech terms with placeholders
        tech_terms = ["vue.js", "react", "python", "javascript", "css", "html"]
        for term in tech_terms:
            normalized = normalized.replace(term, "[TECH]")
        
        # Replace company names with placeholder
        companies = ["calendly", "google", "microsoft", "apple", "facebook"]
        for company in companies:
            normalized = normalized.replace(company, "[COMPANY]")
        
        return normalized
    
    async def prewarm_cache(self, strategy: str = "comprehensive"):
        """Pre-warm cache with likely queries."""
        if strategy == "common":
            await self._prewarm_common_queries()
        elif strategy == "seasonal":
            await self._prewarm_seasonal_queries()
        elif strategy == "pattern_based":
            await self._prewarm_pattern_based()
        elif strategy == "comprehensive":
            await self._prewarm_comprehensive()
    
    async def _prewarm_common_queries(self):
        """Pre-warm cache with most common queries."""
        for query in self.common_queries:
            try:
                # Check if already cached
                if self.cache.get({"query": query, "type": "response"}):
                    continue
                
                # Generate and cache response
                profile = self.classifier.classify_query(query)
                result = await self.router.route_query(query)
                
                # Cache with appropriate strategy
                if result and "response" in result:
                    self.cache.set(
                        {"query": query, "type": "response"},
                        result["response"],
                        ttl=7200,  # 2 hours for common queries
                        tags=["prewarmed", "common"]
                    )
                
                # Small delay to avoid overwhelming system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to prewarm query '{query}': {e}")
    
    async def _prewarm_seasonal_queries(self):
        """Pre-warm based on seasonal patterns."""
        current_month = datetime.now().month
        
        # Hiring season (January, February, September)
        if current_month in [1, 2, 9]:
            queries = self.seasonal_queries["hiring_season"]
            tags = ["prewarmed", "hiring_season"]
        # Portfolio review season (March, April, October, November)
        elif current_month in [3, 4, 10, 11]:
            queries = self.seasonal_queries["portfolio_review"]
            tags = ["prewarmed", "portfolio_review"]
        else:
            # Default to common queries
            queries = self.common_queries[:5]
            tags = ["prewarmed", "default"]
        
        for query in queries:
            try:
                if not self.cache.get({"query": query, "type": "response"}):
                    result = await self.router.route_query(query)
                    if result and "response" in result:
                        self.cache.set(
                            {"query": query, "type": "response"},
                            result["response"],
                            ttl=3600,
                            tags=tags
                        )
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Failed to prewarm seasonal query '{query}': {e}")
    
    async def _prewarm_pattern_based(self):
        """Pre-warm based on observed query patterns."""
        # Use most frequent query patterns to generate likely queries
        top_patterns = self.query_frequency.most_common(10)
        
        for normalized_query, frequency in top_patterns:
            if frequency < 3:  # Only prewarm frequently asked queries
                continue
            
            # Generate variations of successful patterns
            variations = self._generate_query_variations(normalized_query)
            
            for variation in variations:
                try:
                    if not self.cache.get({"query": variation, "type": "response"}):
                        result = await self.router.route_query(variation)
                        if result and "response" in result:
                            self.cache.set(
                                {"query": variation, "type": "response"},
                                result["response"],
                                ttl=1800,  # 30 minutes for pattern-based
                                tags=["prewarmed", "pattern_based"]
                            )
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Failed to prewarm pattern query '{variation}': {e}")
    
    def _generate_query_variations(self, normalized_query: str) -> List[str]:
        """Generate variations of successful query patterns."""
        variations = []
        
        # Replace placeholders with actual values
        if "[TECH]" in normalized_query:
            techs = ["Vue.js", "Python", "JavaScript", "React", "CSS"]
            for tech in techs:
                variations.append(normalized_query.replace("[TECH]", tech))
        
        if "[COMPANY]" in normalized_query:
            companies = ["Calendly", "previous companies", "current company"]
            for company in companies:
                variations.append(normalized_query.replace("[COMPANY]", company))
        
        # If no placeholders, return original (de-normalized)
        if not variations:
            variations.append(normalized_query)
        
        return variations[:3]  # Limit variations
    
    async def _prewarm_comprehensive(self):
        """Comprehensive pre-warming strategy."""
        try:
            # Run all strategies with reduced query sets
            await self._prewarm_common_queries()
            await asyncio.sleep(1)
            
            await self._prewarm_seasonal_queries()
            await asyncio.sleep(1)
            
            if len(self.query_frequency) > 5:  # Only if we have pattern data
                await self._prewarm_pattern_based()
            
            logger.info("Cache pre-warming completed successfully")
            
        except Exception as e:
            logger.error(f"Comprehensive pre-warming failed: {e}")
    
    def get_prewarming_stats(self) -> Dict[str, Any]:
        """Get pre-warming statistics."""
        cache_stats = self.cache.get_cache_stats()
        
        return {
            "cache_stats": cache_stats,
            "query_patterns": dict(self.query_patterns),
            "frequent_queries": dict(self.query_frequency.most_common(10)),
            "total_patterns": len(self.query_patterns),
        }
```

### Step 4: Integration & Performance Monitoring (Day 5)

**Objective**: Integrate all improvements and add performance monitoring

**Files to Modify**:
- Modify: `backend/core/llm_chain.py` 
- Modify: `backend/routes/query.py`
- Create: `backend/core/performance_monitor.py`

**Changes**:

```python
# backend/routes/query.py - Integration
from ..core.query_classifier import IntelligentQueryClassifier, OptimizedQueryRouter
from ..core.unified_cache import UnifiedCache, CacheStrategy
from ..core.cache_prewarmer import SmartCachePrewarmer

# Initialize optimized systems
query_classifier = IntelligentQueryClassifier()
unified_cache = UnifiedCache(max_size_mb=50, default_ttl=1800)
cache_strategy = CacheStrategy(unified_cache)
query_router = OptimizedQueryRouter()
cache_prewarmer = SmartCachePrewarmer(unified_cache, query_classifier, query_router)

@router.post("/query")
async def query_endpoint_optimized(request: Request, query: Query, services: dict = Depends(get_services)):
    """Optimized query endpoint with intelligent routing and caching."""
    
    start_time = time.time()
    client_ip = get_remote_address(request)
    
    # Security validation (unchanged)
    is_valid, error_msg = SecurityValidator.validate_query(query, client_ip)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    sanitized_question = SecurityValidator.sanitize_input(query.question)
    
    # NEW: Fast query classification
    query_profile = query_classifier.classify_query(sanitized_question)
    
    # NEW: Check unified cache first
    cached_response = cache_strategy.get_cached_response(sanitized_question)
    if cached_response:
        # Return cached response immediately
        headers = {
            "X-Cache-Hit": "true",
            "X-Processing-Strategy": query_profile.processing_strategy,
            "X-Estimated-Time": str(query_profile.estimated_response_time)
        }
        return JSONResponse(content={"answer": cached_response}, headers=headers)
    
    # NEW: Route query using optimized strategy
    try:
        result = await query_router.route_query(
            sanitized_question, 
            profile=query_profile,
            services=services,
            client_ip=client_ip
        )
        
        # Cache successful response
        if result and "answer" in result:
            cache_strategy.cache_response(
                sanitized_question, 
                result["answer"], 
                query_profile.processing_strategy
            )
        
        # Performance headers
        processing_time = time.time() - start_time
        headers = {
            "X-Cache-Hit": "false",
            "X-Processing-Strategy": query_profile.processing_strategy,
            "X-Actual-Time": str(processing_time),
            "X-Estimated-Time": str(query_profile.estimated_response_time)
        }
        
        return JSONResponse(content=result, headers=headers)
        
    except Exception as e:
        logger.error(f"Optimized query processing failed: {e}")
        # Fallback to original processing
        return await original_query_processing(...)

# Performance monitoring
class PerformanceMonitor:
    """Monitor query performance and optimization effectiveness."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.strategy_performance = defaultdict(lambda: {"count": 0, "total_time": 0, "avg_time": 0})
    
    def record_query_performance(self, query: str, profile, processing_time: float, cache_hit: bool):
        """Record query performance metrics."""
        
        self.metrics["processing_times"].append(processing_time)
        self.metrics["cache_hits"].append(cache_hit)
        
        # Track strategy performance
        strategy = profile.processing_strategy
        stats = self.strategy_performance[strategy]
        stats["count"] += 1
        stats["total_time"] += processing_time
        stats["avg_time"] = stats["total_time"] / stats["count"]
        
        # Track accuracy of time estimates
        estimated_time = profile.estimated_response_time
        accuracy = abs(processing_time - estimated_time) / estimated_time if estimated_time > 0 else 1
        self.metrics["time_estimate_accuracy"].append(1 - accuracy)  # Convert to accuracy score
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        
        processing_times = self.metrics["processing_times"]
        cache_hits = self.metrics["cache_hits"]
        
        if not processing_times:
            return {"error": "No performance data available"}
        
        cache_hit_rate = sum(cache_hits) / len(cache_hits) if cache_hits else 0
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        return {
            "query_count": len(processing_times),
            "avg_processing_time": avg_processing_time,
            "cache_hit_rate": cache_hit_rate,
            "strategy_performance": dict(self.strategy_performance),
            "time_estimate_accuracy": sum(self.metrics["time_estimate_accuracy"]) / len(self.metrics["time_estimate_accuracy"]) if self.metrics["time_estimate_accuracy"] else 0,
            "95th_percentile_time": sorted(processing_times)[int(0.95 * len(processing_times))] if len(processing_times) > 20 else max(processing_times)
        }
```

## Testing & Validation

### Performance Tests

```python
# tests/performance/test_week3_optimizations.py
import pytest
import time
from backend.core.query_classifier import IntelligentQueryClassifier
from backend.core.unified_cache import UnifiedCache

def test_query_classification_speed():
    """Test query classification performance."""
    classifier = IntelligentQueryClassifier()
    
    queries = [
        "What is Nick's experience?",
        "Show me creative illustrations",
        "How does Nick approach software architecture?",
        "List Nick's technical skills"
    ]
    
    start = time.time()
    for query in queries * 10:  # 40 classifications
        profile = classifier.classify_query(query)
        assert profile.confidence > 0.5
    
    duration = time.time() - start
    avg_time = duration / 40
    
    # Should be very fast (< 10ms per classification)
    assert avg_time < 0.01

def test_unified_cache_performance():
    """Test unified cache performance."""
    cache = UnifiedCache(max_size_mb=10)
    
    # Test write performance
    start = time.time()
    for i in range(1000):
        cache.set(f"key_{i}", f"value_{i}" * 100)
    write_duration = time.time() - start
    
    # Test read performance
    start = time.time()
    hits = 0
    for i in range(1000):
        if cache.get(f"key_{i}"):
            hits += 1
    read_duration = time.time() - start
    
    # Performance assertions
    assert write_duration < 1.0  # 1000 writes in under 1 second
    assert read_duration < 0.5   # 1000 reads in under 0.5 seconds
    assert hits == 1000          # All cache hits

@pytest.mark.asyncio
async def test_cache_prewarming():
    """Test cache pre-warming effectiveness."""
    cache = UnifiedCache()
    classifier = IntelligentQueryClassifier()
    router = OptimizedQueryRouter()
    
    prewarmer = SmartCachePrewarmer(cache, classifier, router)
    
    # Pre-warm common queries
    await prewarmer.prewarm_cache("common")
    
    # Check cache utilization
    stats = cache.get_cache_stats()
    assert stats["total_entries"] > 5
    assert stats["utilization"] > 0.1
```

## Success Metrics

### Performance Targets
- **Query Classification**: < 10ms per query (vs 1-2s LLM analysis)
- **Cache Hit Rate**: > 40% for common queries
- **Cache Response Time**: < 50ms for cached responses  
- **Overall Response Time**: Additional 15-25% improvement

### Intelligence Targets
- **Classification Accuracy**: > 90% for query complexity/intent
- **Strategy Effectiveness**: Different strategies show measurable performance differences
- **Pre-warming Success**: > 30% cache hit rate within first hour

## Rollout Plan

1. **Day 1-2**: Implement intelligent query classification
2. **Day 3**: Deploy unified caching system  
3. **Day 4**: Add smart cache pre-warming
4. **Day 5**: Integration and performance monitoring
5. **Day 6-7**: Validation and fine-tuning

This week completes the performance optimization trilogy by adding intelligence and optimal caching on top of the async improvements from previous weeks.