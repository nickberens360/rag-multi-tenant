"""
Security validation module for input sanitization and security checks.

This module contains the SecurityValidator class that handles:
- Query validation and sanitization
- Detection of suspicious patterns and injection attempts
- Input length validation
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class SecurityValidator:
    MAX_QUERY_LENGTH: int = 1000
    MAX_CHAT_HISTORY_LENGTH: int = 10
    MAX_MESSAGE_LENGTH: int = 1000
    SUSPICIOUS_PATTERNS: List[str] = [
        r"ignore\s+(?:all\s+)?(previous|above)\s+instructions?",
        r"ignore\s+all\s+previous\s+instructions?",
        r"system\s*:?\s*you\s+are\s+now",
        r"forget\s+everything\s+(above|before)",
        r"new\s+instructions?\s*:",
        r"</?\s*(script|iframe|object|embed|form)",
        r"javascript\s*:",
        r"data\s*:\s*text/html",
        r"(prompt|system)\s+(injection|hack|override)",
        # Made these patterns more specific to avoid blocking legitimate content
        r"act\s+as\s+if\s+you\s+are\s+(a\s+)?(different|another|new|chatgpt)",
        r"pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another|new)",
    ]
    ALLOWED_MODELS: List[Optional[str]] = ["claude", "claude_haiku", "gemini", None]

    @classmethod
    def validate_query(cls, query, client_ip: str) -> tuple[bool, str]:
        try:
            if not query.question or not isinstance(query.question, str):
                return False, "Question is required and must be text"
            if len(query.question) > cls.MAX_QUERY_LENGTH:
                return (
                    False,
                    f"Question too long (max {cls.MAX_QUERY_LENGTH} characters)",
                )
            if query.chat_history:
                if len(query.chat_history) > cls.MAX_CHAT_HISTORY_LENGTH:
                    return (
                        False,
                        f"Chat history too long (max {cls.MAX_CHAT_HISTORY_LENGTH} messages)",
                    )
                for i, msg in enumerate(query.chat_history):
                    if not isinstance(msg.text, str) or len(msg.text) > cls.MAX_MESSAGE_LENGTH:
                        return (
                            False,
                            f"Message {i + 1} invalid or too long (max {cls.MAX_MESSAGE_LENGTH} characters)",
                        )
            if query.preferred_model and query.preferred_model not in cls.ALLOWED_MODELS:
                return False, "Invalid model preference"

            combined_text = query.question.lower()
            if query.chat_history:
                combined_text += " " + " ".join([msg.text.lower() for msg in query.chat_history])
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected from {client_ip}: {pattern}")
                    return False, "Content not allowed"

            return True, ""
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return False, "Validation error"

    @classmethod
    def sanitize_input(cls, text: Optional[str]) -> str:
        if not isinstance(text, str):
            return ""
        # Remove control characters except for common whitespace
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Normalize whitespace and limit length
        return re.sub(r"\s+", " ", sanitized).strip()[: cls.MAX_QUERY_LENGTH]
