"""
Performance tests for LLM call reduction improvements.

Tests verify that the fast classifiers achieve target performance improvements
while maintaining accuracy and response quality.
"""

import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from langchain.docstore.document import Document

from backend.core.content_indexer import ContentIndexer
from backend.core.fast_content_classifier import FastContentClassifier
from backend.core.fast_query_classifier import FastQueryClassifier
from backend.core.smart_query_handler import SmartQueryHandler


class TestQueryAnalysisPerformance:
    """Test query analysis performance improvements."""

    def test_fast_query_classification_performance(self):
        """Ensure fast query classification is < 100ms (vs previous 1-2 seconds)."""
        classifier = FastQueryClassifier()

        test_queries = [
            "What is Nick's experience with Vue.js?",
            "Show me creative illustrations",
            "Tell me about your development philosophy",
            "What programming languages does he know?",
            "Explain your approach to software architecture",
        ]

        total_time = 0
        for query in test_queries:
            start = time.time()
            result = classifier.classify(query)
            duration = time.time() - start
            total_time += duration

            # Each query should be analyzed in < 100ms
            assert duration < 0.1, f"Query analysis took {duration:.3f}s, expected < 0.1s"

            # Should return valid structure
            assert "topics" in result
            assert "complexity" in result
            assert "intent" in result
            assert isinstance(result["topics"], list)
            assert result["complexity"] in ["simple", "moderate", "complex"]

        avg_time = total_time / len(test_queries)
        assert avg_time < 0.05, f"Average query analysis time {avg_time:.3f}s, expected < 0.05s"

    def test_fast_content_classification_performance(self):
        """Test content metadata extraction performance."""
        classifier = FastContentClassifier()

        # Mock document with realistic content
        test_doc = Document(
            page_content="""
            Nick has extensive experience with Vue.js and React development.
            He has worked on multiple frontend projects using modern JavaScript frameworks.
            His expertise includes component architecture, state management, and performance optimization.
            """,
            metadata={},
        )

        file_path = Path("test_experience.md")

        start = time.time()
        metadata = classifier.enhance_document_metadata(test_doc, file_path)
        duration = time.time() - start

        # Should complete in < 50ms
        assert duration < 0.05, f"Content classification took {duration:.3f}s, expected < 0.05s"

        # Should extract relevant topics
        content_types = metadata["content_type"].split(",")
        assert any(topic in ["experience", "skills", "technical"] for topic in content_types)

        # Should include performance indicators
        assert metadata.get("fast_classified") is True
        assert "topic_confidence" in metadata

    def test_smart_query_handler_performance(self):
        """Test overall smart query handler performance improvement."""
        # Mock dependencies
        mock_retriever = Mock()
        mock_llm = Mock()

        handler = SmartQueryHandler(mock_retriever, mock_llm, use_fast_classifier=True)

        test_queries = [
            "What experience does Nick have?",
            "Show me creative work",
            "List technical skills",
        ]

        for query in test_queries:
            start = time.time()
            result = handler.analyze_query_fast(query)
            duration = time.time() - start

            # Fast analysis should be < 100ms
            assert duration < 0.1, f"Smart handler analysis took {duration:.3f}s"

            # Should maintain quality
            assert "topics" in result
            assert len(result["topics"]) > 0


class TestAccuracyValidation:
    """Test that fast classifiers maintain accuracy."""

    def test_topic_classification_accuracy(self):
        """Ensure fast classification maintains accuracy."""
        classifier = FastQueryClassifier()

        test_cases = [
            ("What experience does Nick have?", ["experience"]),
            ("Show me creative illustrations", ["creative"]),
            ("What programming languages does he know?", ["skills", "technical"]),
            ("Tell me about your background", ["about"]),
            ("What projects have you built?", ["project"]),
            ("How do you approach software design?", ["technical"]),
        ]

        correct_predictions = 0
        total_predictions = 0

        for query, expected_topics in test_cases:
            result = classifier.classify(query)
            predicted_topics = result["topics"]

            # Check if at least one expected topic was predicted
            if any(topic in predicted_topics for topic in expected_topics):
                correct_predictions += 1
            total_predictions += 1

        accuracy = correct_predictions / total_predictions
        assert accuracy >= 0.8, f"Classification accuracy {accuracy:.2f} below target 0.8"

    def test_content_metadata_accuracy(self):
        """Test content metadata extraction accuracy."""
        classifier = FastContentClassifier()

        test_cases = [
            (
                "Nick is a software engineer with 5+ years of experience in React and Vue.js development.",
                Path("experience.md"),
                ["experience", "skills", "technical"],
            ),
            (
                "Here are some creative illustrations I've created for various projects.",
                Path("illustrations.json"),
                ["creative"],
            ),
            ("About Nick: He's passionate about creating user-friendly web applications.", Path("about.md"), ["about"]),
        ]

        for content, file_path, expected_topics in test_cases:
            doc = Document(page_content=content, metadata={})
            metadata = classifier.enhance_document_metadata(doc, file_path)

            content_types = metadata["content_type"].split(",")

            # Should detect at least one expected topic
            found_topics = [topic for topic in expected_topics if topic in content_types]
            assert len(found_topics) > 0, f"Expected topics {expected_topics}, got {content_types}"

    def test_complexity_classification_accuracy(self):
        """Test query complexity classification accuracy."""
        classifier = FastQueryClassifier()

        test_cases = [
            ("What skills does Nick have?", "simple"),
            ("Tell me about your experience", "moderate"),
            ("How do you approach software architecture design?", "complex"),
            ("List projects", "simple"),
            ("Explain your development philosophy", "complex"),
        ]

        for query, expected_complexity in test_cases:
            result = classifier.classify(query)
            predicted_complexity = result["complexity"]

            # Allow some flexibility in complexity classification
            complexity_scores = {"simple": 1, "moderate": 2, "complex": 3}
            expected_score = complexity_scores[expected_complexity]
            predicted_score = complexity_scores[predicted_complexity]

            # Should be within 1 level of expected complexity
            assert (
                abs(expected_score - predicted_score) <= 1
            ), f"Expected {expected_complexity}, got {predicted_complexity} for '{query}'"


class TestFallbackBehavior:
    """Test fallback behavior when fast classifiers are disabled."""

    def test_content_indexer_fallback(self):
        """Test content indexer fallback to LLM when fast classifier disabled."""
        mock_llm = Mock()

        # Test with fast classifier disabled
        indexer = ContentIndexer(mock_llm, use_fast_classifier=False)

        doc = Document(page_content="Test content", metadata={})
        Path("test.md")

        # Should use LLM path when fast classifier disabled
        assert indexer.use_fast_classifier is False
        assert indexer.fast_classifier is None

    def test_smart_query_handler_fallback(self):
        """Test smart query handler fallback to LLM analysis."""
        mock_retriever = Mock()
        mock_llm = Mock()

        # Mock LLM response
        mock_llm.return_value = Mock()

        # Test with fast classifier disabled
        handler = SmartQueryHandler(mock_retriever, mock_llm, use_fast_classifier=False)

        assert handler.use_fast_classifier is False
        assert handler.fast_classifier is None


class TestMemoryUsage:
    """Test memory efficiency of fast classifiers."""

    def test_classifier_memory_efficiency(self):
        """Test that classifiers don't consume excessive memory."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create multiple classifiers
        classifiers = []
        for _ in range(10):
            classifiers.extend([FastQueryClassifier(), FastContentClassifier()])

        # Run classifications
        for i, classifier in enumerate(classifiers):
            if isinstance(classifier, FastQueryClassifier):
                classifier.classify(f"Test query {i}")
            else:
                doc = Document(page_content=f"Test content {i}", metadata={})
                classifier.enhance_document_metadata(doc, Path("test.md"))

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Should not increase memory by more than 50MB
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB"


@pytest.mark.integration
class TestEndToEndPerformance:
    """Integration tests for end-to-end performance improvements."""

    @pytest.mark.asyncio
    async def test_complete_query_flow_performance(self):
        """Test complete query flow performance improvement."""
        # This would require a more complete setup with actual retriever
        # For now, test the individual components that make up the flow

        query_classifier = FastQueryClassifier()
        content_classifier = FastContentClassifier()

        # Simulate complete flow timing
        start = time.time()

        # 1. Query analysis (should be < 50ms)
        query_analysis = query_classifier.classify("What is Nick's experience with React?")

        # 2. Content metadata (pre-computed, so effectively 0ms at query time)
        doc = Document(page_content="React developer with 3+ years experience", metadata={})
        metadata = content_classifier.enhance_document_metadata(doc, Path("experience.md"))

        # 3. Document context (lightweight, < 10ms)
        context = f"From {metadata['file_name']}: {doc.page_content[:100]}..."

        total_time = time.time() - start

        # Total analysis should be very fast
        assert total_time < 0.1, f"Complete analysis took {total_time:.3f}s, expected < 0.1s"

        # Verify quality maintained
        assert "experience" in query_analysis["topics"]
        assert "experience" in metadata["content_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
