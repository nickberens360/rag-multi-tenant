"""
Filter models for metadata-aware retrieval.

This module defines the filter specifications for smart retrieval that distinguishes
between manual (authoritative) and inferred (soft signal) metadata.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MetadataFilter:
    """
    Represents a metadata filter with strict/soft semantics.

    Attributes:
        field: The metadata field to filter on (e.g., 'effective_content_type', 'effective_tags')
        value: The value to match (e.g., 'technical', 'python')
        strict: If True, apply hard filter (exclude non-matches). If False, use as soft signal for reranking.
        boost_weight: Weight for soft reranking (only used when strict=False)
    """

    field: str
    value: str
    strict: bool = False
    boost_weight: float = 0.2  # Default boost for soft matches


@dataclass
class RetrievalFilters:
    """
    Container for all filters to apply during retrieval.

    Attributes:
        content_type: Content type filter (e.g., 'technical', 'experience')
        tags: List of tag filters
        strict_mode: Default strict mode if individual filters don't specify
    """

    content_type: Optional[MetadataFilter] = None
    tags: List[MetadataFilter] = None
    strict_mode: bool = False  # Default to soft reranking

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def get_strict_filters(self) -> List[MetadataFilter]:
        """Get all filters that should be applied as strict (hard) filters."""
        strict = []
        if self.content_type and self.content_type.strict:
            strict.append(self.content_type)
        strict.extend([f for f in self.tags if f.strict])
        return strict

    def get_soft_filters(self) -> List[MetadataFilter]:
        """Get all filters that should be applied as soft (reranking) signals."""
        soft = []
        if self.content_type and not self.content_type.strict:
            soft.append(self.content_type)
        soft.extend([f for f in self.tags if not f.strict])
        return soft

    def has_filters(self) -> bool:
        """Check if any filters are configured."""
        return self.content_type is not None or len(self.tags) > 0


def parse_filter_string(filter_str: str, default_strict: bool = False) -> Optional[MetadataFilter]:
    """
    Parse a filter string into a MetadataFilter.

    Supported formats:
    - 'content_type:technical' -> soft filter for content_type=technical
    - 'content_type:technical:strict' -> strict filter for content_type=technical
    - 'tags:python' -> soft filter for tags containing 'python'
    - 'tags:python:strict' -> strict filter for tags containing 'python'

    Args:
        filter_str: Filter string to parse
        default_strict: Default strict mode if not specified in filter string

    Returns:
        MetadataFilter if parsing succeeds, None otherwise
    """
    if not filter_str or ":" not in filter_str:
        return None

    parts = filter_str.split(":")
    if len(parts) < 2:
        return None

    field_map = {"content_type": "effective_content_type", "tags": "effective_tags"}

    field_name = parts[0].strip()
    value = parts[1].strip()

    # Check for :strict suffix
    strict = default_strict
    if len(parts) >= 3 and parts[2].strip().lower() == "strict":
        strict = True

    # Map to effective field names
    effective_field = field_map.get(field_name)
    if not effective_field:
        return None

    return MetadataFilter(field=effective_field, value=value, strict=strict)


def parse_filter_strings(filter_strs: List[str], default_strict: bool = False) -> RetrievalFilters:
    """
    Parse multiple filter strings into a RetrievalFilters object.

    Args:
        filter_strs: List of filter strings
        default_strict: Default strict mode for filters

    Returns:
        RetrievalFilters object with parsed filters
    """
    filters = RetrievalFilters(strict_mode=default_strict)

    for filter_str in filter_strs:
        parsed = parse_filter_string(filter_str, default_strict)
        if not parsed:
            continue

        if parsed.field == "effective_content_type":
            filters.content_type = parsed
        elif parsed.field == "effective_tags":
            filters.tags.append(parsed)

    return filters
