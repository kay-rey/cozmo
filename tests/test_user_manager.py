"""
Unit tests for the UserManager class.
Tests user profile creation, statistics tracking, and personalization features.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

# Add the parent directory to the path so we can import our modules
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.user_manager import UserManager
from utils.models import UserProfile, UserStats
from utils.database import DatabaseManager


class TestUserManager:
    """Test suite for UserManager class."""

    @pytest_asyncio.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()

        db_manager = DatabaseManager(temp_file.name)
        await db_manager.initialize_database()

        yield db_manager

        # Cleanup
        await db_manager.close_all_connections()
        os.unlink(temp_file.name)

    @pytest_asyncio.fixture
    async def user_manager(self, temp_db):
        """Create UserManager instance with temporary database."""
        manager = UserManager()
        manager.db_manager = temp_db
        return manager

    @pytest.mark.asyncio
    async def test_create_new_user(self, user_manager):
        """Test creating a new user profile."""
        user_id = 12345

        # Create new user
        user = await user_manager.get_or_create_user(user_id)

        assert user.user_id == user_id
        assert user.total_points == 0
        assert user.questions_answered == 0
        assert user.questions_correct == 0
        assert user.current_streak == 0
        assert user.best_streak == 0
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_get_existing_user(self, user_manager):
        """Test retrieving an existing user profile."""
        user_id = 12345

        # Create user first
        original_user = await user_manager.get_or_create_user(user_id)

        # Get the same user again
        retrieved_user = await user_manager.get_or_create_user(user_id)

        assert retrieved_user.user_id == original_user.user_id
        assert retrieved_user.created_at == original_user.created_at

    @pytest.mark.asyncio
    async def test_update_stats_correct_answer(self, user_manager):
        """Test updating stats for a correct answer."""
        user_id = 12345

        # Create user and update stats
        updated_user = await user_manager.update_stats(
            user_id=user_id,
            points=20,
            is_correct=True,
            difficulty="medium",
            category="players",
        )

        assert updated_user.total_points == 20
        assert updated_user.questions_answered == 1
        assert updated_user.questions_correct == 1
        assert updated_user.current_streak == 1
        assert updated_user.best_streak == 1
        assert updated_user.accuracy_percentage == 100.0

    @pytest.mark.asyncio
    async def test_update_stats_incorrect_answer(self, user_manager):
        """Test updating stats for an incorrect answer."""
        user_id = 12345

        # Create user with some correct answers first
        await user_manager.update_stats(user_id, 20, True, "medium")
        await user_manager.update_stats(user_id, 20, True, "medium")

        # Now answer incorrectly
        updated_user = await user_manager.update_stats(
            user_id=user_id,
            points=0,
            is_correct=False,
            difficulty="hard",
            category="history",
        )

        assert updated_user.total_points == 40  # No points added for wrong answer
        assert updated_user.questions_answered == 3
        assert updated_user.questions_correct == 2
        assert updated_user.current_streak == 0  # Streak reset
        assert updated_user.best_streak == 2  # Best streak preserved
        assert updated_user.accuracy_percentage == pytest.approx(66.67, rel=1e-2)

    @pytest.mark.asyncio
    async def test_streak_tracking(self, user_manager):
        """Test streak tracking functionality."""
        user_id = 12345

        # Answer 5 questions correctly
        for i in range(5):
            updated_user = await user_manager.update_stats(user_id, 10, True, "easy")

        assert updated_user.current_streak == 5
        assert updated_user.best_streak == 5

        # Answer incorrectly to break streak
        updated_user = await user_manager.update_stats(user_id, 0, False, "easy")
        assert updated_user.current_streak == 0
        assert updated_user.best_streak == 5  # Best streak preserved

        # Start new streak
        for i in range(3):
            updated_user = await user_manager.update_stats(user_id, 10, True, "easy")

        assert updated_user.current_streak == 3
        assert updated_user.best_streak == 5  # Still the best

    @pytest.mark.asyncio
    async def test_update_streak_method(self, user_manager):
        """Test the update_streak method specifically."""
        user_id = 12345

        # Create user first
        await user_manager.get_or_create_user(user_id)

        # Test correct answer streak
        streak = await user_manager.update_streak(user_id, True)
        assert streak == 1

        streak = await user_manager.update_streak(user_id, True)
        assert streak == 2

        # Test incorrect answer (streak reset)
        streak = await user_manager.update_streak(user_id, False)
        assert streak == 0

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_manager):
        """Test getting comprehensive user statistics."""
        user_id = 12345

        # Create some activity for the user
        await user_manager.update_stats(user_id, 10, True, "easy", "players")
        await user_manager.update_stats(user_id, 20, True, "medium", "history")
        await user_manager.update_stats(user_id, 0, False, "hard", "general")

        stats = await user_manager.get_user_stats(user_id)

        assert isinstance(stats, UserStats)
        assert stats.user_profile.user_id == user_id
        assert stats.user_profile.total_points == 30
        assert stats.user_profile.questions_answered == 3
        assert stats.user_profile.questions_correct == 2
        assert stats.accuracy_percentage == pytest.approx(66.67, rel=1e-2)

    @pytest.mark.asyncio
    async def test_reset_user_stats(self, user_manager):
        """Test resetting user statistics."""
        user_id = 12345

        # Create user with some stats
        await user_manager.update_stats(user_id, 50, True, "hard")
        await user_manager.update_stats(user_id, 20, True, "medium")

        # Verify stats exist
        user_before = await user_manager.get_or_create_user(user_id)
        assert user_before.total_points == 70
        assert user_before.questions_answered == 2

        # Reset stats
        success = await user_manager.reset_user_stats(user_id)
        assert success is True

        # Verify stats are reset
        user_after = await user_manager.get_or_create_user(user_id)
        assert user_after.total_points == 0
        assert user_after.questions_answered == 0
        assert user_after.questions_correct == 0
        assert user_after.current_streak == 0
        assert user_after.best_streak == 0

    @pytest.mark.asyncio
    async def test_challenge_completion_daily(self, user_manager):
        """Test daily challenge completion tracking."""
        user_id = 12345

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Check if user can attempt daily challenge (should be True initially)
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is True

        # Complete daily challenge
        success = await user_manager.update_challenge_completion(user_id, "daily")
        assert success is True

        # Check if user can attempt again (should be False)
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is False

    @pytest.mark.asyncio
    async def test_challenge_completion_weekly(self, user_manager):
        """Test weekly challenge completion tracking."""
        user_id = 12345

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Check if user can attempt weekly challenge (should be True initially)
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is True

        # Complete weekly challenge
        success = await user_manager.update_challenge_completion(user_id, "weekly")
        assert success is True

        # Check if user can attempt again (should be False for same week)
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is False

    @pytest.mark.asyncio
    async def test_get_user_rank(self, user_manager):
        """Test getting user rank in leaderboard."""
        # Create multiple users with different scores
        users_data = [
            (12345, 100),  # Should be rank 2
            (12346, 150),  # Should be rank 1
            (12347, 50),  # Should be rank 3
            (12348, 0),  # Should have no rank (0 points)
        ]

        for user_id, points in users_data:
            if points > 0:
                # Add points by answering questions
                remaining_points = points
                while remaining_points > 0:
                    question_points = min(
                        30, remaining_points
                    )  # Max 30 points per question
                    await user_manager.update_stats(
                        user_id, question_points, True, "hard"
                    )
                    remaining_points -= question_points
            else:
                # Just create the user
                await user_manager.get_or_create_user(user_id)

        # Test ranks
        rank_1 = await user_manager.get_user_rank(12346)  # 150 points
        rank_2 = await user_manager.get_user_rank(12345)  # 100 points
        rank_3 = await user_manager.get_user_rank(12347)  # 50 points
        rank_none = await user_manager.get_user_rank(12348)  # 0 points

        assert rank_1 == 1
        assert rank_2 == 2
        assert rank_3 == 3
        assert rank_none is None  # Users with 0 points don't get ranked

    @pytest.mark.asyncio
    async def test_get_user_preferences(self, user_manager):
        """Test getting user preferences and personalization data."""
        user_id = 12345

        # Create some activity for the user
        await user_manager.update_stats(user_id, 20, True, "medium", "players")
        await user_manager.update_stats(user_id, 30, True, "hard", "history")
        await user_manager.update_stats(user_id, 10, True, "easy", "general")

        preferences = await user_manager.get_user_preferences(user_id)

        assert isinstance(preferences, dict)
        assert "preferred_difficulty" in preferences
        assert "weak_areas" in preferences
        assert "next_goals" in preferences
        assert "play_streak_days" in preferences
        assert "favorite_categories" in preferences

    @pytest.mark.asyncio
    async def test_accuracy_calculation(self, user_manager):
        """Test accuracy percentage calculation."""
        user_id = 12345

        # Answer 7 out of 10 questions correctly
        correct_answers = [
            True,
            True,
            False,
            True,
            False,
            True,
            True,
            False,
            True,
            True,
        ]

        for is_correct in correct_answers:
            points = 10 if is_correct else 0
            await user_manager.update_stats(user_id, points, is_correct, "easy")

        user = await user_manager.get_or_create_user(user_id)
        assert user.accuracy_percentage == 70.0

    @pytest.mark.asyncio
    async def test_database_error_handling(self, user_manager):
        """Test error handling for database operations."""
        # Mock a database error
        with patch.object(user_manager.db_manager, "get_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception):
                await user_manager.get_or_create_user(12345)

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, user_manager):
        """Test concurrent operations on the same user."""
        user_id = 12345

        # Create user first to avoid race condition
        await user_manager.get_or_create_user(user_id)

        # Create multiple concurrent update operations
        tasks = []
        for i in range(5):
            task = user_manager.update_stats(user_id, 10, True, "easy")
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that at least some operations completed successfully
        # Due to database locking, some might fail, but at least one should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0

        # Verify final state - should have at least some points
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.total_points > 0
        assert final_user.questions_answered > 0
        assert final_user.questions_correct > 0

    @pytest.mark.asyncio
    async def test_user_profile_data_types(self, user_manager):
        """Test that user profile maintains correct data types."""
        user_id = 12345

        user = await user_manager.get_or_create_user(user_id)

        assert isinstance(user.user_id, int)
        assert isinstance(user.total_points, int)
        assert isinstance(user.questions_answered, int)
        assert isinstance(user.questions_correct, int)
        assert isinstance(user.current_streak, int)
        assert isinstance(user.best_streak, int)
        assert user.last_played is None or isinstance(user.last_played, datetime)
        assert user.daily_challenge_completed is None or isinstance(
            user.daily_challenge_completed, date
        )
        assert user.weekly_challenge_completed is None or isinstance(
            user.weekly_challenge_completed, date
        )
        assert user.preferred_difficulty is None or isinstance(
            user.preferred_difficulty, str
        )
        assert user.created_at is None or isinstance(user.created_at, datetime)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
