"""
Response cache warmer for follow-up questions.

This module warms the response cache at startup by pre-generating
answers for common follow-up questions, ensuring instant responses
when users click them.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever

logger = logging.getLogger(__name__)


class ResponseCacheWarmer:
    """Warms the response cache with common follow-up questions."""

    def __init__(self):
        self.warmed_questions: List[str] = []
        self.warming_complete = False
        self.warming_in_progress = False
        self.successful_warmups = 0
        self.failed_warmups = 0

    async def warm_cache(
        self,
        questions: List[str],
        retrievers: Dict[str, BaseRetriever],
        app_state: Any,
    ) -> None:
        """
        Warm the cache with responses for the given questions.

        Args:
            questions: List of questions to pre-cache
            retrievers: Dictionary of retrievers for RAG
            app_state: FastAPI app state containing services
        """
        if self.warming_in_progress:
            logger.warning("Cache warming already in progress, skipping duplicate request")
            return

        if self.warming_complete:
            logger.info("Cache warming already complete, skipping")
            return

        if not questions:
            logger.info("No questions to warm cache with")
            self.warming_complete = True
            return

        # Skip cache warming in multi-tenant mode to prevent cross-tenant cache pollution
        import os

        if os.getenv("ENABLE_MULTI_TENANT", "false").lower() == "true":
            logger.info("Skipping cache warming in multi-tenant mode to prevent cross-tenant cache pollution")
            self.warming_complete = True
            return

        self.warming_in_progress = True
        logger.info(f"Starting cache warming for {len(questions)} questions...")

        try:
            from ..core.llm_chain import stream_with_fallback

            self.successful_warmups = 0
            self.failed_warmups = 0

            for i, question in enumerate(questions, 1):
                try:
                    logger.debug(f"Warming cache [{i}/{len(questions)}]: {question}")

                    # Create chat history with just the question
                    chat_history: List[BaseMessage] = [HumanMessage(content=question)]

                    # Call stream_with_fallback which will automatically cache the response
                    # Note: Cache warming only happens for default tenant (tenant_id="00000000...")
                    text_stream, _, _ = await stream_with_fallback(
                        retrievers,
                        chat_history,
                        question,
                        preferred_model=None,
                        tenant_id="00000000-0000-0000-0000-000000000000",  # Default tenant only
                    )

                    # Consume the stream to ensure caching happens
                    response_text = ""
                    async for chunk in text_stream:
                        response_text += chunk

                    if response_text:
                        self.successful_warmups += 1
                        self.warmed_questions.append(question)
                        logger.debug(f"Successfully cached response for: {question[:50]}...")
                    else:
                        self.failed_warmups += 1
                        logger.warning(f"Empty response for question: {question}")

                except Exception as e:
                    self.failed_warmups += 1
                    logger.error(f"Failed to warm cache for question '{question}': {e}", exc_info=True)

                # Small delay between questions to avoid overwhelming the LLM
                if i < len(questions):
                    await asyncio.sleep(0.5)

            self.warming_complete = True
            self.warming_in_progress = False
            logger.info(
                f"Cache warming complete: {self.successful_warmups} successful, "
                f"{self.failed_warmups} failed out of {len(questions)} total"
            )

        except Exception as e:
            logger.error(f"Cache warming failed: {e}", exc_info=True)
            self.warming_complete = True
            self.warming_in_progress = False

    def get_warmed_questions(self) -> List[str]:
        """Get the list of successfully warmed questions."""
        return self.warmed_questions.copy()

    def is_warming_complete(self) -> bool:
        """Check if cache warming is complete."""
        return self.warming_complete

    def reset_warming_state(self) -> None:
        """Reset the warming state to allow re-warming if needed."""
        if self.warming_in_progress:
            logger.warning("Cannot reset warming state while warming is in progress")
            return

        self.warming_complete = False
        self.warmed_questions.clear()
        self.successful_warmups = 0
        self.failed_warmups = 0
        logger.info("Cache warming state reset - ready for re-warming")

    def get_status(self) -> Dict[str, Any]:
        """Get the current cache warming status."""
        return {
            "warming_complete": self.warming_complete,
            "warming_in_progress": self.warming_in_progress,
            "successful_warmups": self.successful_warmups,
            "failed_warmups": self.failed_warmups,
            "warmed_count": len(self.warmed_questions),
            "warmed_questions": self.warmed_questions,
        }


# Global cache warmer instance
_cache_warmer: Optional[ResponseCacheWarmer] = None


def get_cache_warmer() -> ResponseCacheWarmer:
    """Get or create the global cache warmer instance."""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = ResponseCacheWarmer()
    return _cache_warmer


async def start_cache_warming(retrievers: Dict[str, BaseRetriever], app_state: Any) -> None:
    """
    Start cache warming in the background.

    This function starts cache warming and returns immediately,
    allowing the app to start serving requests while warming happens.
    """
    # Check response caching settings from DB
    try:
        from ..core.settings_manager import get_settings_manager

        sm = get_settings_manager()
        rs = sm.get_response_settings()
        # Require both global caching and response caching to be enabled
        if not getattr(rs, "enable_caching", True) or not getattr(rs, "enable_response_caching", True):
            logger.info("Follow-up response caching is disabled by settings")
            return
    except Exception as e:
        logger.warning(f"Could not read response caching settings, skipping cache warming: {e}")
        return

    # Get the follow-up service to extract general questions
    followup_service = app_state.followup_service
    if not followup_service:
        logger.warning("No follow-up service available for cache warming")
        return

    # Get the static questions (all 6 questions) - convert tuple to list for processing
    questions_to_warm = list(followup_service.default_questions)

    if not questions_to_warm:
        logger.info("No general follow-up questions found for cache warming")
        return

    # Get or create cache warmer
    warmer = get_cache_warmer()

    # Start warming in the background
    logger.info(f"Starting background cache warming for {len(questions_to_warm)} general questions")
    asyncio.create_task(warmer.warm_cache(questions_to_warm, retrievers, app_state))
