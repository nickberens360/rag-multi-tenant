"""
Startup-time content classification using LLM for high accuracy.

This module performs LLM-based content classification during indexing/startup
instead of query time, providing better accuracy than hardcoded patterns
while still achieving significant performance gains.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel

from .llm_utils import extract_topics_with_llm
from .taxonomy_loader import get_topic_taxonomy

logger = logging.getLogger(__name__)


class StartupContentClassifier:
    """High-accuracy content classification using LLM at startup/indexing time."""

    def __init__(self, llm: BaseLanguageModel):
        """Initialize with LLM for content analysis."""
        self.llm = llm
        self._classification_cache: Dict[str, Dict[str, Any]] = {}

    def classify_content_with_llm(self, doc: Document, file_path: Path) -> Dict[str, Any]:
        """
        Perform high-accuracy content classification using LLM.

        This runs during indexing/startup, not during queries, so the LLM overhead
        is acceptable for the improved accuracy and domain flexibility.
        """
        content = doc.page_content

        # Check cache first (based on content hash)
        content_hash = str(hash(content))
        if content_hash in self._classification_cache:
            logger.debug(f"Using cached classification for {file_path.name}")
            return self._classification_cache[content_hash]

        # Use LLM for dynamic, accurate topic extraction
        llm_topics = extract_topics_with_llm(self.llm, content)

        # Enhance with file-based heuristics for completeness
        heuristic_topics = self._extract_heuristic_topics(content, file_path)

        # Merge and deduplicate topics
        all_topics = self._merge_topics(llm_topics, heuristic_topics)

        # Extract enhanced keywords using LLM-informed approach
        keywords = self._extract_enhanced_keywords(content, all_topics)

        # Calculate confidence based on LLM+heuristic agreement
        confidence = self._calculate_llm_confidence(llm_topics, heuristic_topics, content, file_path)

        # Handle special file types
        special_metadata = self._handle_special_files(doc, file_path)

        # Build comprehensive metadata
        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": ",".join(all_topics),
            "content_types": ",".join(all_topics),  # Legacy compatibility
            "content_length": len(content),
            "has_code": self._detect_code_content(content),
            "content_keywords": keywords,
            "topic_confidence": confidence,
            "classification_method": "startup_llm",
            "llm_topics": ",".join(llm_topics) if llm_topics else "",
            "heuristic_topics": ",".join(heuristic_topics) if heuristic_topics else "",
            **special_metadata,
        }

        # Cache the result
        self._classification_cache[content_hash] = metadata

        logger.info(f"LLM classified {file_path.name}: topics={all_topics}, confidence={confidence:.2f}")

        return metadata

    def _extract_heuristic_topics(self, content: str, file_path: Path) -> List[str]:
        """Extract topics using taxonomy-driven heuristics (fallback to hardcoded)."""
        content_lower = content.lower()
        file_name_lower = file_path.name.lower()
        detected_topics = set()

        taxonomy = get_topic_taxonomy()
        if taxonomy and isinstance(taxonomy.get("categories"), dict):
            for topic, cfg in taxonomy["categories"].items():
                # Build effective patterns from synonyms and explicit regex overrides
                patterns: list[re.Pattern] = []
                synonyms = [s for s in (cfg.get("synonyms") or []) if isinstance(s, str) and s.strip()]
                if synonyms:
                    try:
                        escaped = [re.escape(s.strip()) for s in synonyms]
                        syn_pattern = re.compile(r"\\b(?:" + "|".join(escaped) + r")\\b", re.IGNORECASE)
                        patterns.append(syn_pattern)
                    except re.error:
                        for s in synonyms:
                            try:
                                patterns.append(re.compile(r"\\b" + re.escape(s.strip()) + r"\\b", re.IGNORECASE))
                            except re.error:
                                continue

                for raw in cfg.get("regex") or []:
                    if not isinstance(raw, str):
                        continue
                    try:
                        patterns.append(re.compile(raw, re.IGNORECASE))
                    except re.error:
                        continue

                # Apply patterns to file name and content
                try:
                    if any(pat.search(file_name_lower) for pat in patterns) or any(
                        pat.search(content_lower) for pat in patterns
                    ):
                        detected_topics.add(topic)
                        continue
                except re.error:
                    pass

        # Fallback heuristics to preserve behavior
        if not detected_topics:
            # File name based hints
            file_hints = {
                "about": ["about", "bio", "personal", "profile", "readme"],
                "experience": ["resume", "cv", "work", "career", "employment", "experience"],
                "skills": ["skills", "technologies", "expertise", "competencies", "stack"],
                "creative": ["illustration", "art", "design", "gallery", "portfolio", "creative"],
                "project": ["project", "projects", "development", "portfolio", "work"],
            }

            for topic, hints in file_hints.items():
                if any(hint in file_name_lower for hint in hints):
                    detected_topics.add(topic)

            # Content-based detection (more conservative than fast classifier)
            if any(word in content_lower for word in ["experience", "worked", "employment", "company", "role"]):
                detected_topics.add("experience")

            if any(word in content_lower for word in ["skill", "technology", "programming", "proficient"]):
                detected_topics.add("skills")

            if any(word in content_lower for word in ["about", "background", "philosophy", "passion"]):
                detected_topics.add("about")

            if any(word in content_lower for word in ["illustration", "art", "design", "creative"]):
                detected_topics.add("creative")

            if any(word in content_lower for word in ["project", "built", "developed", "created"]):
                detected_topics.add("project")

        # Always apply a light content-based skills detection to complement taxonomy matches
        if any(word in content_lower for word in ["skill", "technology", "programming", "proficient"]):
            detected_topics.add("skills")

        if self._detect_code_content(content):
            detected_topics.add("technical")

        return list(detected_topics) if detected_topics else ["general"]

    def _merge_topics(self, llm_topics: List[str], heuristic_topics: List[str]) -> List[str]:
        """Merge LLM and heuristic topics, prioritizing LLM accuracy."""
        # Start with LLM topics (higher quality)
        merged = set(llm_topics) if llm_topics else set()

        # Add heuristic topics that don't conflict
        for topic in heuristic_topics:
            if topic not in merged:
                merged.add(topic)

        # Ensure we have at least one topic
        if not merged:
            merged = {"general"}
        else:
            # If we have specific topics, drop overly-generic label
            if "general" in merged and len(merged) > 1:
                merged.discard("general")

        # Convert to sorted list for consistency
        return sorted(list(merged))

    def _extract_enhanced_keywords(self, content: str, topics: List[str]) -> str:
        """Extract keywords with topic-aware enhancement."""
        content_lower = content.lower()
        keywords = set()

        # Extract technical terms and proper nouns
        technical_terms = re.findall(r"\b[A-Z][a-z]*(?:[A-Z][a-z]*)*\b", content)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", content)
        keywords.update(technical_terms)
        keywords.update(acronyms)

        # Topic-specific keyword extraction (taxonomy-driven if available)
        taxonomy = get_topic_taxonomy()
        if taxonomy and isinstance(taxonomy.get("categories"), dict):
            topic_keywords: Dict[str, List[str]] = {}
            for topic, cfg in taxonomy["categories"].items():
                syn = [s.lower() for s in (cfg.get("synonyms") or []) if isinstance(s, str)]
                extra = [s.lower() for s in (cfg.get("keywords") or []) if isinstance(s, str)]
                topic_keywords[topic] = list({*syn, *extra})
        else:
            topic_keywords = {
                "skills": ["javascript", "python", "react", "vue", "node", "typescript", "css", "html"],
                "experience": ["company", "role", "position", "manager", "director", "lead"],
                "creative": ["illustration", "art", "design", "portfolio", "gallery"],
                "project": ["built", "created", "developed", "github", "repository"],
                "technical": ["code", "programming", "software", "api", "database"],
            }

        for topic in topics:
            if topic in topic_keywords:
                for keyword in topic_keywords[topic]:
                    if keyword in content_lower:
                        keywords.add(keyword)

        # Frequency-based keyword extraction
        words = re.findall(r"\b[a-z]+\b", content_lower)
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) >= 4:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1

        # Add frequent meaningful words
        stop_words = {"that", "this", "with", "from", "they", "were", "been", "have", "will", "would", "could"}
        frequent_words = [word for word, freq in word_freq.items() if freq >= 2 and word not in stop_words]
        keywords.update(frequent_words[:10])  # Top 10 frequent words

        return ",".join(sorted(list(keywords)))

    def _calculate_llm_confidence(
        self, llm_topics: List[str], heuristic_topics: List[str], content: str, file_path: Path
    ) -> float:
        """Calculate confidence based on LLM and heuristic agreement."""
        base_confidence = 0.8  # Higher base confidence for LLM classification

        # Boost confidence when LLM and heuristics agree
        if llm_topics and heuristic_topics:
            overlap = set(llm_topics) & set(heuristic_topics)
            agreement_ratio = len(overlap) / max(len(llm_topics), len(heuristic_topics))
            base_confidence += agreement_ratio * 0.15

        # Boost confidence for file name alignment
        file_name_lower = file_path.name.lower()
        for topic in llm_topics:
            if topic in file_name_lower or any(hint in file_name_lower for hint in [topic, f"{topic}s"]):
                base_confidence += 0.05

        return min(base_confidence, 1.0)  # Cap at 1.0

    def _detect_code_content(self, content: str) -> bool:
        """Detect if content contains code."""
        code_indicators = [
            "```",  # Code blocks
            "function ",
            "def ",
            "class ",
            "const ",
            "let ",
            "var ",  # Programming keywords
            "import ",
            "from ",
            "require(",
            "#include",  # Import statements
            "public class",
            "private ",
            "protected ",  # OOP keywords
        ]

        content_lower = content.lower()
        return any(indicator.lower() in content_lower for indicator in code_indicators)

    def _handle_special_files(self, doc: Document, file_path: Path) -> Dict[str, Any]:
        """Handle special file types with specific processing."""
        special_metadata = {}

        # Handle illustration JSON files
        if file_path.name == "illustrations.json":
            special_metadata["is_illustration_data"] = True
            try:
                if '"file"' in doc.page_content:
                    data = json.loads(doc.page_content)
                    if isinstance(data, dict) and "file" in data:
                        illustration_file = data.get("file")
                        special_metadata["illustration_file"] = illustration_file
                        special_metadata["display_path"] = f"/illustrations/{illustration_file}"
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON content in {file_path}")
        else:
            special_metadata["is_illustration_data"] = False

        return special_metadata

    def batch_classify_content(self, documents_with_paths: List[Tuple[Document, Path]]) -> List[Dict[str, Any]]:
        """
        Classify multiple documents in batch for efficient startup processing.

        This method can be optimized for batch LLM calls if the LLM provider supports it.
        """
        results = []

        logger.info(f"Starting batch classification of {len(documents_with_paths)} documents")

        for i, (doc, file_path) in enumerate(documents_with_paths):
            try:
                metadata = self.classify_content_with_llm(doc, file_path)
                results.append(metadata)

                # Log progress for long operations
                if (i + 1) % 10 == 0:
                    logger.info(f"Classified {i + 1}/{len(documents_with_paths)} documents")

            except Exception as e:
                logger.error(f"Failed to classify {file_path}: {e}")
                # Provide fallback metadata
                fallback_metadata = {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_type": file_path.suffix.lower(),
                    "content_type": "general",
                    "content_types": "general",
                    "content_length": len(doc.page_content),
                    "has_code": False,
                    "content_keywords": "",
                    "topic_confidence": 0.3,
                    "classification_method": "fallback",
                    "is_illustration_data": file_path.name == "illustrations.json",
                }
                results.append(fallback_metadata)

        logger.info(f"Completed batch classification: {len(results)} documents processed")

        return results

    def get_classification_stats(self) -> Dict[str, Any]:
        """Get statistics about the classification process."""
        if not self._classification_cache:
            return {"status": "no_classifications"}

        topics_count: Dict[str, int] = {}
        confidence_scores = []
        methods_count: Dict[str, int] = {}

        for metadata in self._classification_cache.values():
            # Count topics
            topics = metadata.get("content_type", "").split(",")
            for topic in topics:
                if topic:
                    topics_count[topic] = topics_count.get(topic, 0) + 1

            # Track confidence scores
            confidence_scores.append(metadata.get("topic_confidence", 0))

            # Count methods
            method = metadata.get("classification_method", "unknown")
            methods_count[method] = methods_count.get(method, 0) + 1

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            "total_classified": len(self._classification_cache),
            "topics_distribution": topics_count,
            "average_confidence": avg_confidence,
            "methods_used": methods_count,
            "high_confidence_ratio": (
                len([c for c in confidence_scores if c > 0.8]) / len(confidence_scores) if confidence_scores else 0
            ),
        }
