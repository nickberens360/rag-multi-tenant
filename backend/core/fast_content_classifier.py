"""
Fast content classification without LLM calls for performance optimization.

This module replaces LLM-based content analysis with lightning-fast pattern matching
and heuristic classification, reducing query time from seconds to milliseconds.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from langchain.docstore.document import Document

logger = logging.getLogger(__name__)


class FastContentClassifier:
    """Lightning-fast content classification using patterns and keywords."""

    def __init__(self):
        """Initialize classifier with taxonomy-first configuration and safe fallbacks."""

        from .taxonomy_loader import get_topic_taxonomy

        tax = get_topic_taxonomy()
        if tax and isinstance(tax.get("categories"), dict):
            self._init_from_taxonomy(tax)
        else:
            self._init_default_tables()

    def extract_content_topics_fast(self, content: str, file_path: Path) -> List[str]:
        """Extract topics from content using fast keyword matching (no LLM)."""
        content_lower = content.lower()
        file_name_lower = file_path.name.lower()

        detected_topics = set()

        # File name hints (highest priority)
        for topic, hints in self.file_topic_hints.items():
            if any(hint in file_name_lower for hint in hints):
                detected_topics.add(topic)

        # Special file handling
        if file_path.name == "illustrations.json":
            detected_topics.add("creative")

        # Content keyword matching
        for topic, keywords in self.content_keywords.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in content_lower)
            # If significant keyword density, add topic
            if keyword_matches >= 2 or (keyword_matches >= 1 and len(keywords) <= 3):
                detected_topics.add(topic)

        # Pattern matching for additional context
        for topic, patterns in self.topic_patterns.items():
            pattern_matches = sum(len(re.findall(pattern, content_lower)) for pattern in patterns)
            if pattern_matches >= 2:  # Multiple pattern matches indicate strong topic relevance
                detected_topics.add(topic)

        # Convert to sorted list (most likely topics first)
        topics = list(detected_topics)
        if not topics:
            topics = ["general"]

        return topics

    def extract_content_keywords_fast(self, content: str) -> str:
        """Extract keywords using fast regex/NLP without LLM."""
        content_lower = content.lower()

        # Extract technical terms, proper nouns, and key phrases
        technical_terms = re.findall(r"\b[A-Z][a-z]*(?:[A-Z][a-z]*)*\b", content)  # CamelCase
        acronyms = re.findall(r"\b[A-Z]{2,}\b", content)  # Acronyms

        # Extract words that appear frequently and are likely keywords
        words = re.findall(r"\b[a-z]+\b", content_lower)
        word_freq: Dict[str, int] = {}
        for word in words:
            if len(word) >= 4:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get most frequent meaningful words
        frequent_words = [
            word
            for word, freq in word_freq.items()
            if freq >= 2
            and word not in {"that", "this", "with", "from", "they", "were", "been", "have", "will", "would", "could"}
        ]

        # Combine all keywords
        all_keywords = technical_terms + acronyms + frequent_words[:10]  # Limit to top 10

        return ",".join(set(all_keywords))

    def calculate_topic_confidence(self, topics: List[str], content: str, file_path: Path) -> float:
        """Calculate confidence score for topic classification."""
        if not topics or topics == ["general"]:
            return 0.3  # Low confidence for general classification

        confidence = 0.5  # Base confidence

        # Boost confidence based on file name matches
        file_name_lower = file_path.name.lower()
        for topic in topics:
            if topic in self.file_topic_hints:
                if any(hint in file_name_lower for hint in self.file_topic_hints[topic]):
                    confidence += 0.2

        # Boost confidence based on keyword density
        content_lower = content.lower()
        total_keywords = 0
        matching_keywords = 0

        for topic in topics:
            if topic in self.content_keywords:
                topic_keywords = self.content_keywords[topic]
                total_keywords += len(topic_keywords)
                matching_keywords += sum(1 for keyword in topic_keywords if keyword in content_lower)

        if total_keywords > 0:
            keyword_ratio = matching_keywords / total_keywords
            confidence += min(keyword_ratio, 0.3)  # Max boost of 0.3

        return min(confidence, 1.0)  # Cap at 1.0

    def enhance_document_metadata(self, doc: Document, file_path: Path) -> Dict[str, Any]:
        """Enhanced metadata extraction without LLM calls."""
        content = doc.page_content

        # Fast topic extraction
        content_types = self.extract_content_topics_fast(content, file_path)

        # Fast keyword extraction
        keywords = self.extract_content_keywords_fast(content)

        # Topic confidence
        topic_confidence = self.calculate_topic_confidence(content_types, content, file_path)

        # Special handling for illustration JSON files
        is_illustration_data = file_path.name == "illustrations.json"
        illustration_file = None

        if is_illustration_data:
            try:
                if '"file"' in doc.page_content:
                    data = json.loads(doc.page_content)
                    if isinstance(data, dict) and "file" in data:
                        illustration_file = data.get("file")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON content in {file_path}")

        # Build enhanced metadata
        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_type": ",".join(content_types),
            "content_types": ",".join(content_types),  # Legacy compatibility
            "content_length": len(content),
            "has_code": "```" in content or bool(re.search(r"\b(function|class|def|const|let|var)\b", content.lower())),
            "is_illustration_data": is_illustration_data,
            "illustration_file": illustration_file,
            "content_keywords": keywords,
            "topic_confidence": topic_confidence,
            "fast_classified": True,  # Indicator that fast classification was used
        }

        return metadata

    # --- Internal initialization helpers ---

    def _init_default_tables(self) -> None:
        """Populate built-in hardcoded patterns and keyword tables (legacy behavior)."""
        # Topic classification patterns
        self.topic_patterns = {
            "experience": [
                r"\b(experience|work|job|role|company|resume|cv|career|employment|position)\b",
                r"\b(worked|employed|professional|freelance|contractor|intern|manager|director|lead)\b",
                r"\b(years|since|from|to|duration|tenure|responsibilities|achievements)\b",
            ],
            "skills": [
                r"\b(skill|technology|tech|expertise|know|proficient|familiar|competent)\b",
                r"\b(programming|coding|languages|frameworks|tools|libraries|platforms)\b",
                r"\b(javascript|python|react|vue|angular|node|express|fastapi|django)\b",
                r"\b(html|css|typescript|sql|mongodb|postgresql|docker|kubernetes)\b",
            ],
            "about": [
                r"\b(about|who|background|interest|person|bio|philosophy|passion|motivation)\b",
                r"\b(tell me about|who is|what is.*like|personality|character|values)\b",
                r"\b(believes|approach|perspective|mindset|goals|mission)\b",
            ],
            "creative": [
                r"\b(illustration|art|design|creative|inspiration|artistic|visual|gallery)\b",
                r"\b(draw|paint|artwork|portfolio|sketch|cartoon|image|graphics)\b",
                r"\b(artist|designer|illustrator|creative process|style|aesthetic)\b",
            ],
            "project": [
                r"\b(project|built|created|developed|made|portfolio|application|app)\b",
                r"\b(github|code|repository|demo|website|platform|system|tool)\b",
                r"\b(development|implementation|architecture|features|functionality)\b",
            ],
            "technical": [
                r"\b(technical|code|programming|development|software|engineering|api)\b",
                r"\b(algorithm|function|class|method|database|server|client|frontend|backend)\b",
                r"\b(architecture|design pattern|best practices|optimization|performance)\b",
            ],
        }

        # Query complexity patterns
        self.complexity_patterns = {
            "simple": [
                r"^(what|who|when|where|list|show|tell me)\b",
                r"\b(skills|technologies|experience with|resume|cv)\b",
                r"^(list|show|display|give me|find)\b",
            ],
            "complex": [
                r"\b(how does|why|explain|approach|philosophy|compare|analyze|strategy)\b",
                r"\b(architecture|design pattern|best practices|methodology|process)\b",
                r"\b(implementation|integration|optimization|performance|scalability)\b",
            ],
        }

        # Query intent patterns
        self.intent_patterns = {
            "question": [r"\?$", r"^(what|who|how|why|when|where)", r"\b(is|are|do|does|can|will)\b"],
            "retrieval": [r"^(show|list|find|get|give me|display)", r"\b(illustrations|examples|samples|portfolio)\b"],
            "explanation": [r"\b(explain|describe|tell me about|how does|walk me through)\b"],
        }

        # File-based topic hints
        self.file_topic_hints = {
            "about": ["about", "bio", "personal", "profile"],
            "experience": ["resume", "cv", "work", "career", "employment"],
            "skills": ["skills", "technologies", "expertise", "competencies"],
            "creative": ["illustration", "art", "design", "gallery", "portfolio"],
            "project": ["project", "projects", "work", "development", "portfolio"],
        }

        # Keywords for fast content analysis
        self.content_keywords = {
            "experience": {
                "company",
                "role",
                "position",
                "responsibilities",
                "achievements",
                "professional",
                "employment",
                "work",
                "career",
                "manager",
                "director",
                "lead",
                "senior",
                "junior",
            },
            "skills": {
                "javascript",
                "python",
                "react",
                "vue",
                "angular",
                "node",
                "typescript",
                "html",
                "css",
                "sql",
                "mongodb",
                "postgresql",
                "docker",
                "kubernetes",
                "aws",
                "api",
            },
            "about": {
                "philosophy",
                "passion",
                "motivation",
                "believes",
                "values",
                "approach",
                "perspective",
                "mindset",
                "goals",
                "mission",
                "personality",
                "character",
                "background",
            },
            "creative": {
                "illustration",
                "art",
                "design",
                "artistic",
                "visual",
                "gallery",
                "draw",
                "paint",
                "artwork",
                "sketch",
                "cartoon",
                "image",
                "graphics",
                "creative",
                "inspiration",
            },
            "project": {
                "built",
                "created",
                "developed",
                "project",
                "application",
                "website",
                "platform",
                "system",
                "tool",
                "github",
                "repository",
                "demo",
                "portfolio",
            },
            "technical": {
                "code",
                "programming",
                "development",
                "software",
                "engineering",
                "algorithm",
                "function",
                "class",
                "method",
                "database",
                "server",
                "client",
                "api",
            },
        }

    def _init_from_taxonomy(self, tax: Dict[str, Any]) -> None:
        """Derive patterns and keyword tables from the taxonomy config."""
        cats = tax.get("categories", {})

        # Build topic_patterns using provided regex or synonyms
        topic_patterns: Dict[str, List[str]] = {}
        file_topic_hints: Dict[str, List[str]] = {}
        content_keywords: Dict[str, set] = {}

        for name, cfg in cats.items():
            syn = [s for s in (cfg.get("synonyms") or []) if isinstance(s, str) and s]
            regexes = [r for r in (cfg.get("regex") or []) if isinstance(r, str) and r]

            # If regex provided, use it; otherwise craft simple word-boundary regex per synonym
            if regexes:
                topic_patterns[name] = list(regexes)
            elif syn:
                topic_patterns[name] = [rf"\b({re.escape(s)})\b" for s in syn]
            else:
                topic_patterns[name] = []

            # File hints: reuse synonyms as filename hints
            file_topic_hints[name] = [s.lower() for s in syn]

            # Keywords: reuse synonyms as content keywords; allow optional explicit keywords
            kws = set(s.lower() for s in syn)
            for extra in cfg.get("keywords") or []:
                if isinstance(extra, str) and extra:
                    kws.add(extra.lower())
            content_keywords[name] = kws

        # Default patterns for complexity/intent unchanged
        self.complexity_patterns = {
            "simple": [
                r"^(what|who|when|where|list|show|tell me)\b",
                r"\b(skills|technologies|experience with|resume|cv)\b",
                r"^(list|show|display|give me|find)\b",
            ],
            "complex": [
                r"\b(how does|why|explain|approach|philosophy|compare|analyze|strategy)\b",
                r"\b(architecture|design pattern|best practices|methodology|process)\b",
                r"\b(implementation|integration|optimization|performance|scalability)\b",
            ],
        }
        self.intent_patterns = {
            "question": [r"\?$", r"^(what|who|how|why|when|where)", r"\b(is|are|do|does|can|will)\b"],
            "retrieval": [r"^(show|list|find|get|give me|display)", r"\b(illustrations|examples|samples|portfolio)\b"],
            "explanation": [r"\b(explain|describe|tell me about|how does|walk me through)\b"],
        }

        # Assign built tables
        self.topic_patterns = topic_patterns
        self.file_topic_hints = file_topic_hints
        self.content_keywords = content_keywords
