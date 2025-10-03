import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Type, Union, cast

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI

from .config_v2 import AppConfig
from .query_logger import get_query_logger

# Import API key manager for secure key retrieval
try:
    from .api_key_manager import api_key_manager

    API_KEY_MANAGER_AVAILABLE = True
except ImportError:
    API_KEY_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)


# --- Dynamic Configuration ---
def get_primary_llm() -> str:
    """
    Get the response LLM from database settings with fallback to environment.

    UPDATED: Now uses response_llm setting (what users see in chat).
    Fallback chain: Database response_llm → Legacy primary_llm → Environment → Default
    """
    try:
        # Try to get from database settings first
        from .settings_manager import get_settings_manager

        settings_manager = get_settings_manager()

        # Use new response LLM setting
        response_llm = settings_manager.get_response_llm()

        # Validate the database value
        valid_llms = ["claude", "gemini"]
        if response_llm in valid_llms:
            logger.debug(f"Using response LLM from database settings: {response_llm}")
            return response_llm
        else:
            logger.warning(f"Invalid response LLM in database: {response_llm}, falling back to legacy primary_llm")

            # Fallback to legacy primary_llm for backward compatibility
            system_config = settings_manager.get_system_config_settings()
            legacy_primary = system_config.primary_llm
            if legacy_primary in valid_llms:
                logger.debug(f"Using legacy primary LLM from database: {legacy_primary}")
                return legacy_primary
    except Exception as e:
        logger.debug(f"Could not get LLM settings from database: {e}, using environment fallback")

    # Fallback to environment variable
    env_primary_llm = AppConfig.get_primary_llm()
    logger.debug(f"Using primary LLM from environment: {env_primary_llm}")
    return env_primary_llm


# --- Configuration ---
GEMINI_MODEL = AppConfig.get_gemini_model()

# Model name constants
FAST_MODEL = "claude_haiku"
QUALITY_MODEL = "claude"

# Default configuration values (replacing legacy data_source_config)
DEFAULT_PROMPTS = {
    "system_template": """You are Nick Berens' AI assistant. You help visitors learn about Nick's
professional background, skills, experience, and interests. Use the following pieces of context to
answer the question. If you don't know the answer based on the context provided, just say you don't
have that information.

Context: {context}

Answer as Nick would, in a friendly and professional tone. Keep responses concise but informative.""",
    "history_aware": """Given a chat history and the latest user question which might reference the
chat history, formulate a standalone question which can be understood without the chat history. Do NOT
answer the question, just reformulate it if needed and otherwise return it as is.""",
}


CLAUDE_MODEL = AppConfig.get_claude_model()
EMBEDDING_MODEL = AppConfig.get_embedding_model()
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))


def _get_response_caching_settings() -> tuple[bool, int]:
    """Fetch caching enabled flag and TTL from DB ResponseSettings with env fallback."""
    try:
        from .settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        rs = settings_manager.get_response_settings()
        # Respect module-level ENABLE_CACHING as a master switch for tests/env overrides
        enabled = bool(ENABLE_CACHING and getattr(rs, "enable_caching", True))
        ttl = int(getattr(rs, "cache_ttl_seconds", CACHE_TTL))
        # Bound TTL to sane limits as ResponseSettings does
        ttl = max(60, min(86400, ttl))
        return enabled, ttl
    except Exception:
        return ENABLE_CACHING, CACHE_TTL


def get_max_cache_size() -> int:
    """
    Get the max cache size from admin settings with fallback to environment.

    Returns the configured max cache size from database settings with fallback
    to environment variable and default.
    """
    try:
        from .settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        system_config = settings_manager.get_system_config_settings()
        return system_config.max_cache_size
    except Exception as e:
        logger.warning(f"Failed to get max_cache_size from settings, using fallback: {e}")
        return int(os.getenv("MAX_CACHE_SIZE", "100"))


# --- LLM Provider Configuration ---
LLM_PROVIDERS = [
    {
        "name": "claude",
        "class": ChatAnthropic,
        "model": CLAUDE_MODEL,
        "init_kwargs": {"model": CLAUDE_MODEL, "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
    },
    {
        "name": "claude_haiku",
        "class": ChatAnthropic,
        "model": "claude-3-haiku-20240307",
        "init_kwargs": {"model": "claude-3-haiku-20240307", "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
    },
    {
        "name": "gemini",
        "class": ChatGoogleGenerativeAI,
        "model": GEMINI_MODEL,
        "init_kwargs": {"model": GEMINI_MODEL, "temperature": 0.7, "timeout": REQUEST_TIMEOUT},
    },
]


# --- Rate Limit Tracking ---
class RateLimitTracker:
    """Track rate limit status for different LLM providers"""

    def __init__(self):
        self._rate_limit_status: Dict[str, bool] = {}
        self._rate_limit_reset_time: Dict[str, datetime] = {}
        self._lock = RLock()

    def is_rate_limited(self, provider: str) -> bool:
        """Check if a provider is currently rate limited - FIXED thread safety"""
        with self._lock:
            if provider not in self._rate_limit_status:
                return False
            if provider in self._rate_limit_reset_time and datetime.now() > self._rate_limit_reset_time[provider]:
                self.clear_rate_limit(provider)
                return False
            return self._rate_limit_status.get(provider, False)

    def set_rate_limited(self, provider: str, reset_minutes: int = 60):
        """Mark a provider as rate limited"""
        with self._lock:
            self._rate_limit_status[provider] = True
            self._rate_limit_reset_time[provider] = datetime.now() + timedelta(minutes=reset_minutes)
        logger.warning(f"{provider} rate limit hit, will reset at {self._rate_limit_reset_time[provider]}")

    def clear_rate_limit(self, provider: str):
        """Clear rate limit status for a provider"""
        with self._lock:
            self._rate_limit_status[provider] = False
            if provider in self._rate_limit_reset_time:
                del self._rate_limit_reset_time[provider]
        logger.info(f"{provider} rate limit cleared")

    def get_status(self) -> Dict[str, bool]:
        """Get current rate limit status for all providers, clearing expired ones."""
        with self._lock:
            current_time = datetime.now()
            for provider, reset_time in list(self._rate_limit_reset_time.items()):
                if current_time > reset_time:
                    self._rate_limit_status[provider] = False
                    if provider in self._rate_limit_reset_time:
                        del self._rate_limit_reset_time[provider]
            return self._rate_limit_status.copy()


# Global rate limit tracker
rate_limit_tracker = RateLimitTracker()

# --- Caching Layers ---
_response_cache: Dict[str, Dict[str, Any]] = {}
_retrieval_cache: Dict[str, Dict[str, Any]] = {}


def select_optimal_model_for_query(query: str, preferred_model: Optional[str] = None) -> str:
    """
    Select the optimal LLM model based on query complexity.

    Claude Haiku: Fast, cheap, good for simple factual queries
    Claude Sonnet: Slower, expensive, better for complex reasoning
    """
    from ..security.validator import SecurityValidator

    # If user explicitly prefers a model, validate and respect that
    if preferred_model:
        if (
            preferred_model in [p["name"] for p in LLM_PROVIDERS]
            and preferred_model in SecurityValidator.ALLOWED_MODELS
        ):
            return preferred_model
        else:
            logger.warning(f"Preferred model '{preferred_model}' not allowed, falling back to default")
            # Fall through to default selection logic

    # Check if response smart selection is enabled
    try:
        from .settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        smart_selection_enabled = settings_manager.is_response_smart_selection_enabled()
    except Exception as e:
        logger.debug(f"Could not get smart selection setting: {e}, falling back to legacy setting")
        smart_selection_enabled = AppConfig.ENABLE_SMART_MODEL_SELECTION

    if not smart_selection_enabled:
        logger.debug("Response smart selection disabled, using primary LLM")
        return get_primary_llm()

    # Analyze query complexity
    query_lower = query.lower()

    # Simple query indicators (good for Haiku - 30-60% faster)
    simple_indicators = [
        "what programming languages",
        "what technologies",
        "what skills",
        "list",
        "show me",
        "tell me about",
        "experience with",
        "know about",
        "background in",
    ]

    # Complex query indicators (need Sonnet for quality)
    complex_indicators = [
        "how does",
        "why",
        "explain",
        "approach to",
        "philosophy",
        "compare",
        "analyze",
        "strategy",
        "architecture",
        "design pattern",
        "best practices",
    ]

    # Check for simple queries
    is_simple = any(indicator in query_lower for indicator in simple_indicators)
    is_complex = any(indicator in query_lower for indicator in complex_indicators)

    # Short queries are usually simple
    is_short = len(query.split()) <= 10

    # Get response LLM preference and perform family-based smart selection
    response_llm = get_primary_llm()  # This now returns response_llm

    # Smart selection within response model families
    if response_llm == "gemini":
        # Gemini family: Currently only one model, but future-ready for gemini-pro
        if is_complex:
            # For complex queries, could use gemini-pro in future
            logger.debug(f"Using Gemini for complex query: '{query[:50]}...'")
            selected_model = "gemini"
        else:
            # For simple/moderate queries, use standard Gemini
            logger.debug(f"Using Gemini for query: '{query[:50]}...'")
            selected_model = "gemini"

    elif response_llm == "claude":
        # Claude family: Smart selection between Haiku (fast) and Sonnet (quality)
        if is_simple and not is_complex and is_short:
            logger.debug(f"Using Claude Haiku for simple query: '{query[:50]}...'")
            selected_model = FAST_MODEL  # claude_haiku
        elif is_complex:
            logger.debug(f"Using Claude Sonnet for complex query: '{query[:50]}...'")
            selected_model = QUALITY_MODEL  # claude
        else:
            # Default to Haiku for moderate queries (speed over perfection)
            logger.debug(f"Using Claude Haiku for moderate query: '{query[:50]}...'")
            selected_model = FAST_MODEL  # claude_haiku
    else:
        # Fallback to response LLM if unknown
        logger.debug(f"Unknown response LLM '{response_llm}', using as-is")
        selected_model = response_llm

    # Final validation to ensure selected model is allowed
    if selected_model not in SecurityValidator.ALLOWED_MODELS:
        logger.warning(f"Selected model '{selected_model}' not in allowed models, falling back to primary")
        return get_primary_llm()

    return selected_model


def route_query_to_retrievers(query: str, retrievers: Dict[str, BaseRetriever]) -> List[BaseRetriever]:
    """
    Route a query to a LangChain-compatible retriever.

    Prefer the wrapped `unified` retriever (BaseRetriever) for compatibility with
    LangChain's history-aware utilities and async `.ainvoke`. If only the raw
    `_unified_retriever` instance is present, adapt it by calling `.get_retriever()`.
    """
    # Prefer the LangChain BaseRetriever wrapper when available
    if "unified" in retrievers:
        logger.debug(f"Using unified BaseRetriever for query: '{query}'")
        return [retrievers["unified"]]

    # Fallback: adapt the raw UnifiedRetriever instance to a BaseRetriever
    if "_unified_retriever" in retrievers:
        try:
            from .unified_retriever import UnifiedRetriever  # local import to avoid cycles

            unified_raw = retrievers["_unified_retriever"]
            if isinstance(unified_raw, UnifiedRetriever):
                adapted = unified_raw.get_retriever()
                logger.debug(f"Adapted raw UnifiedRetriever to BaseRetriever for query: '{query}'")
                return [adapted]
        except Exception as e:
            logger.warning(f"Failed to adapt UnifiedRetriever to BaseRetriever: {e}")

    logger.error("Unified retriever not found in retrievers dictionary")
    return []


async def async_retrieve_documents(
    query: str, retrievers: Dict[str, BaseRetriever], tenant_id: Optional[str] = None
) -> List[Document]:
    """
    Async document retrieval with enhanced performance optimizations and tenant support.

    SECURITY: When tenant_id is provided, ONLY retrieves tenant-scoped documents.
    Never includes shared documents to prevent cross-tenant data leakage.
    """
    from .unified_retriever import UnifiedRetriever

    # The actual UnifiedRetriever instance is stored under "_unified_retriever"
    unified_retriever = retrievers.get("_unified_retriever")
    if unified_retriever and isinstance(unified_retriever, UnifiedRetriever):
        logger.debug("Using async unified retriever for enhanced performance")
        try:
            # Use tenant-aware auto-routing if tenant_id is provided and supported
            if tenant_id and hasattr(unified_retriever, "semantic_search_for_tenant"):
                # SECURITY: Tenant-scoped search with NO shared documents
                docs = await asyncio.to_thread(unified_retriever.semantic_search_for_tenant, query, tenant_id)
                logger.debug(
                    f"Async tenant-scoped retrieval successful, got {len(docs)} documents for tenant {tenant_id}"
                )
            else:
                # Use async auto-routing for better performance (non-tenant scenarios only)
                docs = await asyncio.to_thread(unified_retriever.auto_route_query, query)
                logger.debug(f"Async retrieval successful, got {len(docs)} documents")
            return docs
        except Exception as e:
            logger.warning(f"Async retrieval failed: {e}")
            # SECURITY: Return empty list on failure - do NOT fall back to non-tenant retrieval
            # Better to fail safely than to potentially leak tenant data
            return []
    else:
        logger.warning("Unified retriever not available, falling back to route_query_to_retrievers")
        # Fallback to route_query_to_retrievers instead of returning empty list
        selected_retrievers = route_query_to_retrievers(query, retrievers)
        if selected_retrievers:
            # Use the first available retriever with async invoke
            try:
                docs = await selected_retrievers[0].ainvoke(query)
                # Ensure we return a flat list of Document objects
                if isinstance(docs, list):
                    flat_docs = []
                    for item in docs:
                        if isinstance(item, list):
                            flat_docs.extend(item)
                        else:
                            flat_docs.append(item)
                    return flat_docs
                return [docs] if docs else []
            except Exception as e:
                logger.error(f"Fallback retrieval failed: {e}")
                return []
        return []


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error or overload error"""
    if hasattr(error, "status_code") and error.status_code in [429, 529]:
        return True
    error_str = str(error).lower()
    rate_limit_indicators = [
        "rate limit",
        "quota exceeded",
        "too many requests",
        "429",
        "529",
        "resource exhausted",
        "rate_limit_exceeded",
        "rate_limit_error",
        "overloaded",
        "overloaded_error",
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)


def is_authentication_error(error: Exception) -> bool:
    """Detect authentication failures (e.g., invalid API key, 401).

    Uses string heuristics to avoid tight coupling to vendor exception types.
    """
    try:
        msg = str(error).lower()
    except Exception:
        msg = ""
    return "authentication" in msg or "invalid x-api-key" in msg or "401" in msg or "unauthorized" in msg


def get_api_key_for_provider(provider_type: str) -> Optional[str]:
    """
    Get API key for a provider, preferring database storage over environment variables.

    Args:
        provider_type: Type of provider ('anthropic', 'google', 'openai')

    Returns:
        API key string or None if not found
    """
    if API_KEY_MANAGER_AVAILABLE:
        try:
            # Try to get from database first
            api_key = api_key_manager.get_api_key_by_type(provider_type)
            if api_key:
                logger.debug(f"Using database-stored API key for {provider_type}")
                return api_key
        except Exception as e:
            logger.warning(f"Failed to get {provider_type} API key from database: {e}")

    # Fallback to environment variables
    env_var_map = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY"}

    env_var = env_var_map.get(provider_type)
    if env_var:
        api_key = os.getenv(env_var)
        if api_key:
            logger.debug(f"Using environment variable {env_var} for {provider_type}")
            return api_key

    logger.warning(f"No API key found for {provider_type}")
    return None


def get_llm_instances() -> Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]]:
    """Initializes and returns a dictionary of available LLM instances with managed API keys."""
    llms: Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]] = {}
    for provider_config in LLM_PROVIDERS:
        provider_name: str = cast(str, provider_config["name"])
        provider_class: Type[Union[ChatGoogleGenerativeAI, ChatAnthropic]] = cast(
            Type[Union[ChatGoogleGenerativeAI, ChatAnthropic]],
            provider_config["class"],
        )
        init_kwargs: Dict[str, Any] = cast(Dict[str, Any], provider_config["init_kwargs"]).copy()

        try:
            if not rate_limit_tracker.is_rate_limited(provider_name):
                # Get API key for this provider type
                provider_type_map = {"claude": "anthropic", "claude_haiku": "anthropic", "gemini": "google"}
                provider_type = provider_type_map.get(provider_name)

                if provider_type:
                    api_key = get_api_key_for_provider(provider_type)
                    if api_key:
                        # Add API key to init kwargs
                        if provider_type == "anthropic":
                            init_kwargs["api_key"] = api_key
                        elif provider_type == "google":
                            init_kwargs["google_api_key"] = api_key

                        llms[provider_name] = provider_class(**init_kwargs)
                        logger.info(f"{provider_name.title()} model initialized successfully with managed API key")
                    else:
                        logger.warning(f"No API key available for {provider_name}, skipping initialization")
                        llms[provider_name] = None
                else:
                    # Fallback for unknown provider types - use original initialization
                    llms[provider_name] = provider_class(**init_kwargs)
                    logger.info(f"{provider_name.title()} model initialized with environment variables")
            else:
                logger.warning(f"{provider_name.title()} is rate limited, skipping initialization")
                llms[provider_name] = None
        except Exception as e:
            logger.warning(f"Failed to initialize {provider_name.title()}: {e}")
            llms[provider_name] = None

    if not any(llms.values()):
        raise RuntimeError("No LLM models could be initialized. Check API keys and model names.")
    return llms


def _build_dynamic_system_prompt() -> str:
    """Build system prompt with response settings guidance."""
    try:
        from .settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        response_settings = settings_manager.get_response_settings()

        # Length guidance mapping
        length_guidance = {
            "brief": "Provide a concise, brief response in 1-2 sentences.",
            "medium": "Provide a thorough response in 2-3 paragraphs.",
            "detailed": "Provide a comprehensive, detailed response with full explanations.",
            "comprehensive": "Provide an extensive, comprehensive response covering all aspects.",
        }

        length_instruction = length_guidance.get(response_settings.preferred_response_length, length_guidance["medium"])

        # Style guidance mapping
        style_guidance = {
            "professional": "Use a professional, formal tone.",
            "conversational": "Use a friendly, conversational tone.",
            "technical": "Use precise, technical language with specific details.",
            "casual": "Use a casual, relaxed tone.",
        }

        style_instruction = style_guidance.get(response_settings.response_style, style_guidance["conversational"])

        # Build prompt with dynamic guidance
        DEFAULT_PROMPTS.get("system_template", "")

        # Enhanced prompt with response settings
        enhanced_prompt = (
            "You are Nick Berens' expert digital assistant. Your role is to answer questions about his "
            "skills, experience, and work based *only* on the provided context."
            "\n\n"
            "**⚠️ ABSOLUTE RULE - CONTEXT ADHERENCE:**"
            "\n"
            "You MUST ONLY answer questions using information explicitly present in the provided context below. "
            "If the context does not contain the answer, you MUST respond with: "
            '"I don\'t have that information in my knowledge base about Nick Berens."'
            "\n"
            "**DO NOT:**"
            "\n- Use your general knowledge or training data"
            "\n- Make inferences beyond what's explicitly stated in the context"
            "\n- Answer questions about topics not covered in the context"
            "\n\n"
            "**RESPONSE GUIDELINES:**"
            f"\n- Length: {length_instruction}"
            f"\n- Style: {style_instruction}"
            "\n\n"
            "**CRITICAL INSTRUCTIONS:**"
            "\n"
            "1.  **Persona:** When the user asks about 'you' or 'your' experience (e.g., 'What is your "
            "experience?'), always respond about Nick Berens in the third person (e.g., 'Nick's experience "
            "is...')."
            "\n"
            "2.  **Resume Requests:** If asked for the resume (e.g., 'Show me your resume'), synthesize the "
            "provided resume context into a clear, professional summary. **NEVER** state that you are an AI "
            "or do not have a resume. The user is asking for Nick's resume, and the context provided is the "
            "source for it."
            "\n"
            "3.  **Formatting:** Use markdown, such as bullet points, to structure information like work "
            "experience or skills for readability."
            "\n\n"
            "**Provided Context:**\n{context}"
        )

        return enhanced_prompt

    except Exception as e:
        logger.warning(f"Failed to build dynamic system prompt: {e}")
        # Fallback to default prompt
        return DEFAULT_PROMPTS.get(
            "system_template",
            (
                "You are Nick Berens' expert digital assistant. Your role is to answer questions about his "
                "skills, experience, and work based *only* on the provided context. Speak in a helpful and "
                "professional tone."
                "\n\n"
                "**⚠️ ABSOLUTE RULE - CONTEXT ADHERENCE:**"
                "\n"
                "You MUST ONLY answer questions using information explicitly present in the provided context below. "
                "If the context does not contain the answer, you MUST respond with: "
                '"I don\'t have that information in my knowledge base about Nick Berens."'
                "\n"
                "**DO NOT:**"
                "\n- Use your general knowledge or training data"
                "\n- Make inferences beyond what's explicitly stated in the context"
                "\n- Answer questions about topics not covered in the context"
                "\n\n"
                "**CRITICAL INSTRUCTIONS:**"
                "\n"
                "1.  **Persona:** When the user asks about 'you' or 'your' experience (e.g., 'What is your "
                "experience?'), always respond about Nick Berens in the third person (e.g., 'Nick's experience "
                "is...')."
                "\n"
                "2.  **Resume Requests:** If asked for the resume (e.g., 'Show me your resume'), synthesize the "
                "provided resume context into a clear, professional summary. **NEVER** state that you are an AI "
                "or do not have a resume. The user is asking for Nick's resume, and the context provided is the "
                "source for it."
                "\n"
                "3.  **Formatting:** Use markdown, such as bullet points, to structure information like work "
                "experience or skills for readability."
                "\n\n"
                "**Provided Context:**\n{context}"
            ),
        )


def create_qa_chain(llm: BaseLanguageModel) -> Runnable:
    """Creates the main question-answering chain with dynamic response settings."""
    system_prompt = _build_dynamic_system_prompt()
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    return create_stuff_documents_chain(llm, prompt)


def create_history_aware_prompt() -> ChatPromptTemplate:
    """Creates a prompt template for reformulating questions based on chat history."""
    contextualize_q_system_prompt = DEFAULT_PROMPTS.get(
        "history_aware",
        (
            "Given a chat history and the latest user question which might reference the chat history, "
            "formulate a standalone question which can be understood without the chat history. "
            "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
        ),
    )
    return ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
        ]
    )


class CacheManager:
    """Manages caching operations for responses and retrievals"""

    @staticmethod
    def get_cache_key(
        user_input: Optional[str],
        chat_history: Optional[List] = None,
        model: Optional[str] = None,
        additional_context: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Generate a comprehensive cache key including user input, chat history, model, and settings.

        Args:
            user_input: The user's query
            chat_history: Chat conversation history
            model: Model being used for generation
            additional_context: Additional context like settings, thresholds, etc.

        Returns:
            SHA256 hash of all relevant factors for caching
        """
        enabled, _ttl = _get_response_caching_settings()
        if not enabled or not isinstance(user_input, str):
            return None

        # Normalize user input
        normalized_input = re.sub(r"[^\w\s]", "", user_input.lower()).strip()

        # Create cache key components
        cache_components = [normalized_input]

        # Add chat history length and hash of recent messages
        if chat_history:
            history_length = len(chat_history)
            cache_components.append(f"hist_len:{history_length}")

            # Include hash of last few messages for context sensitivity
            if history_length > 0:
                recent_messages = chat_history[-3:] if history_length > 3 else chat_history
                history_text = "".join(
                    [str(msg.get("content", "")) for msg in recent_messages if isinstance(msg, dict)]
                )
                history_hash = hashlib.md5(history_text.encode("utf-8")).hexdigest()[:8]
                cache_components.append(f"hist_hash:{history_hash}")
        else:
            cache_components.append("hist_len:0")

        # Add model information
        from backend.core.config_v2 import AppConfig

        model_name = model or getattr(AppConfig, "CLAUDE_MODEL", "default")
        cache_components.append(f"model:{model_name}")

        # Add relevant configuration that affects retrieval/generation

        config_hash_parts = [
            f"threshold:{AppConfig.get_rag_score_threshold()}",
            f"max_results:{AppConfig.get_max_results()}",
            f"mmr:{AppConfig.get_rag_use_mmr()}",
        ]

        if additional_context:
            for key, value in sorted(additional_context.items()):
                config_hash_parts.append(f"{key}:{value}")

        config_hash = hashlib.md5(":".join(config_hash_parts).encode("utf-8")).hexdigest()[:8]
        cache_components.append(f"config:{config_hash}")

        # Generate final cache key
        cache_key_string = "|".join(cache_components)
        return hashlib.sha256(cache_key_string.encode("utf-8")).hexdigest()

    @staticmethod
    def get_cached_response(cache_key: str) -> Optional[str]:
        enabled, ttl = _get_response_caching_settings()
        if not cache_key or not enabled:
            return None
        if cache_key in _response_cache:
            cached_data = _response_cache[cache_key]
            if time.time() - cached_data["timestamp"] < ttl:
                logger.info(f"Response cache hit for key: {cache_key}")
                return str(cached_data["response"])
            else:
                del _response_cache[cache_key]
                logger.info(f"Stale response cache entry removed: {cache_key}")
        return None

    @staticmethod
    def cache_response(cache_key: str, response_chunks: List[str]):
        enabled, _ttl = _get_response_caching_settings()
        if not cache_key or not enabled:
            return
        if len(_response_cache) >= get_max_cache_size():
            oldest_key = min(_response_cache, key=lambda k: _response_cache[k]["timestamp"])
            del _response_cache[oldest_key]
            logger.info(f"Evicted oldest response cache entry: {oldest_key}")
        full_response = "".join(response_chunks)
        _response_cache[cache_key] = {"response": full_response, "timestamp": time.time()}
        logger.info(f"Cached full response for key: {cache_key}")

    @staticmethod
    def get_cached_retrieval(cache_key: str) -> Optional[List[Document]]:
        enabled, ttl = _get_response_caching_settings()
        if not cache_key or not enabled:
            return None
        if cache_key in _retrieval_cache:
            cached_data = _retrieval_cache[cache_key]
            if time.time() - cached_data["timestamp"] < ttl:
                logger.info(f"Retrieval cache hit for key: {cache_key}")
                return cast(List[Document], cached_data["documents"])
            else:
                del _retrieval_cache[cache_key]
                logger.info(f"Stale retrieval cache entry removed: {cache_key}")
        return None

    @staticmethod
    def cache_retrieval(cache_key: str, documents: List[Document]):
        enabled, _ttl = _get_response_caching_settings()
        if not cache_key or not enabled:
            return
        if len(_retrieval_cache) >= get_max_cache_size():
            oldest_key = min(_retrieval_cache, key=lambda k: _retrieval_cache[k]["timestamp"])
            del _retrieval_cache[oldest_key]
            logger.info(f"Evicted oldest retrieval cache entry: {oldest_key}")
        _retrieval_cache[cache_key] = {"documents": documents, "timestamp": time.time()}
        logger.info(f"Stored {len(documents)} documents in retrieval cache for key: {cache_key}")


# Wrapper functions for backward compatibility (aliases to CacheManager)
def get_cache_key(
    user_input: Optional[str],
    chat_history: Optional[List] = None,
    model: Optional[str] = None,
    additional_context: Optional[Dict] = None,
) -> Optional[str]:
    return CacheManager.get_cache_key(user_input, chat_history, model, additional_context)


def get_cached_response(cache_key: str) -> Optional[str]:
    return CacheManager.get_cached_response(cache_key)


def cache_response(cache_key: str, response_chunks: List[str]):
    return CacheManager.cache_response(cache_key, response_chunks)


def get_cached_retrieval(cache_key: str) -> Optional[List[Document]]:
    return CacheManager.get_cached_retrieval(cache_key)


def cache_retrieval(cache_key: str, documents: List[Document]):
    return CacheManager.cache_retrieval(cache_key, documents)


async def stream_with_fallback(
    retrievers: Dict[str, BaseRetriever],
    chat_history: List[BaseMessage],
    user_input: str,
    preferred_model: Optional[str] = None,
    client_ip: Optional[str] = None,
    question: Optional[str] = None,
    request_id: Optional[str] = None,
    start_time: Optional[float] = None,
    tenant_id: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[AsyncIterator[str], str, Dict[str, Any]]:
    """
    Handle user input, perform retrieval (with caching),
    and stream a response from an LLM with fallback capabilities.
    """
    # Include tenant_id in cache key to prevent cross-tenant leakage
    cache_key = CacheManager.get_cache_key(
        user_input,
        chat_history=chat_history,
        model=AppConfig.get_claude_model(),
        additional_context={"tenant_id": tenant_id or "none"},
    )
    metadata = {"rate_limit_status": rate_limit_tracker.get_status()}

    # Merge additional metadata from routes
    if additional_metadata:
        metadata.update(additional_metadata)

    # 1) Cached FINAL response?
    if cache_key and (cached_response := CacheManager.get_cached_response(cache_key)):
        logger.debug(f"Cache hit: returning cached response for key: {cache_key}")

        async def cached_stream():
            # Log cached response with cache_hit=True BEFORE yielding
            if client_ip and question:
                try:
                    query_logger = get_query_logger()
                    # Merge cache-specific metadata with passed metadata
                    cache_metadata = {
                        "cache_hit": True,
                        "source_urls": [],
                        "source_titles": [],
                        "geo_info": None,
                        "tokens_used": 0,
                        "provider": "cached",
                    }
                    cache_metadata.update(metadata)

                    # Calculate actual response time from start_time if provided
                    actual_response_time = (time.time() - start_time) if start_time else 0.0

                    query_logger.log_query(
                        client_ip=client_ip,
                        question=question,
                        response=cached_response,
                        model_used="cached",
                        query_type="text",
                        response_time=actual_response_time,
                        metadata=cache_metadata,
                        request_id=request_id,
                    )
                except Exception as e:
                    logger.warning(f"Failed to log cached response: {e}")

            yield cached_response

        return cached_stream(), "cached", metadata
    else:
        logger.debug(f"Cache miss for key: {cache_key}. Will generate new response.")

    # 2) Initialize LLMs
    try:
        llms = get_llm_instances()
    except RuntimeError as e:
        logger.error(f"Fatal error initializing LLM instances: {e}")

        async def error_stream():
            yield "I'm sorry, the AI service is temporarily unavailable. Please contact support."

        return error_stream(), "error", {"rate_limit_status": {}}

    # 3) Cached RETRIEVAL?
    unique_docs = CacheManager.get_cached_retrieval(cache_key) if cache_key else None
    if unique_docs is None:
        logger.info(f"Retrieval cache miss for key: {cache_key}. Performing vector search...")

        # Try async retrieval first for better performance
        try:
            all_docs = await async_retrieve_documents(user_input, retrievers, tenant_id)
            logger.info(f"Async retrieval completed, got {len(all_docs)} documents (tenant_id={tenant_id})")
        except Exception as async_error:
            logger.warning(f"Async retrieval failed: {async_error}. Falling back to standard retrieval...")
            all_docs = []

        # Check if async retrieval returned documents
        if not all_docs:
            if "async_error" not in locals():
                logger.warning(f"Async retrieval returned no documents for tenant {tenant_id}")

            # TENANT ISOLATION: If we have a tenant_id, ONLY use tenant-scoped retrieval
            # NEVER fall back to non-tenant retrieval as that could leak other tenants' data
            if tenant_id:
                from .unified_retriever import UnifiedRetriever

                unified_retriever = retrievers.get("_unified_retriever")
                if unified_retriever and isinstance(unified_retriever, UnifiedRetriever):
                    try:
                        # SECURITY: Tenant-scoped search with NO shared documents
                        all_docs = unified_retriever.semantic_search_for_tenant(user_input, tenant_id)
                        logger.info(f"Tenant-scoped sync retrieval returned {len(all_docs)} documents")
                    except Exception as e:
                        logger.error(f"Tenant-scoped sync retrieval failed: {e}")
                        all_docs = []
                else:
                    logger.error("UnifiedRetriever not available - cannot perform tenant-scoped search")
                    all_docs = []

                # SECURITY: Do NOT fall back to any non-tenant retrieval
                # Better to return no results than to leak another tenant's data
                if not all_docs:
                    logger.warning(f"No documents found for tenant {tenant_id} - will use empty context")

            else:
                # Only use standard (non-tenant) retrieval when NO tenant context exists
                # This path should only be hit for legacy/default tenant scenarios
                selected_retrievers = route_query_to_retrievers(user_input, retrievers)

                if chat_history and (reformulation_llm := llms.get("claude") or llms.get("gemini")):
                    try:
                        history_prompt = create_history_aware_prompt()
                        history_aware_retrievers = [
                            create_history_aware_retriever(reformulation_llm, r, history_prompt)
                            for r in selected_retrievers
                        ]
                        tasks = [
                            r.ainvoke({"input": user_input, "chat_history": chat_history})
                            for r in history_aware_retrievers
                        ]
                        logger.info("Using history-aware retrievers.")
                    except Exception as e:
                        logger.warning(
                            f"Failed to create history-aware retrievers: {e}. Falling back to regular retrieval."
                        )
                        tasks = [r.ainvoke(user_input) for r in selected_retrievers]
                else:
                    tasks = [r.ainvoke(user_input) for r in selected_retrievers]

                if tasks:
                    retrieval_results = await asyncio.gather(*tasks, return_exceptions=True)
                    all_docs = []
                    for result in retrieval_results:
                        if isinstance(result, Exception):
                            logger.error(f"Error during document retrieval: {result}")
                        elif result:
                            all_docs.extend(cast(List[Document], result))
                else:
                    all_docs = []
                    logger.warning("No retrievers were selected for the query, context will be empty.")

        # Deduplicate by content + metadata
        unique_docs = list(
            {
                hashlib.sha256(
                    f"{doc.page_content}{json.dumps(doc.metadata, sort_keys=True)}".encode("utf-8")
                ).hexdigest(): doc
                for doc in all_docs
            }.values()
        )

        if cache_key:
            CacheManager.cache_retrieval(cache_key, unique_docs)

    # 4) Generation with smart model selection and fallback order
    llm_order = _determine_llm_order(preferred_model, llms, user_input)
    for llm_name, llm_instance in llm_order:
        if not llm_instance:
            continue
        try:
            logger.info(f"Attempting to stream response using {llm_name.title()}...")
            qa_chain = create_qa_chain(llm_instance)

            # Create true progressive streaming with background caching
            logger.debug(f"Starting progressive streaming for cache key: {cache_key}")

            async def progressive_streaming_with_caching(qa=qa_chain, model_name=llm_name):
                full_response_chunks = []
                used_model_name = model_name
                try:
                    # Stream LLM response in real-time while collecting for cache
                    async for chunk in qa.astream({"input": user_input, "context": unique_docs}):
                        # Coerce various chunk types to text for streaming and caching
                        if hasattr(chunk, "content"):
                            text_piece = getattr(chunk, "content", "")
                        elif isinstance(chunk, str):
                            text_piece = chunk
                        elif isinstance(chunk, dict):
                            text_piece = str(chunk.get("answer") or chunk.get("output") or chunk.get("content") or "")
                        else:
                            text_piece = str(chunk)

                        if not isinstance(text_piece, str):
                            text_piece = str(text_piece)

                        if text_piece:
                            # Yield immediately for progressive streaming
                            yield text_piece
                            # Collect for caching
                            full_response_chunks.append(text_piece)

                except Exception as stream_err:
                    # If authentication fails for Anthropic, try env-key fallback then Gemini
                    if is_authentication_error(stream_err) and model_name in {"claude", "claude_haiku"}:
                        try:
                            env_key = os.getenv("ANTHROPIC_API_KEY")
                            if env_key:
                                fallback_model = (
                                    AppConfig.get_claude_model()
                                    if model_name == "claude"
                                    else "claude-3-haiku-20240307"
                                )
                                try:
                                    fallback_llm = ChatAnthropic(
                                        model=fallback_model, api_key=env_key, temperature=0.7, timeout=REQUEST_TIMEOUT
                                    )
                                    qa_env = create_qa_chain(fallback_llm)
                                    used_model_name = model_name  # same provider family
                                    async for chunk in qa_env.astream({"input": user_input, "context": unique_docs}):
                                        if hasattr(chunk, "content"):
                                            text_piece = getattr(chunk, "content", "")
                                        elif isinstance(chunk, str):
                                            text_piece = chunk
                                        elif isinstance(chunk, dict):
                                            text_piece = str(
                                                chunk.get("answer") or chunk.get("output") or chunk.get("content") or ""
                                            )
                                        else:
                                            text_piece = str(chunk)
                                        if text_piece:
                                            yield text_piece
                                            full_response_chunks.append(text_piece)
                                    return
                                except Exception:
                                    # proceed to gemini fallback
                                    pass

                            gem_llm = llms.get("gemini")
                            if gem_llm is not None:
                                qa_gem = create_qa_chain(gem_llm)
                                used_model_name = "gemini"
                                async for chunk in qa_gem.astream({"input": user_input, "context": unique_docs}):
                                    if hasattr(chunk, "content"):
                                        text_piece = getattr(chunk, "content", "")
                                    elif isinstance(chunk, str):
                                        text_piece = chunk
                                    elif isinstance(chunk, dict):
                                        text_piece = str(
                                            chunk.get("answer") or chunk.get("output") or chunk.get("content") or ""
                                        )
                                    else:
                                        text_piece = str(chunk)
                                    if text_piece:
                                        yield text_piece
                                        full_response_chunks.append(text_piece)
                                return
                        except Exception:
                            # Fall through to re-raise
                            pass

                    # Re-raise for non-auth errors or if fallbacks failed
                    raise

                finally:
                    # Background caching after streaming completes
                    if cache_key and full_response_chunks:
                        logger.debug(
                            f"Background caching for key: {cache_key} ({len(full_response_chunks)} chunks, "
                            f"total length: {len(''.join(full_response_chunks))})"
                        )
                        CacheManager.cache_response(cache_key, full_response_chunks)

                        # Update streaming response log with actual content
                        if client_ip and question:
                            try:
                                complete_response = "".join(full_response_chunks)
                                # Calculate actual response time from start_time if provided
                                actual_response_time = (time.time() - start_time) if start_time else 0.0

                                query_logger = get_query_logger()
                                query_logger.update_streaming_response(
                                    cache_key=cache_key,
                                    client_ip=client_ip,
                                    question=question,
                                    actual_response=complete_response,
                                    request_id=request_id,
                                    model_used=used_model_name,
                                    response_time=actual_response_time,
                                    metadata=metadata,
                                )
                            except Exception as e:
                                logger.warning(f"Failed to update streaming response log: {e}")
                    elif cache_key:
                        logger.debug(f"Not caching response for key {cache_key} - no chunks collected")

            logger.info(f"Successfully initialized progressive streaming with {llm_name.title()}.")
            metadata["rate_limit_status"] = rate_limit_tracker.get_status()
            return progressive_streaming_with_caching(), llm_name, metadata

        except Exception as e:
            logger.error(f"{llm_name.title()} streaming failed: {type(e).__name__} - {e}")
            if is_rate_limit_error(e):
                rate_limit_tracker.set_rate_limited(llm_name)
                logger.warning(f"Rate limit detected for {llm_name}, marking as rate limited")
                metadata["rate_limit_status"] = rate_limit_tracker.get_status()
            logger.info("Trying next available model.")

    # 5) If all fail
    logger.error("All LLM streaming attempts failed.")

    async def fallback_stream():
        yield "I'm sorry, but I'm currently experiencing technical difficulties and cannot provide a response."

    return fallback_stream(), "error", metadata


def _determine_llm_order(
    preferred_model: Optional[str],
    llms: Dict[str, Optional[Union[ChatGoogleGenerativeAI, ChatAnthropic]]],
    query: Optional[str] = None,
) -> List[Tuple[str, Union[ChatGoogleGenerativeAI, ChatAnthropic]]]:
    """Determine the order in which to try LLMs based on preference, query complexity, and availability."""
    provider_names = [str(p["name"]) for p in LLM_PROVIDERS]

    # Smart model selection based on query complexity
    if query and not preferred_model:
        optimal_model = select_optimal_model_for_query(query)
        if optimal_model in provider_names and llms.get(optimal_model):
            # Put optimal model first
            provider_names.insert(0, provider_names.pop(provider_names.index(optimal_model)))
    elif preferred_model and preferred_model in provider_names and llms.get(preferred_model):
        # User preference overrides smart selection
        provider_names.insert(0, provider_names.pop(provider_names.index(preferred_model)))

    llm_order: List[Tuple[str, Union[ChatGoogleGenerativeAI, ChatAnthropic]]] = []
    for name in provider_names:
        instance = llms.get(name)
        if instance is not None:
            llm_order.append((name, instance))
    return llm_order


def get_rate_limit_status() -> Dict[str, bool]:
    """Get current rate limit status for all providers"""
    return rate_limit_tracker.get_status()
