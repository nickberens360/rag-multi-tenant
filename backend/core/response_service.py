import logging
import time
from typing import Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Error message templates
ERROR_NO_MATCHING_IMAGES = (
    "Sorry, I couldn't find any illustrations matching '{search_term}'. You can ask to see all of my art."
)


class QueryResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    answer: str
    images: Optional[List[str]] = None
    followup_questions: Optional[List[str]] = None
    processing_time: Optional[float] = None
    llm_used: Optional[str] = None  # Keep for backward compatibility
    model_used: Optional[str] = None  # New field for frontend
    rate_limits: Optional[Dict[str, bool]] = None  # New field for rate limit status


class ResponseService:
    """Service for building consistent API responses."""

    def __init__(self, base_image_url: str = "/illustrations/"):
        self.base_image_url = base_image_url

    def build_image_response(
        self,
        search_term: str,
        found_images: List[Dict[str, str]],
        start_time: float,
        followup_questions: Optional[List[str]] = None,
        success_message_template: str = "Here are the illustrations I found for '{}':",
        model_used: str = "image_search",
        rate_limits: Optional[Dict[str, bool]] = None,
    ) -> QueryResponse:
        """Build a response for successful image searches."""
        if found_images:
            # Handle cases where img['file'] might already contain the base path
            image_urls = []
            for img in found_images:
                file_path = img["file"]
                # Remove any existing "/illustrations/" prefix to avoid double slashes
                if file_path.startswith("/illustrations/"):
                    file_path = file_path[len("/illustrations/") :]
                elif file_path.startswith("illustrations/"):
                    file_path = file_path[len("illustrations/") :]
                image_urls.append(f"{self.base_image_url}{file_path}")
            processing_time = time.time() - start_time

            # Customize message based on search term
            if search_term == "all":
                answer = "Of course! Here are some of my illustrations:"
            else:
                answer = success_message_template.format(search_term)

            logger.info(f"Image search completed in {processing_time:.3f}s")
            return QueryResponse(
                answer=answer,
                images=image_urls,
                followup_questions=followup_questions,
                processing_time=processing_time,
                llm_used="image_search",
                model_used=model_used,
                rate_limits=rate_limits,
            )
        else:
            processing_time = time.time() - start_time
            return QueryResponse(
                answer=ERROR_NO_MATCHING_IMAGES.format(search_term=search_term),
                followup_questions=followup_questions,
                processing_time=processing_time,
                llm_used="image_search",
                model_used=model_used,
                rate_limits=rate_limits,
            )

    def build_no_images_response(
        self,
        start_time: float,
        followup_questions: Optional[List[str]] = None,
        model_used: str = "image_search",
        rate_limits: Optional[Dict[str, bool]] = None,
    ) -> QueryResponse:
        """Build a response when no images are available."""
        processing_time = time.time() - start_time
        return QueryResponse(
            answer="I couldn't find any illustrations at the moment.",
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used="image_search",
            model_used=model_used,
            rate_limits=rate_limits,
        )

    def build_ai_response(
        self,
        answer: str,
        start_time: float,
        llm_used: str,
        followup_questions: Optional[List[str]] = None,
        model_used: Optional[str] = None,
        rate_limits: Optional[Dict[str, bool]] = None,
    ) -> QueryResponse:
        """Build a response for AI-generated text."""
        processing_time = time.time() - start_time
        logger.info(f"Query processed successfully in {processing_time:.3f}s using {llm_used}")

        return QueryResponse(
            answer=answer,
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used=llm_used,
            model_used=model_used or llm_used,  # Use model_used if provided, fallback to llm_used
            rate_limits=rate_limits,
        )

    def build_error_response(
        self,
        error_message: str,
        start_time: float,
        llm_used: str = "fallback",
        followup_questions: Optional[List[str]] = None,
        model_used: Optional[str] = None,
        rate_limits: Optional[Dict[str, bool]] = None,
    ) -> QueryResponse:
        """Build a response for errors."""
        processing_time = time.time() - start_time

        return QueryResponse(
            answer=error_message,
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used=llm_used,
            model_used=model_used or llm_used,  # Use model_used if provided, fallback to llm_used
            rate_limits=rate_limits,
        )

    def process_response_formatting(self, response: str, sources: Optional[List[Dict[str, str]]] = None) -> str:
        """Apply formatting based on admin settings."""
        try:
            from .settings_manager import get_settings_manager

            settings_manager = get_settings_manager()
            response_settings = settings_manager.get_response_settings()

            # Apply response formatting
            formatted_response = response

            # Handle markdown settings
            if not response_settings.enable_markdown:
                formatted_response = self._strip_markdown(formatted_response)

            # Handle code highlighting settings
            if not response_settings.enable_code_highlighting:
                formatted_response = self._strip_code_highlighting(formatted_response)

            # Add sources if enabled
            if response_settings.include_sources and sources:
                source_section = self._format_sources(sources, response_settings)
                if source_section:
                    formatted_response += f"\n\n{source_section}"

            return formatted_response

        except Exception as e:
            logger.warning(f"Failed to apply response formatting: {e}")
            return response  # Return original response on error

    def _format_sources(self, sources: List[Dict[str, str]], response_settings) -> str:
        """Format sources based on admin settings."""
        if not sources:
            return ""

        # Limit source count
        limited_sources = sources[: response_settings.max_sources]

        # Format based on preference
        if response_settings.source_format == "numbered":
            return self._format_numbered_sources(limited_sources)
        elif response_settings.source_format == "bulleted":
            return self._format_bulleted_sources(limited_sources)
        elif response_settings.source_format == "inline":
            return self._format_inline_sources(limited_sources)
        else:
            return self._format_numbered_sources(limited_sources)  # Default

    def _format_numbered_sources(self, sources: List[Dict[str, str]]) -> str:
        """Format sources as numbered list."""
        if not sources:
            return ""

        source_lines = ["**Sources:**"]
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Unknown Source")
            file_path = source.get("file", "")
            source_lines.append(f"{i}. {title} ({file_path})")

        return "\n".join(source_lines)

    def _format_bulleted_sources(self, sources: List[Dict[str, str]]) -> str:
        """Format sources as bulleted list."""
        if not sources:
            return ""

        source_lines = ["**Sources:**"]
        for source in sources:
            title = source.get("title", "Unknown Source")
            file_path = source.get("file", "")
            source_lines.append(f"• {title} ({file_path})")

        return "\n".join(source_lines)

    def _format_inline_sources(self, sources: List[Dict[str, str]]) -> str:
        """Format sources inline."""
        if not sources:
            return ""

        source_names = [s.get("title", "Unknown") for s in sources]
        return f"\n\n*Sources: {', '.join(source_names)}*"

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting for plain text output."""
        import re

        # Remove headers
        text = re.sub(r"^#{1,6}\s+(.+)$", r"\1", text, flags=re.MULTILINE)

        # Remove bold/italic
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)

        # Remove links
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "[Code Block]", text)
        text = re.sub(r"`(.+?)`", r"\1", text)

        return text

    def _strip_code_highlighting(self, text: str) -> str:
        """Remove code highlighting while keeping code blocks."""
        import re

        # Convert highlighted code blocks to plain code blocks
        text = re.sub(r"```\w+\n([\s\S]*?)```", r"```\n\1```", text)

        return text
