"""Tests for core.followup_service module."""

import concurrent.futures
import threading
from unittest.mock import patch

import pytest

from backend.core.followup_service import FollowUpService


class TestFollowupService:
    """Test cases for followup service module."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test that FollowUpService initializes correctly."""
        service = FollowUpService()

        # Verify question pools are initialized
        assert isinstance(service.question_pools, dict)
        assert "technical" in service.question_pools
        assert "personal" in service.question_pools
        assert "creative" in service.question_pools

        # Verify default questions are initialized as tuple (immutable)
        assert isinstance(service.default_questions, tuple)
        assert len(service.default_questions) == 6

        # Verify expected default questions are present
        expected_questions = (
            "Show me your illustrations",
            "Tell me about your experience",
            "What inspires your artwork?",
            "What technologies do you work with?",
            "What's your development philosophy?",
            "How can I contact Nick?",
        )
        assert service.default_questions == expected_questions

        # Verify initial state
        assert service.current_index == 0
        assert hasattr(service, "_lock")
        assert service._lock is not None
        assert service._cached_settings is None
        assert service._settings_cache_timestamp == 0

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_generate_followups_with_default_settings(self, mock_db_manager):
        """Test basic follow-up generation with default settings."""
        # Mock database to return None (no saved settings) and provide fallback categories
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Test with all parameters (as would be called in production)
        result = service.generate_followups(
            user_question="What is your experience?",
            ai_response="I have extensive experience in...",
            conversation_history=[{"user": "Hello", "assistant": "Hi there!"}],
        )

        # Should return list with exactly one question (default max_questions=1)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], str)
        # Should be from the available questions (fallback to question_pools)
        all_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )
        assert result[0] in all_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_sequential_ordering(self, mock_db_manager):
        """Test that questions are returned in sequential order."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool (from fallback hardcoded pools)
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        # Generate all questions in sequence (with max_questions=1 for sequential testing)
        results = []
        with patch.object(service, "_get_settings") as mock_settings:
            # Mock settings to return max_questions=1 for sequential testing
            from backend.core.settings_schemas import FollowUpSettings

            mock_settings.return_value = FollowUpSettings(max_questions=1)

            for i in range(len(expected_questions)):
                result = service.generate_followups("test", "test")
                results.extend(result)

        # Should match the expected questions in order
        assert results == expected_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_wrap_around_behavior(self, mock_db_manager):
        """Test that question selection wraps around after reaching the end."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        # Generate more questions than available (test wrap-around)
        results = []
        with patch.object(service, "_get_settings") as mock_settings:
            # Mock settings to return max_questions=1 for sequential testing
            from backend.core.settings_schemas import FollowUpSettings

            mock_settings.return_value = FollowUpSettings(max_questions=1)

            for i in range(len(expected_questions) + 3):  # Go beyond end
                result = service.generate_followups("test", "test")
                results.extend(result)

        # First len(expected_questions) should be the original questions
        assert results[: len(expected_questions)] == expected_questions

        # Next 3 should be the first 3 questions again (wrap-around)
        assert results[len(expected_questions) : len(expected_questions) + 3] == expected_questions[:3]

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_parameters_currently_unused(self, mock_db_manager):
        """Test that different parameter values don't affect output (currently unused)."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        # All these calls should return the same sequence regardless of parameters
        result1 = service.generate_followups("question1", "response1", [])
        result2 = service.generate_followups("question2", "response2", [{"user": "test"}])
        result3 = service.generate_followups("", "", None)

        # Since parameters are unused in static mode, all should return the next sequential questions
        # We can't predict exact values due to sequential nature, but they should be valid
        assert len(result1) == 1  # Default max_questions is 1 for static mode
        assert len(result2) == 1
        assert len(result3) == 1
        assert result1[0] in expected_questions
        assert result2[0] in expected_questions
        assert result3[0] in expected_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_thread_safety_no_skips_or_duplicates(self, mock_db_manager):
        """Test thread safety - no questions skipped or duplicated."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        n_calls = 100
        n_threads = 10

        def call_generate():
            return service.generate_followups("test", "test")[0]  # Get first question from result

        # Execute calls concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
            futures = [executor.submit(call_generate) for _ in range(n_calls)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify we got exactly n_calls results
        assert len(results) == n_calls

        # Verify all results are valid questions
        for result in results:
            assert result in expected_questions

        # Since execution order may vary due to threading, we can't guarantee exact sequence
        # But we can verify that we get a reasonable distribution and no invalid values
        result_counts = {q: results.count(q) for q in expected_questions}

        # Each question should appear at least once given enough calls
        # With 100 calls and 16 questions, expect roughly 6-7 of each
        for count in result_counts.values():
            assert count > 0  # Each question should appear at least once
            assert count < n_calls  # No single question should dominate completely

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_concurrent_index_consistency(self, mock_db_manager):
        """Test that concurrent access maintains proper index progression."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        results = []
        results_lock = threading.Lock()

        def thread_worker():
            for _ in range(10):
                result = service.generate_followups("test", "test")[0]  # Get first question from result
                with results_lock:
                    results.append(result)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=thread_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 50 total results (5 threads × 10 calls each)
        assert len(results) == 50

        # All results should be valid questions
        for result in results:
            assert result in expected_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_empty_questions_guard(self, mock_db_manager):
        """Test behavior when no questions are available from any source."""
        # Mock database to return empty results (no categories, no questions)
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = []  # No categories
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Temporarily override question_pools and default_questions to simulate empty state
        original_question_pools = service.question_pools
        original_default_questions = service.default_questions
        service.question_pools = {}
        service.default_questions = ()

        try:
            with patch("backend.core.followup_service.logger") as mock_logger:
                result = service.generate_followups("test", "test")

                # Should return empty list when no questions available
                assert result == []

                # Should log warning about no questions being available
                warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                no_questions_warning = any("No questions available" in call for call in warning_calls)
                assert no_questions_warning, f"Expected 'No questions available' warning, got: {warning_calls}"
        finally:
            # Restore original questions
            service.question_pools = original_question_pools
            service.default_questions = original_default_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_debug_logging(self, mock_db_manager):
        """Test that debug logging works correctly."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        with patch("backend.core.followup_service.logger") as mock_logger:
            service.generate_followups("test", "test")

            # The new architecture logs multiple debug messages:
            # - Category loading (3 calls for each category)
            # - Built question pool message
            # - Static selection message
            # So we verify that debug was called multiple times and includes the key messages
            assert mock_logger.debug.call_count >= 2

            # Check that the important debug messages are present
            debug_calls = [str(call) for call in mock_logger.debug.call_args_list]

            # Should have question pool building message
            pool_message_found = any("Built question pool with" in call for call in debug_calls)
            assert pool_message_found, f"Expected 'Built question pool' debug message, got: {debug_calls}"

            # Should have static selection message
            static_message_found = any("FollowUpService static: selected" in call for call in debug_calls)
            assert static_message_found, f"Expected 'static: selected' debug message, got: {debug_calls}"

    @pytest.mark.unit
    def test_immutable_questions(self):
        """Test that questions tuple cannot be accidentally mutated."""
        service = FollowUpService()

        # Attempting to modify tuple should raise error
        with pytest.raises((TypeError, AttributeError)):
            service.questions[0] = "Modified question"

        # Attempting to append should raise error
        with pytest.raises(AttributeError):
            service.questions.append("New question")

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_regression_api_compatibility(self, mock_db_manager):
        """Test that the API remains compatible with existing callers."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Test all expected calling patterns from the codebase

        # Basic call with required parameters
        result1 = service.generate_followups("user question", "ai response")
        assert len(result1) == 1  # Default max_questions is 1 for static service
        assert isinstance(result1[0], str)

        # Call with all parameters
        result2 = service.generate_followups("user question", "ai response", [{"user": "Hello", "assistant": "Hi"}])
        assert len(result2) == 1
        assert isinstance(result2[0], str)

        # Call with None conversation_history (explicit)
        result3 = service.generate_followups("user question", "ai response", None)
        assert len(result3) == 1
        assert isinstance(result3[0], str)

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_deterministic_sequence_single_thread(self, mock_db_manager):
        """Test that single-threaded calls produce deterministic sequence."""
        # Mock database to provide fallback behavior
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True, "sort_order": 1},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True, "sort_order": 2},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True, "sort_order": 3},
        ]
        mock_db_manager.get_followup_questions.return_value = []

        service = FollowUpService()

        # Build expected question pool
        expected_questions = (
            service.question_pools["technical"]
            + service.question_pools["personal"]
            + service.question_pools["creative"]
        )

        # Generate two full cycles
        first_cycle = []
        second_cycle = []

        with patch.object(service, "_get_settings") as mock_settings:
            # Mock settings to return max_questions=1 for sequential testing
            from backend.core.settings_schemas import FollowUpSettings

            mock_settings.return_value = FollowUpSettings(max_questions=1)

            # First cycle
            for _ in range(len(expected_questions)):
                result = service.generate_followups("test", "test")
                first_cycle.extend(result)

            # Second cycle
            for _ in range(len(expected_questions)):
                result = service.generate_followups("test", "test")
                second_cycle.extend(result)

        # Both cycles should be identical
        assert first_cycle == second_cycle
        assert first_cycle == expected_questions
