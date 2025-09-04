"""
Unit tests for the Achievement System.
Tests achievement definitions, progress tracking, unlock logic, and edge cases.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import the modules to test
from utils.achievement_system import (
    AchievementSystem,
    Achievement,
    UserAchievement,
    AchievementProgress,
    AchievementType,
    achievement_system,
)
from utils.database import DatabaseManager


class TestAchievementSystem:
    """Test cases for the AchievementSystem class."""

    @pytest.fixture
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

    @pytest.fixture
    def achievement_system_instance(self):
        """Create a fresh AchievementSystem instance for testing."""
        return AchievementSystem()

    def test_achievement_definitions_loaded(self, achievement_system_instance):
        """Test that achievement definitions are properly loaded."""
        achievements = achievement_system_instance.achievements

        # Check that achievements are loaded
        assert len(achievements) > 0

        # Check specific achievements exist
        assert "hot_streak" in achievements
        assert "galaxy_expert" in achievements
        assert "dedicated_fan" in achievements

        # Validate achievement structure
        hot_streak = achievements["hot_streak"]
        assert hot_streak.name == "Hot Streak"
        assert hot_streak.achievement_type == AchievementType.STREAK
        assert hot_streak.requirement["value"] == 5
        assert hot_streak.reward_points == 50
        assert hot_streak.emoji == "🔥"

    def test_achievement_categories(self, achievement_system_instance):
        """Test that achievements are properly categorized."""
        achievements = achievement_system_instance.achievements

        # Check that different categories exist
        categories = {achievement.category for achievement in achievements.values()}
        expected_categories = {
            "streaks",
            "dedication",
            "points",
            "participation",
            "accuracy",
            "difficulty",
            "challenges",
        }

        assert expected_categories.issubset(categories)

    @pytest.mark.asyncio
    async def test_unlock_achievement_success(
        self, temp_db, achievement_system_instance
    ):
        """Test successful achievement unlocking."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345
            achievement_id = "hot_streak"

            # Unlock the achievement
            result = await achievement_system_instance.unlock_achievement(
                user_id, achievement_id
            )
            assert result is True

            # Verify it was stored in database
            user_achievements = await achievement_system_instance.get_user_achievements(
                user_id
            )
            assert len(user_achievements) == 1
            assert user_achievements[0].achievement_id == achievement_id
            assert user_achievements[0].user_id == user_id

    @pytest.mark.asyncio
    async def test_unlock_achievement_duplicate(
        self, temp_db, achievement_system_instance
    ):
        """Test that duplicate achievement unlocks are handled properly."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345
            achievement_id = "hot_streak"

            # Unlock the achievement twice
            result1 = await achievement_system_instance.unlock_achievement(
                user_id, achievement_id
            )
            result2 = await achievement_system_instance.unlock_achievement(
                user_id, achievement_id
            )

            assert result1 is True
            assert result2 is True  # Should still return True but not create duplicate

            # Verify only one record exists
            user_achievements = await achievement_system_instance.get_user_achievements(
                user_id
            )
            assert len(user_achievements) == 1

    @pytest.mark.asyncio
    async def test_unlock_invalid_achievement(
        self, temp_db, achievement_system_instance
    ):
        """Test unlocking an invalid achievement ID."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345
            invalid_achievement_id = "nonexistent_achievement"

            result = await achievement_system_instance.unlock_achievement(
                user_id, invalid_achievement_id
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_streak_achievement(self, temp_db, achievement_system_instance):
        """Test checking streak-based achievements."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Test context with streak that meets hot_streak requirement
            context = {
                "current_streak": 5,
                "total_points": 100,
                "questions_answered": 10,
                "questions_correct": 8,
            }

            new_achievements = await achievement_system_instance.check_achievements(
                user_id, context
            )

            # Should unlock hot_streak achievement
            achievement_ids = [a.id for a in new_achievements]
            assert "hot_streak" in achievement_ids

    @pytest.mark.asyncio
    async def test_check_points_achievement(self, temp_db, achievement_system_instance):
        """Test checking points-based achievements."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Test context with points that meet point_collector requirement
            context = {
                "current_streak": 0,
                "total_points": 1000,
                "questions_answered": 50,
                "questions_correct": 40,
            }

            new_achievements = await achievement_system_instance.check_achievements(
                user_id, context
            )

            # Should unlock point_collector achievement
            achievement_ids = [a.id for a in new_achievements]
            assert "point_collector" in achievement_ids

    @pytest.mark.asyncio
    async def test_check_accuracy_achievement(
        self, temp_db, achievement_system_instance
    ):
        """Test checking accuracy-based achievements."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Test context with high accuracy over minimum questions
            context = {
                "current_streak": 0,
                "total_points": 500,
                "questions_answered": 100,
                "questions_correct": 85,  # 85% accuracy
            }

            new_achievements = await achievement_system_instance.check_achievements(
                user_id, context
            )

            # Should unlock sharp_shooter achievement (80% accuracy over 100 questions)
            achievement_ids = [a.id for a in new_achievements]
            assert "sharp_shooter" in achievement_ids

    @pytest.mark.asyncio
    async def test_accuracy_achievement_insufficient_questions(
        self, temp_db, achievement_system_instance
    ):
        """Test that accuracy achievements require minimum question count."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Test context with high accuracy but insufficient questions
            context = {
                "current_streak": 0,
                "total_points": 500,
                "questions_answered": 50,  # Below minimum of 100
                "questions_correct": 45,  # 90% accuracy
            }

            new_achievements = await achievement_system_instance.check_achievements(
                user_id, context
            )

            # Should not unlock accuracy achievements
            achievement_ids = [a.id for a in new_achievements]
            assert "sharp_shooter" not in achievement_ids
            assert "perfectionist" not in achievement_ids

    @pytest.mark.asyncio
    async def test_get_achievement_progress(self, temp_db, achievement_system_instance):
        """Test getting achievement progress."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Mock user stats for progress calculation
            with patch.object(
                achievement_system_instance,
                "_get_current_progress_value",
                return_value=3.0,
            ):
                progress = await achievement_system_instance.get_achievement_progress(
                    user_id, "hot_streak"
                )

                assert progress is not None
                assert progress.achievement_id == "hot_streak"
                assert progress.current_value == 3.0
                assert progress.required_value == 5.0
                assert progress.progress_percentage == 60.0
                assert progress.is_completed is False

    @pytest.mark.asyncio
    async def test_get_achievement_progress_completed(
        self, temp_db, achievement_system_instance
    ):
        """Test getting progress for a completed achievement."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345
            achievement_id = "hot_streak"

            # First unlock the achievement
            await achievement_system_instance.unlock_achievement(
                user_id, achievement_id
            )

            # Then check progress
            progress = await achievement_system_instance.get_achievement_progress(
                user_id, achievement_id
            )

            assert progress is not None
            assert progress.is_completed is True
            assert progress.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_get_user_achievement_stats(
        self, temp_db, achievement_system_instance
    ):
        """Test getting comprehensive user achievement statistics."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Unlock a few achievements
            await achievement_system_instance.unlock_achievement(user_id, "hot_streak")
            await achievement_system_instance.unlock_achievement(
                user_id, "point_collector"
            )

            stats = await achievement_system_instance.get_user_achievement_stats(
                user_id
            )

            assert stats["unlocked_count"] == 2
            assert stats["total_achievements"] > 0
            assert stats["completion_percentage"] > 0
            assert (
                stats["total_bonus_points"] == 150
            )  # 50 + 100 from the two achievements
            assert "category_stats" in stats
            assert "recent_achievements" in stats

    @pytest.mark.asyncio
    async def test_get_achievements_by_category(self, achievement_system_instance):
        """Test getting achievements filtered by category."""
        streak_achievements = (
            await achievement_system_instance.get_achievements_by_category("streaks")
        )

        assert len(streak_achievements) > 0
        for achievement in streak_achievements:
            assert achievement.category == "streaks"

    def test_get_all_achievements(self, achievement_system_instance):
        """Test getting all available achievements."""
        all_achievements = asyncio.run(
            achievement_system_instance.get_all_achievements()
        )

        assert len(all_achievements) > 0
        assert isinstance(all_achievements[0], Achievement)

    def test_get_achievement_by_id(self, achievement_system_instance):
        """Test getting a specific achievement by ID."""
        achievement = asyncio.run(
            achievement_system_instance.get_achievement_by_id("hot_streak")
        )

        assert achievement is not None
        assert achievement.id == "hot_streak"
        assert achievement.name == "Hot Streak"

    def test_get_achievement_by_invalid_id(self, achievement_system_instance):
        """Test getting an achievement with invalid ID."""
        achievement = asyncio.run(
            achievement_system_instance.get_achievement_by_id("invalid_id")
        )

        assert achievement is None

    @pytest.mark.asyncio
    async def test_daily_streak_calculation(self, temp_db, achievement_system_instance):
        """Test daily streak calculation logic."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Mock the daily streak calculation
            with patch.object(
                achievement_system_instance, "_calculate_daily_streak", return_value=7
            ):
                result = (
                    await achievement_system_instance._check_daily_streak_requirement(
                        user_id, 7
                    )
                )
                assert result is True

                result = (
                    await achievement_system_instance._check_daily_streak_requirement(
                        user_id, 10
                    )
                )
                assert result is False

    @pytest.mark.asyncio
    async def test_error_handling_in_check_achievements(
        self, temp_db, achievement_system_instance
    ):
        """Test error handling in achievement checking."""
        with patch("utils.achievement_system.db_manager", temp_db):
            user_id = 12345

            # Test with invalid context
            invalid_context = {"invalid_key": "invalid_value"}

            # Should not raise exception and return empty list
            new_achievements = await achievement_system_instance.check_achievements(
                user_id, invalid_context
            )
            assert isinstance(new_achievements, list)

    @pytest.mark.asyncio
    async def test_database_error_handling(self, achievement_system_instance):
        """Test handling of database errors."""
        user_id = 12345

        # Mock database connection to raise an exception
        with patch("utils.achievement_system.db_manager.get_connection") as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")

            # Should handle the error gracefully
            result = await achievement_system_instance.unlock_achievement(
                user_id, "hot_streak"
            )
            assert result is False

            achievements = await achievement_system_instance.get_user_achievements(
                user_id
            )
            assert achievements == []


if __name__ == "__main__":
    pytest.main([__file__])
