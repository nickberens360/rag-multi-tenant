"""
Request models for the FastAPI application.

This module contains Pydantic models for validating incoming requests:
- Message: Individual chat message with sender and text
- Query: Main query request with question, chat history, and model preference
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..security.validator import SecurityValidator


class Message(BaseModel):
    sender: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The sender of the message (user or assistant)",
        examples=["user", "assistant"],
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=SecurityValidator.MAX_MESSAGE_LENGTH,
        description="The message content",
        examples=[
            "What technologies do you specialize in?",
            "I specialize in full-stack development with Vue.js, Python, and modern web technologies.",
        ],
    )


class Query(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=SecurityValidator.MAX_QUERY_LENGTH,
        description="The user's question or request about the organization's experience, skills, projects, or content",
        examples=[
            "What is the professional background?",
            "Tell me about experience with Vue.js and Python",
            "What projects have been completed recently?",
            "What technologies are used for backend development?",
            "Can you show me some creative work?",
            "What services does the organization offer?",
        ],
    )
    chat_history: List[Message] = Field(
        default=[],
        max_length=SecurityValidator.MAX_CHAT_HISTORY_LENGTH,
        description="Previous conversation history for context. Optional - leave empty for new conversations.",
        examples=[
            [],
            [
                {"sender": "user", "text": "What technologies do you use?"},
                {
                    "sender": "assistant",
                    "text": "I primarily work with Vue.js for frontend, Python/FastAPI for backend, and modern deployment tools.",
                },
            ],
        ],
    )
    preferred_model: Optional[str] = Field(
        default=None,
        description="User's preferred AI model (claude or gemini). Leave empty for automatic selection.",
        examples=["claude", "gemini", None],
    )
    metadata_filters: Optional[List[str]] = Field(
        default=None,
        description=(
            "Optional metadata filters for retrieval. Format: 'field:value' or 'field:value:strict'. "
            "Examples: ['content_type:technical'], ['tags:python:strict'], ['content_type:experience', 'tags:vue']"
        ),
        examples=[
            ["content_type:technical"],
            ["tags:python:strict"],
            ["content_type:experience", "tags:vue"],
            None,
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What is the background in software engineering?",
                    "chat_history": [],
                    "preferred_model": None,
                },
                {
                    "question": "Can you show me some recent projects?",
                    "chat_history": [],
                    "preferred_model": "claude",
                },
                {
                    "question": "Tell me more about the technologies mentioned",
                    "chat_history": [
                        {"sender": "user", "text": "What technologies are used?"},
                        {
                            "sender": "assistant",
                            "text": "The stack includes Vue.js, Python/FastAPI, and modern deployment tools.",
                        },
                    ],
                    "preferred_model": "claude",
                },
            ]
        }
    }
