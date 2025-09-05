"""
Enhanced unit tests for the UserManager class.
Comprehensive tests for user management, statistics, achievements, and edge cases.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import aiosqlite

# Add the parent directory to the path so we can import our modules
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.user_manager import UserManager
from utils.models import UserProfile, UserStats
from utils.database import DatabaseManager


class TestEnhancedUserManager:
    """Enhanced test suite for UserManager class."""

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

    @pytest_asyncio.fixture
    async def sample_users(self, user_manager):
        """Create sample users for testing."""
        users_data = [
            (
                12345,
                500,
                25,
                20,
                5,
                8,
            ),  # user_id, points, answered, correct, current_streak, best_streak
            (12346, 800, 40, 35, 3, 10),
            (12347, 300, 15, 10, 0, 5),
        ]

        created_users = []
        for user_data in users_data:
            user_id, points, answered, correct, current_streak, best_streak = user_data

            # Create user
            user = await user_manager.get_or_create_user(user_id)

            # Update stats to match test data
            async with user_manager.db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE users SET 
                        total_points = ?, questions_answered = ?, questions_correct = ?,
                        current_streak = ?, best_streak = ?, last_played = ?
                    WHERE user_id = ?
                    """,
                    (
                        points,
                        answered,
                        correct,
                        current_streak,
                        best_streak,
                        datetime.now(),
                        user_id,
                    ),
                )
                await conn.commit()

            created_users.append(user_id)

        return created_users

    @pytest.mark.asyncio
    async def test_user_creation_comprehensive(self, user_manager):
        """Test comprehensive user creation scenarios."""
        user_id = 99999

        # Test initial user creation
        user = await user_manager.get_or_create_user(user_id)

        assert user.user_id == user_id
        assert user.total_points == 0
        assert user.questions_answered == 0
        assert user.questions_correct == 0
        assert user.current_streak == 0
        assert user.best_streak == 0
        assert user.last_played is None
        assert user.daily_challenge_completed is None
        assert user.weekly_challenge_completed is None
        assert user.preferred_difficulty is None
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    @pytest.mark.asyncio
    async def test_user_retrieval_consistency(self, user_manager):
        """Test that user retrieval is consistent."""
        user_id = 88888

        # Create user
        user1 = await user_manager.get_or_create_user(user_id)
        creation_time = user1.created_at

        # Retrieve same user multiple times
        user2 = await user_manager.get_or_create_user(user_id)
        user3 = await user_manager.get_or_create_user(user_id)

        # All should be identical
        assert user1.user_id == user2.user_id == user3.user_id
        assert user1.created_at == user2.created_at == user3.created_at == creation_time

    @pytest.mark.asyncio
    async def test_stats_update_comprehensive(self, user_manager):
        """Test comprehensive statistics updates."""
        user_id = 77777

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Test multiple correct answers
        for i in range(5):
            points = (i + 1) * 10  # 10, 20, 30, 40, 50
            difficulty = ["easy", "medium", "hard"][i % 3]
            category = ["math", "science", "history"][i % 3]

            updated_user = await user_manager.update_stats(
                user_id=user_id,
                points=points,
                is_correct=True,
                difficulty=difficulty,
                category=category,
            )

        # Verify final stats
        assert updated_user.total_points == 150  # 10+20+30+40+50
        assert updated_user.questions_answered == 5
        assert updated_user.questions_correct == 5
        assert updated_user.current_streak == 5
        assert updated_user.best_streak == 5
        assert updated_user.accuracy_percentage == 100.0

    @pytest.mark.asyncio
    async def test_streak_mechanics_detailed(self, user_manager):
        """Test detailed streak mechanics."""
        user_id = 66666

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Build up a streak
        streak_results = []
        for i in range(7):
            user = await user_manager.update_stats(user_id, 10, True, "easy")
            streak_results.append(user.current_streak)

        assert streak_results == [1, 2, 3, 4, 5, 6, 7]
        assert user.best_streak == 7

        # Break the streak
        user = await user_manager.update_stats(user_id, 0, False, "easy")
        assert user.current_streak == 0
        assert user.best_streak == 7  # Best streak preserved

        # Start new streak
        user = await user_manager.update_stats(user_id, 10, True, "easy")
        assert user.current_streak == 1
        assert user.best_streak == 7  # Still preserved

        # Build longer streak
        for i in range(9):
            user = await user_manager.update_stats(user_id, 10, True, "easy")

        assert user.current_streak == 10
        assert user.best_streak == 10  # New best streak

    @pytest.mark.asyncio
    async def test_accuracy_calculation_edge_cases(self, user_manager):
        """Test accuracy calculation with edge cases."""
        user_id = 55555

        # Test with no questions answered
        user = await user_manager.get_or_create_user(user_id)
        assert user.accuracy_percentage == 0.0

        # Test with all correct answers
        for i in range(10):
            await user_manager.update_stats(user_id, 10, True, "easy")

        user = await user_manager.get_or_create_user(user_id)
        assert user.accuracy_percentage == 100.0

        # Test with all incorrect answers
        user_id_2 = 55556
        await user_manager.get_or_create_user(user_id_2)
        for i in range(10):
            await user_manager.update_stats(user_id_2, 0, False, "easy")

        user = await user_manager.get_or_create_user(user_id_2)
        assert user.accuracy_percentage == 0.0

        # Test with mixed results
        user_id_3 = 55557
        await user_manager.get_or_create_user(user_id_3)

        # 7 correct, 3 incorrect
        for i in range(7):
            await user_manager.update_stats(user_id_3, 10, True, "easy")
        for i in range(3):
            await user_manager.update_stats(user_id_3, 0, False, "easy")

        user = await user_manager.get_or_create_user(user_id_3)
        assert user.accuracy_percentage == 70.0

    @pytest.mark.asyncio
    async def test_preferred_difficulty_calculation(self, user_manager):
        """Test preferred difficulty calculation logic."""
        user_id = 44444

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Test correct answer maintains difficulty
        user = await user_manager.update_stats(user_id, 30, True, "hard")
        assert user.preferred_difficulty == "hard"

        # Test incorrect answer suggests easier difficulty
        user = await user_manager.update_stats(user_id, 0, False, "hard")
        assert user.preferred_difficulty == "medium"

        # Test medium to easy progression
        user = await user_manager.update_stats(user_id, 0, False, "medium")
        assert user.preferred_difficulty == "easy"

        # Test easy stays easy when incorrect
        user = await user_manager.update_stats(user_id, 0, False, "easy")
        assert user.preferred_difficulty == "easy"

    @pytest.mark.asyncio
    async def test_challenge_completion_tracking(self, user_manager):
        """Test challenge completion tracking."""
        user_id = 33333

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Test daily challenge
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is True

        # Complete daily challenge
        success = await user_manager.update_challenge_completion(user_id, "daily")
        assert success is True

        # Check can't attempt again today
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is False

        # Test weekly challenge
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is True

        # Complete weekly challenge
        success = await user_manager.update_challenge_completion(user_id, "weekly")
        assert success is True

        # Check can't attempt again this week
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is False

    @pytest.mark.asyncio
    async def test_weekly_challenge_week_boundary(self, user_manager):
        """Test weekly challenge across week boundaries."""
        user_id = 22222

        # Create user
        await user_manager.get_or_create_user(user_id)

        # Mock completion date to last week
        last_week = date.today() - timedelta(days=7)

        async with user_manager.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET weekly_challenge_completed = ? WHERE user_id = ?",
                (last_week, user_id),
            )
            await conn.commit()

        # Should be able to attempt this week
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is True

    @pytest.mark.asyncio
    async def test_user_stats_comprehensive(self, user_manager, sample_users):
        """Test comprehensive user statistics retrieval."""
        user_id = sample_users[0]  # First sample user

        stats = await user_manager.get_user_stats(user_id)

        # Verify structure
        assert isinstance(stats, UserStats)
        assert isinstance(stats.user_profile, UserProfile)
        assert isinstance(stats.accuracy_percentage, float)
        assert isinstance(stats.points_per_category, dict)
        assert isinstance(stats.difficulty_breakdown, dict)
        assert isinstance(stats.recent_performance, list)
        assert isinstance(stats.achievements_count, int)

        # Verify user profile data
        assert stats.user_profile.user_id == user_id
        assert stats.user_profile.total_points > 0
        assert stats.user_profile.questions_answered > 0

    @pytest.mark.asyncio
    async def test_user_ranking_system(self, user_manager, sample_users):
        """Test user ranking system."""
        # Get ranks for all sample users
        ranks = []
        for user_id in sample_users:
            rank = await user_manager.get_user_rank(user_id)
            ranks.append((user_id, rank))

        # Verify ranking order (higher points = better rank)
        # Sample users: 12345(500pts), 12346(800pts), 12347(300pts)
        # Expected order: 12346(1st), 12345(2nd), 12347(3rd)

        user_ranks = {user_id: rank for user_id, rank in ranks if rank is not None}

        if len(user_ranks) >= 2:
            # User with 800 points should have better rank than user with 500 points
            assert user_ranks[12346] < user_ranks[12345]
            # User with 500 points should have better rank than user with 300 points
            assert user_ranks[12345] < user_ranks[12347]

    @pytest.mark.asyncio
    async def test_user_preferences_analysis(self, user_manager):
        """Test user preferences and analysis."""
        user_id = 11111

        # Create user with varied activity
        await user_manager.get_or_create_user(user_id)

        # Add activity in different categories and difficulties
        activities = [
            (20, True, "medium", "science"),
            (30, True, "hard", "science"),
            (10, False, "easy", "math"),
            (20, True, "medium", "history"),
            (30, False, "hard", "science"),
        ]

        for points, is_correct, difficulty, category in activities:
            await user_manager.update_stats(
                user_id, points, is_correct, difficulty, category
            )

        preferences = await user_manager.get_user_preferences(user_id)

        # Verify structure
        assert "preferred_difficulty" in preferences
        assert "weak_areas" in preferences
        assert "next_goals" in preferences
        assert "play_streak_days" in preferences
        assert "favorite_categories" in preferences

        # Verify data types
        assert isinstance(preferences["weak_areas"], list)
        assert isinstance(preferences["next_goals"], list)
        assert isinstance(preferences["favorite_categories"], list)

    @pytest.mark.asyncio
    async def test_user_reset_functionality(self, user_manager):
        """Test user statistics reset functionality."""
        user_id = 10101

        # Create user with stats
        await user_manager.get_or_create_user(user_id)

        # Add some activity
        for i in range(5):
            await user_manager.update_stats(user_id, 20, True, "medium")

        # Verify stats exist
        user_before = await user_manager.get_or_create_user(user_id)
        assert user_before.total_points > 0
        assert user_before.questions_answered > 0

        # Reset stats
        success = await user_manager.reset_user_stats(user_id)
        assert success is True

        # Verify reset
        user_after = await user_manager.get_or_create_user(user_id)
        assert user_after.total_points == 0
        assert user_after.questions_answered == 0
        assert user_after.questions_correct == 0
        assert user_after.current_streak == 0
        assert user_after.best_streak == 0
        assert user_after.daily_challenge_completed is None
        assert user_after.weekly_challenge_completed is None

    @pytest.mark.asyncio
    async def test_concurrent_user_operations(self, user_manager):
        """Test concurrent operations on user data."""
        user_id = 99999

        # Create user first
        await user_manager.get_or_create_user(user_id)

        # Create multiple concurrent update tasks
        async def update_task(points, is_correct):
            try:
                return await user_manager.update_stats(
                    user_id, points, is_correct, "easy"
                )
            except Exception as e:
                return e

        tasks = [
            update_task(10, True),
            update_task(10, True),
            update_task(10, False),
            update_task(10, True),
            update_task(10, True),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least some operations should succeed
        successful_results = [r for r in results if isinstance(r, UserProfile)]
        assert len(successful_results) > 0

        # Verify final state is consistent
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.questions_answered > 0
        assert final_user.total_points >= 0

    @pytest.mark.asyncio
    async def test_database_error_handling(self, user_manager):
        """Test database error handling."""
        user_id = 88888

        # Mock database connection failure
        with patch.object(user_manager.db_manager, "get_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            # Should raise exception
            with pytest.raises(Exception):
                await user_manager.get_or_create_user(user_id)

            with pytest.raises(Exception):
                await user_manager.update_stats(user_id, 10, True, "easy")

    @pytest.mark.asyncio
    async def test_data_type_consistency(self, user_manager):
        """Test that all data types remain consistent."""
        user_id = 77777

        # Create and update user
        user = await user_manager.get_or_create_user(user_id)
        user = await user_manager.update_stats(user_id, 25, True, "medium", "science")

        # Verify all data types
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
        assert isinstance(user.accuracy_percentage, float)

    @pytest.mark.asyncio
    async def test_edge_case_user_ids(self, user_manager):
        """Test edge cases for user IDs."""
        edge_case_ids = [0, 1, 2**63 - 1, -1]  # Various edge case IDs

        for user_id in edge_case_ids:
            if user_id >= 0:  # Only test valid user IDs
                user = await user_manager.get_or_create_user(user_id)
                assert user.user_id == user_id

    @pytest.mark.asyncio
    async def test_last_played_tracking(self, user_manager):
        """Test last played timestamp tracking."""
        user_id = 66666

        # Create user
        user = await user_manager.get_or_create_user(user_id)
        assert user.last_played is None

        # Update stats
        before_update = datetime.now()
        user = await user_manager.update_stats(user_id, 10, True, "easy")
        after_update = datetime.now()

        # Verify last_played is set and within expected range
        assert user.last_played is not None
        assert before_update <= user.last_played <= after_update


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
