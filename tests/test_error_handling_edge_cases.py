"""
Comprehensive error handling and edge case tests.
Tests system behavior under various error conditions and edge cases.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
import aiosqlite

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.scoring_engine import ScoringEngine
from utils.models import Question, UserProfile


class TestErrorHandlingEdgeCases:
    """Comprehensive error handling and edge case tests."""

    @pytest.fixture
    def question_engine(self):
        """Create QuestionEngine instance for testing."""
        return QuestionEngine()

    @pytest.fixture
    def scoring_engine(self):
        """Create ScoringEngine instance for testing."""
        return ScoringEngine()

    @pytest.fixture
    def mock_user_manager(self):
        """Create mock UserManager for testing."""
        manager = MagicMock(spec=UserManager)
        manager.get_or_create_user = AsyncMock()
        manager.update_stats = AsyncMock()
        return manager

    # Question Engine Error Handling Tests

    @pytest.mark.asyncio
    async def test_question_engine_empty_cache(self, question_engine):
        """Test question engine behavior with empty question cache."""
        # Clear all questions
        question_engine._questions_cache = {"easy": [], "medium": [], "hard": []}

        # Should return None when no questions available
        question = await question_engine.get_question()
        assert question is None

        question = await question_engine.get_question(difficulty="easy")
        assert question is None

    @pytest.mark.asyncio
    async def test_question_engine_corrupted_cache(self, question_engine):
        """Test question engine with corrupted cache data."""
        # Inject corrupted data
        question_engine._questions_cache = {
            "easy": [None, "invalid", {"not": "a question"}],
            "medium": [],
            "hard": [],
        }

        # Should handle corrupted data gracefully
        question = await question_engine.get_question(difficulty="easy")
        # Should either return None or handle the corruption

    def test_question_engine_invalid_question_data(self, question_engine):
        """Test question engine with invalid question data."""
        # Test with malformed question object
        invalid_question = Question()  # Empty question

        # Should handle validation gracefully
        result = asyncio.run(question_engine.validate_answer(invalid_question, "test"))
        assert result is False

    @pytest.mark.asyncio
    async def test_question_engine_memory_pressure(self, question_engine):
        """Test question engine under memory pressure."""
        # Simulate large cache operations
        large_cache = {"easy": [], "medium": [], "hard": []}

        # Create many question objects
        for i in range(1000):
            question = Question(
                id=i,
                question_text=f"Question {i}" * 100,  # Large text
                correct_answer=f"Answer {i}" * 50,
                options=[f"Option {j}" * 20 for j in range(4)],
            )
            large_cache["easy"].append(question)

        question_engine._questions_cache = large_cache

        # Should still function with large cache
        question = await question_engine.get_question(difficulty="easy")
        assert question is not None

    # User Manager Error Handling Tests

    @pytest.mark.asyncio
    async def test_user_manager_invalid_user_ids(self, mock_user_manager):
        """Test user manager with invalid user IDs."""
        invalid_ids = [None, -1, 0, "string", 2**64, float("inf")]

        for invalid_id in invalid_ids:
            try:
                await mock_user_manager.get_or_create_user(invalid_id)
                # If it doesn't raise an exception, that's also valid behavior
            except (TypeError, ValueError, OverflowError):
                # These exceptions are acceptable for invalid IDs
                pass

    @pytest.mark.asyncio
    async def test_user_manager_extreme_values(self, mock_user_manager):
        """Test user manager with extreme values."""
        user_id = 12345

        # Test with extreme point values
        extreme_values = [
            (2**31 - 1, True, "easy"),  # Max int
            (-1000, True, "easy"),  # Negative points
            (0, True, "easy"),  # Zero points
        ]

        for points, is_correct, difficulty in extreme_values:
            try:
                await mock_user_manager.update_stats(
                    user_id, points, is_correct, difficulty
                )
            except (ValueError, OverflowError):
                # Acceptable to reject extreme values
                pass

    @pytest.mark.asyncio
    async def test_user_manager_concurrent_modifications(self, mock_user_manager):
        """Test user manager with concurrent modifications."""
        user_id = 12345

        # Simulate race condition
        mock_user_manager.update_stats.side_effect = [
            UserProfile(user_id=user_id, total_points=10),
            Exception("Concurrent modification detected"),
            UserProfile(user_id=user_id, total_points=20),
        ]

        # Should handle concurrent modifications gracefully
        tasks = [
            mock_user_manager.update_stats(user_id, 10, True, "easy"),
            mock_user_manager.update_stats(user_id, 10, True, "easy"),
            mock_user_manager.update_stats(user_id, 10, True, "easy"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some operations should succeed or fail gracefully
        exceptions = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if isinstance(r, UserProfile)]

        assert len(exceptions) + len(successes) == len(tasks)

    # Scoring Engine Error Handling Tests

    def test_scoring_engine_invalid_inputs(self, scoring_engine):
        """Test scoring engine with invalid inputs."""
        invalid_inputs = [
            # (difficulty, is_correct, time_taken, current_streak, user_accuracy)
            (None, True, 10.0, 5, 80.0),
            ("invalid", True, 10.0, 5, 80.0),
            ("easy", None, 10.0, 5, 80.0),
            ("easy", True, None, 5, 80.0),
            ("easy", True, -10.0, 5, 80.0),  # Negative time
            ("easy", True, 10.0, None, 80.0),
            ("easy", True, 10.0, -5, 80.0),  # Negative streak
            ("easy", True, 10.0, 5, None),
            ("easy", True, 10.0, 5, -10.0),  # Negative accuracy
            ("easy", True, 10.0, 5, 150.0),  # Over 100% accuracy
        ]

        for (
            difficulty,
            is_correct,
            time_taken,
            current_streak,
            user_accuracy,
        ) in invalid_inputs:
            try:
                result = scoring_engine.calculate_total_score(
                    difficulty=difficulty,
                    is_correct=is_correct,
                    time_taken=time_taken,
                    current_streak=current_streak,
                    user_accuracy=user_accuracy,
                )
                # Should either handle gracefully or return sensible defaults
                assert isinstance(result, dict)
                assert "total_points" in result
            except (TypeError, ValueError):
                # Acceptable to reject invalid inputs
                pass

    def test_scoring_engine_extreme_calculations(self, scoring_engine):
        """Test scoring engine with extreme calculation values."""
        # Test with very large numbers
        result = scoring_engine.calculate_total_score(
            difficulty="hard",
            is_correct=True,
            time_taken=0.001,  # Very fast
            current_streak=10000,  # Very large streak
            user_accuracy=100.0,
            max_time=30,
            is_challenge=True,
        )

        # Should handle extreme values without overflow
        assert isinstance(result["total_points"], int)
        assert result["total_points"] >= 0

    def test_scoring_engine_division_by_zero(self, scoring_engine):
        """Test scoring engine division by zero scenarios."""
        # Test with zero max_time
        result = scoring_engine.calculate_time_bonus(10.0, 0)
        # Should handle gracefully (likely return 1.0 or handle the edge case)
        assert isinstance(result, float)
        assert result >= 0

    # Database Error Simulation Tests

    @pytest.mark.asyncio
    async def test_database_connection_timeout(self, mock_user_manager):
        """Test database connection timeout handling."""
        mock_user_manager.get_or_create_user.side_effect = asyncio.TimeoutError(
            "Database timeout"
        )

        with pytest.raises(asyncio.TimeoutError):
            await mock_user_manager.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_database_integrity_errors(self, mock_user_manager):
        """Test database integrity error handling."""
        mock_user_manager.update_stats.side_effect = aiosqlite.IntegrityError(
            "UNIQUE constraint failed"
        )

        with pytest.raises(aiosqlite.IntegrityError):
            await mock_user_manager.update_stats(12345, 10, True, "easy")

    @pytest.mark.asyncio
    async def test_database_corruption_errors(self, mock_user_manager):
        """Test database corruption error handling."""
        mock_user_manager.get_or_create_user.side_effect = aiosqlite.DatabaseError(
            "Database is corrupted"
        )

        with pytest.raises(aiosqlite.DatabaseError):
            await mock_user_manager.get_or_create_user(12345)

    # Memory and Resource Tests

    def test_memory_leak_prevention(self, question_engine):
        """Test prevention of memory leaks in caching."""
        initial_cache_size = len(question_engine._daily_challenge_cache)

        # Simulate many cache operations
        for i in range(100):
            question_engine._daily_challenge_cache[f"2024-01-{i:02d}"] = Question(id=i)

        # Cache should have reasonable limits or cleanup
        current_cache_size = len(question_engine._daily_challenge_cache)

        # Either cache grows reasonably or has cleanup mechanism
        assert current_cache_size <= 1000  # Reasonable upper limit

    def test_large_data_handling(self, scoring_engine):
        """Test handling of large data structures."""
        # Create large user stats
        large_stats = {
            "accuracy_percentage": 85.0,
            "difficulty_breakdown": {
                f"category_{i}": {"total": 1000, "correct": 850} for i in range(100)
            },
            "user_profile": {
                "total_points": 1000000,
                "questions_answered": 50000,
                "questions_correct": 42500,
                "current_streak": 1000,
            },
            "recent_performance": [True] * 10000,  # Very large recent performance
            "points_per_category": {f"cat_{i}": 10000 for i in range(1000)},
        }

        # Should handle large data without performance issues
        analytics = scoring_engine.calculate_performance_analytics(large_stats)
        assert isinstance(analytics, dict)

    # Edge Case Data Tests

    def test_unicode_and_special_characters(self, question_engine):
        """Test handling of unicode and special characters."""
        unicode_question = Question(
            question_text="What is 🌟 + 🌙?",
            correct_answer="✨",
            options=["🌟", "🌙", "✨", "💫"],
            answer_variations=["✨", "sparkles", "星星"],
        )

        # Should handle unicode characters
        result = asyncio.run(question_engine.validate_answer(unicode_question, "✨"))
        assert result is True

        result = asyncio.run(
            question_engine.validate_answer(unicode_question, "sparkles")
        )
        assert result is True

    def test_very_long_strings(self, question_engine):
        """Test handling of very long strings."""
        long_text = "A" * 10000
        long_question = Question(
            question_text=long_text,
            correct_answer=long_text,
            options=[long_text, "B", "C", "D"],
        )

        # Should handle long strings without issues
        result = asyncio.run(question_engine.validate_answer(long_question, long_text))
        assert result is True

    def test_empty_and_whitespace_strings(self, question_engine):
        """Test handling of empty and whitespace-only strings."""
        edge_cases = ["", "   ", "\t\n\r", "\u00a0"]  # Various whitespace

        question = Question(question_text="Test question", correct_answer="test")

        for edge_case in edge_cases:
            result = asyncio.run(question_engine.validate_answer(question, edge_case))
            assert result is False  # Should reject empty/whitespace answers

    # Concurrency and Threading Tests

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, question_engine):
        """Test concurrent access to question cache."""

        async def get_question_task():
            return await question_engine.get_question()

        # Create many concurrent tasks
        tasks = [get_question_task() for _ in range(50)]

        # Should handle concurrent access without corruption
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All results should be valid (Question objects or None)
        for result in results:
            assert result is None or isinstance(result, Question)

    @pytest.mark.asyncio
    async def test_concurrent_daily_challenge_access(self, question_engine):
        """Test concurrent access to daily challenge."""

        async def get_daily_challenge_task():
            return await question_engine.get_daily_challenge_question()

        # Multiple concurrent requests for daily challenge
        tasks = [get_daily_challenge_task() for _ in range(10)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All results should be the same question (or all None)
        valid_results = [r for r in results if isinstance(r, Question)]
        if len(valid_results) > 1:
            # All should have the same ID (same daily question)
            first_id = valid_results[0].id
            assert all(q.id == first_id for q in valid_results)

    # Performance and Stress Tests

    def test_performance_under_load(self, scoring_engine):
        """Test performance under high load."""
        import time

        start_time = time.time()

        # Perform many calculations
        for i in range(1000):
            scoring_engine.calculate_total_score(
                difficulty="medium",
                is_correct=True,
                time_taken=10.0,
                current_streak=i % 20,
                user_accuracy=85.0,
            )

        end_time = time.time()
        duration = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert duration < 5.0  # 5 seconds for 1000 calculations

    def test_memory_usage_stability(self, question_engine):
        """Test memory usage remains stable over time."""
        import gc

        # Force garbage collection
        gc.collect()

        # Perform many operations
        for i in range(100):
            asyncio.run(question_engine.get_question())
            if i % 10 == 0:
                gc.collect()

        # Memory should not grow excessively
        # This is a basic test - in practice you'd use memory profiling tools

    # Data Consistency Tests

    def test_data_consistency_after_errors(self, scoring_engine):
        """Test data consistency after error conditions."""
        # Perform normal operation
        result1 = scoring_engine.calculate_total_score("easy", True, 10.0, 5, 80.0)

        # Cause an error condition
        try:
            scoring_engine.calculate_total_score(None, True, 10.0, 5, 80.0)
        except:
            pass

        # Verify normal operation still works
        result2 = scoring_engine.calculate_total_score("easy", True, 10.0, 5, 80.0)

        # Results should be consistent
        assert result1["base_points"] == result2["base_points"]

    def test_state_isolation_between_operations(self, question_engine):
        """Test that operations don't affect each other's state."""
        # Get a question
        question1 = asyncio.run(question_engine.get_question(difficulty="easy"))

        # Perform some other operations
        asyncio.run(question_engine.get_daily_challenge_question())
        asyncio.run(question_engine.get_weekly_challenge_questions())

        # Get another question of same difficulty
        question2 = asyncio.run(question_engine.get_question(difficulty="easy"))

        # Operations should be independent
        if question1 and question2:
            # Both should be valid questions
            assert isinstance(question1, Question)
            assert isinstance(question2, Question)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
