"""
Basic unit tests for the Achievement System.
Tests core functionality without complex database operations.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import the modules to test
from utils.achievement_system import (
    AchievementSystem,
    Achievement,
    UserAchievement,
    AchievementProgress,
    AchievementType,
)


class TestAchievementSystemBasic:
    """Basic test cases for the AchievementSystem class."""

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

    def test_achievement_types_valid(self, achievement_system_instance):
        """Test that all achievements have valid types."""
        achievements = achievement_system_instance.achievements

        valid_types = set(AchievementType)

        for achievement in achievements.values():
            assert achievement.achievement_type in valid_types

    def test_achievement_requirements_structure(self, achievement_system_instance):
        """Test that achievement requirements have proper structure."""
        achievements = achievement_system_instance.achievements

        for achievement in achievements.values():
            assert isinstance(achievement.requirement, dict)
            assert len(achievement.requirement) > 0

            # Check type-specific requirements
            if achievement.achievement_type == AchievementType.STREAK:
                assert "value" in achievement.requirement
                assert isinstance(achievement.requirement["value"], int)
                assert achievement.requirement["value"] > 0

            elif achievement.achievement_type == AchievementType.TOTAL_POINTS:
                assert "value" in achievement.requirement
                assert isinstance(achievement.requirement["value"], int)
                assert achievement.requirement["value"] > 0

    def test_achievement_reward_points_positive(self, achievement_system_instance):
        """Test that all achievements have positive reward points."""
        achievements = achievement_system_instance.achievements

        for achievement in achievements.values():
            assert achievement.reward_points > 0

    def test_achievement_names_unique(self, achievement_system_instance):
        """Test that all achievement names are unique."""
        achievements = achievement_system_instance.achievements

        names = [achievement.name for achievement in achievements.values()]
        assert len(names) == len(set(names))

    def test_achievement_ids_unique(self, achievement_system_instance):
        """Test that all achievement IDs are unique."""
        achievements = achievement_system_instance.achievements

        ids = [achievement.id for achievement in achievements.values()]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_get_all_achievements(self, achievement_system_instance):
        """Test getting all available achievements."""
        all_achievements = await achievement_system_instance.get_all_achievements()

        assert len(all_achievements) > 0
        assert isinstance(all_achievements[0], Achievement)

    @pytest.mark.asyncio
    async def test_get_achievement_by_id(self, achievement_system_instance):
        """Test getting a specific achievement by ID."""
        achievement = await achievement_system_instance.get_achievement_by_id(
            "hot_streak"
        )

        assert achievement is not None
        assert achievement.id == "hot_streak"
        assert achievement.name == "Hot Streak"

    @pytest.mark.asyncio
    async def test_get_achievement_by_invalid_id(self, achievement_system_instance):
        """Test getting an achievement with invalid ID."""
        achievement = await achievement_system_instance.get_achievement_by_id(
            "invalid_id"
        )

        assert achievement is None

    @pytest.mark.asyncio
    async def test_get_achievements_by_category(self, achievement_system_instance):
        """Test getting achievements filtered by category."""
        streak_achievements = (
            await achievement_system_instance.get_achievements_by_category("streaks")
        )

        assert len(streak_achievements) > 0
        for achievement in streak_achievements:
            assert achievement.category == "streaks"

    @pytest.mark.asyncio
    async def test_get_achievements_by_invalid_category(
        self, achievement_system_instance
    ):
        """Test getting achievements with invalid category."""
        invalid_achievements = (
            await achievement_system_instance.get_achievements_by_category(
                "invalid_category"
            )
        )

        assert len(invalid_achievements) == 0

    def test_streak_achievement_requirements(self, achievement_system_instance):
        """Test that streak achievements have proper requirements."""
        achievements = achievement_system_instance.achievements

        streak_achievements = [
            a
            for a in achievements.values()
            if a.achievement_type == AchievementType.STREAK
        ]

        assert len(streak_achievements) > 0

        for achievement in streak_achievements:
            assert "value" in achievement.requirement
            assert achievement.requirement["value"] > 0

    def test_points_achievement_requirements(self, achievement_system_instance):
        """Test that points achievements have proper requirements."""
        achievements = achievement_system_instance.achievements

        points_achievements = [
            a
            for a in achievements.values()
            if a.achievement_type == AchievementType.TOTAL_POINTS
        ]

        assert len(points_achievements) > 0

        for achievement in points_achievements:
            assert "value" in achievement.requirement
            assert achievement.requirement["value"] > 0

    def test_accuracy_achievement_requirements(self, achievement_system_instance):
        """Test that accuracy achievements have proper requirements."""
        achievements = achievement_system_instance.achievements

        accuracy_achievements = [
            a
            for a in achievements.values()
            if a.achievement_type == AchievementType.ACCURACY
        ]

        for achievement in accuracy_achievements:
            assert "value" in achievement.requirement
            assert "min_questions" in achievement.requirement
            assert achievement.requirement["value"] > 0
            assert achievement.requirement["min_questions"] > 0

    def test_achievement_emojis_present(self, achievement_system_instance):
        """Test that all achievements have emojis."""
        achievements = achievement_system_instance.achievements

        for achievement in achievements.values():
            assert achievement.emoji is not None
            assert len(achievement.emoji) > 0

    def test_achievement_descriptions_present(self, achievement_system_instance):
        """Test that all achievements have descriptions."""
        achievements = achievement_system_instance.achievements

        for achievement in achievements.values():
            assert achievement.description is not None
            assert len(achievement.description) > 0

    @pytest.mark.asyncio
    async def test_check_achievement_requirement_streak(
        self, achievement_system_instance
    ):
        """Test checking streak achievement requirements."""
        achievement = await achievement_system_instance.get_achievement_by_id(
            "hot_streak"
        )

        # Test context that meets requirement
        context_success = {"current_streak": 5}
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_success
        )
        assert result is True

        # Test context that doesn't meet requirement
        context_fail = {"current_streak": 3}
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_fail
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_achievement_requirement_points(
        self, achievement_system_instance
    ):
        """Test checking points achievement requirements."""
        achievement = await achievement_system_instance.get_achievement_by_id(
            "point_collector"
        )

        # Test context that meets requirement
        context_success = {"total_points": 1000}
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_success
        )
        assert result is True

        # Test context that doesn't meet requirement
        context_fail = {"total_points": 500}
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_fail
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_achievement_requirement_accuracy(
        self, achievement_system_instance
    ):
        """Test checking accuracy achievement requirements."""
        achievement = await achievement_system_instance.get_achievement_by_id(
            "sharp_shooter"
        )

        # Test context that meets requirement
        context_success = {
            "questions_answered": 100,
            "questions_correct": 85,  # 85% accuracy
        }
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_success
        )
        assert result is True

        # Test context with insufficient questions
        context_insufficient = {
            "questions_answered": 50,
            "questions_correct": 45,  # 90% accuracy but not enough questions
        }
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_insufficient
        )
        assert result is False

        # Test context with low accuracy
        context_low_accuracy = {
            "questions_answered": 100,
            "questions_correct": 70,  # 70% accuracy
        }
        result = await achievement_system_instance._check_achievement_requirement(
            12345, achievement, context_low_accuracy
        )
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
