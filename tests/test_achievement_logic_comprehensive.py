"""
Comprehensive tests for achievement logic and unlocking mechanisms.
Tests achievement requirements, progress tracking, and edge cases.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.models import ACHIEVEMENTS
from utils.scoring_engine import ScoringEngine


class TestAchievementLogicComprehensive:
    """Comprehensive tests for achievement logic."""

    @pytest.fixture
    def scoring_engine(self):
        """Create ScoringEngine instance for testing."""
        return ScoringEngine()

    @pytest.fixture
    def sample_achievements(self):
        """Sample achievement definitions for testing."""
        return {
            "test_streak_5": {
                "name": "Test Streak 5",
                "description": "Answer 5 questions correctly in a row",
                "requirement": {"type": "streak", "value": 5},
                "reward_points": 50,
                "emoji": "🔥",
            },
            "test_total_100": {
                "name": "Test Total 100",
                "description": "Answer 100 questions correctly",
                "requirement": {"type": "total_correct", "value": 100},
                "reward_points": 200,
                "emoji": "💯",
            },
            "test_accuracy_90": {
                "name": "Test Accuracy 90",
                "description": "Maintain 90% accuracy over 50 questions",
                "requirement": {"type": "accuracy", "value": 90, "min_questions": 50},
                "reward_points": 300,
                "emoji": "🎯",
            },
            "test_daily_streak_7": {
                "name": "Test Daily Streak 7",
                "description": "Play for 7 consecutive days",
                "requirement": {"type": "daily_streak", "value": 7},
                "reward_points": 400,
                "emoji": "📅",
            },
        }

    def test_achievement_definitions_structure(self):
        """Test that achievement definitions have correct structure."""
        for achievement_id, achievement in ACHIEVEMENTS.items():
            # Test required fields
            assert "name" in achievement
            assert "description" in achievement
            assert "requirement" in achievement
            assert "reward_points" in achievement
            assert "emoji" in achievement

            # Test requirement structure
            requirement = achievement["requirement"]
            assert "type" in requirement
            assert "value" in requirement

            # Test data types
            assert isinstance(achievement["name"], str)
            assert isinstance(achievement["description"], str)
            assert isinstance(achievement["reward_points"], int)
            assert isinstance(achievement["emoji"], str)
            assert isinstance(requirement["type"], str)
            assert isinstance(requirement["value"], (int, float))

    def test_streak_achievement_logic(self, scoring_engine):
        """Test streak-based achievement logic."""
        # Test below threshold
        achievements = scoring_engine.check_streak_achievements(4, 12345)
        assert "hot_streak" not in achievements

        # Test at threshold
        achievements = scoring_engine.check_streak_achievements(5, 12345)
        assert "hot_streak" in achievements

        # Test above threshold
        achievements = scoring_engine.check_streak_achievements(7, 12345)
        assert "hot_streak" in achievements

        # Test multiple achievements
        achievements = scoring_engine.check_streak_achievements(10, 12345)
        assert "hot_streak" in achievements
        assert "galaxy_expert" in achievements

        # Test very high streak
        achievements = scoring_engine.check_streak_achievements(50, 12345)
        assert len(achievements) >= 2  # Should include multiple streak achievements

    def test_accuracy_achievement_progress(self, scoring_engine):
        """Test accuracy-based achievement progress calculation."""
        # Test insufficient questions
        stats_insufficient = {
            "user_profile": {"questions_answered": 30, "questions_correct": 27},
            "accuracy_percentage": 90.0,
        }

        accuracy_req = {"type": "accuracy", "value": 90, "min_questions": 50}
        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, stats_insufficient
        )

        # Should be based on question progress (30/50 = 60% of minimum)
        assert progress == 30.0  # (30/50) * 50 = 30%

        # Test sufficient questions, good accuracy
        stats_sufficient = {
            "user_profile": {"questions_answered": 60, "questions_correct": 54},
            "accuracy_percentage": 90.0,
        }

        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, stats_sufficient
        )
        assert progress == 100.0  # Meets accuracy requirement

        # Test sufficient questions, insufficient accuracy
        stats_low_accuracy = {
            "user_profile": {"questions_answered": 60, "questions_correct": 48},
            "accuracy_percentage": 80.0,
        }

        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, stats_low_accuracy
        )
        # 50 + (80/90 * 50) = 50 + 44.4 = 94.4
        assert progress == pytest.approx(94.4, rel=1e-1)

    def test_total_correct_achievement_progress(self, scoring_engine):
        """Test total correct achievement progress calculation."""
        total_req = {"type": "total_correct", "value": 100}

        # Test partial progress
        stats_partial = {
            "user_profile": {"questions_correct": 45},
        }

        progress = scoring_engine._calculate_achievement_progress(
            total_req, stats_partial
        )
        assert progress == 45.0  # 45/100 * 100

        # Test complete
        stats_complete = {
            "user_profile": {"questions_correct": 100},
        }

        progress = scoring_engine._calculate_achievement_progress(
            total_req, stats_complete
        )
        assert progress == 100.0

        # Test over-complete
        stats_over = {
            "user_profile": {"questions_correct": 150},
        }

        progress = scoring_engine._calculate_achievement_progress(total_req, stats_over)
        assert progress == 100.0  # Should cap at 100%

    def test_streak_achievement_progress(self, scoring_engine):
        """Test streak achievement progress calculation."""
        streak_req = {"type": "streak", "value": 10}

        # Test partial progress
        stats_partial = {
            "user_profile": {"current_streak": 6},
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, stats_partial
        )
        assert progress == 60.0  # 6/10 * 100

        # Test complete
        stats_complete = {
            "user_profile": {"current_streak": 10},
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, stats_complete
        )
        assert progress == 100.0

        # Test zero streak
        stats_zero = {
            "user_profile": {"current_streak": 0},
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, stats_zero
        )
        assert progress == 0.0

    def test_daily_streak_achievement_progress(self, scoring_engine):
        """Test daily streak achievement progress calculation."""
        daily_req = {"type": "daily_streak", "value": 7}

        # Daily streak calculation is complex and would need play history
        # For now, test that it returns 0 (as implemented)
        stats = {"user_profile": {}}

        progress = scoring_engine._calculate_achievement_progress(daily_req, stats)
        assert progress == 0  # Current implementation returns 0

    def test_unknown_achievement_type_progress(self, scoring_engine):
        """Test progress calculation for unknown achievement types."""
        unknown_req = {"type": "unknown_type", "value": 10}
        stats = {"user_profile": {}}

        progress = scoring_engine._calculate_achievement_progress(unknown_req, stats)
        assert progress == 0

    def test_achievement_progress_with_missing_data(self, scoring_engine):
        """Test achievement progress with missing user data."""
        # Test with empty user profile
        empty_stats = {"user_profile": {}}

        streak_req = {"type": "streak", "value": 5}
        progress = scoring_engine._calculate_achievement_progress(
            streak_req, empty_stats
        )
        assert progress == 0

        total_req = {"type": "total_correct", "value": 100}
        progress = scoring_engine._calculate_achievement_progress(
            total_req, empty_stats
        )
        assert progress == 0

        accuracy_req = {"type": "accuracy", "value": 90, "min_questions": 50}
        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, empty_stats
        )
        assert progress == 0

    def test_achievement_progress_edge_values(self, scoring_engine):
        """Test achievement progress with edge values."""
        # Test with very large values
        large_stats = {
            "user_profile": {
                "current_streak": 1000000,
                "questions_correct": 1000000,
                "questions_answered": 1000000,
            },
            "accuracy_percentage": 100.0,
        }

        streak_req = {"type": "streak", "value": 5}
        progress = scoring_engine._calculate_achievement_progress(
            streak_req, large_stats
        )
        assert progress == 100.0  # Should cap at 100%

        # Test with zero values
        zero_stats = {
            "user_profile": {
                "current_streak": 0,
                "questions_correct": 0,
                "questions_answered": 0,
            },
            "accuracy_percentage": 0.0,
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, zero_stats
        )
        assert progress == 0.0

    def test_multiple_achievement_checking(self, scoring_engine):
        """Test checking multiple achievements simultaneously."""
        # Create stats that should unlock multiple achievements
        high_performance_stats = {
            "user_profile": {
                "current_streak": 10,
                "questions_correct": 100,
                "questions_answered": 110,
            },
            "accuracy_percentage": 90.9,
        }

        # Mock the achievements checking (since we don't have the full achievement system)
        with patch.object(scoring_engine, "achievements", ACHIEVEMENTS):
            # Test that multiple achievements can be identified
            # This would require the full achievement checking system
            pass

    def test_achievement_requirement_validation(self):
        """Test validation of achievement requirements."""
        valid_requirements = [
            {"type": "streak", "value": 5},
            {"type": "total_correct", "value": 100},
            {"type": "accuracy", "value": 90, "min_questions": 50},
            {"type": "daily_streak", "value": 7},
        ]

        for req in valid_requirements:
            assert "type" in req
            assert "value" in req
            assert isinstance(req["value"], (int, float))
            assert req["value"] > 0

    def test_achievement_reward_points_calculation(self):
        """Test achievement reward points are reasonable."""
        for achievement_id, achievement in ACHIEVEMENTS.items():
            reward_points = achievement["reward_points"]

            # Reward points should be positive
            assert reward_points > 0

            # Reward points should be reasonable (not too high or low)
            assert 10 <= reward_points <= 1000

            # Reward points should be multiples of 10 (convention)
            assert reward_points % 10 == 0

    def test_achievement_difficulty_scaling(self):
        """Test that achievement difficulty scales appropriately."""
        streak_achievements = []
        total_achievements = []

        for achievement_id, achievement in ACHIEVEMENTS.items():
            req = achievement["requirement"]
            if req["type"] == "streak":
                streak_achievements.append((req["value"], achievement["reward_points"]))
            elif req["type"] == "total_correct":
                total_achievements.append((req["value"], achievement["reward_points"]))

        # Sort by requirement value
        streak_achievements.sort(key=lambda x: x[0])
        total_achievements.sort(key=lambda x: x[0])

        # Check that harder achievements have higher rewards
        if len(streak_achievements) > 1:
            for i in range(1, len(streak_achievements)):
                prev_req, prev_reward = streak_achievements[i - 1]
                curr_req, curr_reward = streak_achievements[i]

                # Higher requirement should have higher or equal reward
                assert curr_reward >= prev_reward

    def test_achievement_name_and_description_quality(self):
        """Test achievement names and descriptions are appropriate."""
        for achievement_id, achievement in ACHIEVEMENTS.items():
            name = achievement["name"]
            description = achievement["description"]

            # Names should be reasonable length
            assert 5 <= len(name) <= 50

            # Descriptions should be reasonable length
            assert 10 <= len(description) <= 200

            # Names should not contain special characters (except spaces)
            assert name.replace(" ", "").replace("'", "").isalnum()

            # Descriptions should end with appropriate punctuation or not
            # (This is a style choice, but let's check consistency)

    def test_achievement_emoji_validity(self):
        """Test achievement emojis are valid."""
        for achievement_id, achievement in ACHIEVEMENTS.items():
            emoji = achievement["emoji"]

            # Emoji should be a single character or valid emoji sequence
            assert len(emoji) >= 1
            assert len(emoji) <= 4  # Most emojis are 1-4 characters

            # Should not be regular ASCII letters/numbers
            assert not emoji.isalnum()

    def test_achievement_id_consistency(self):
        """Test achievement IDs follow consistent naming."""
        for achievement_id in ACHIEVEMENTS.keys():
            # IDs should be lowercase with underscores
            assert achievement_id.islower()
            assert " " not in achievement_id

            # Should contain only letters, numbers, and underscores
            assert achievement_id.replace("_", "").isalnum()

            # Should not start or end with underscore
            assert not achievement_id.startswith("_")
            assert not achievement_id.endswith("_")

    def test_achievement_progress_boundary_conditions(self, scoring_engine):
        """Test achievement progress at boundary conditions."""
        # Test exactly at requirement
        exact_stats = {
            "user_profile": {"current_streak": 5},
        }

        streak_req = {"type": "streak", "value": 5}
        progress = scoring_engine._calculate_achievement_progress(
            streak_req, exact_stats
        )
        assert progress == 100.0

        # Test one below requirement
        below_stats = {
            "user_profile": {"current_streak": 4},
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, below_stats
        )
        assert progress == 80.0  # 4/5 * 100

        # Test one above requirement
        above_stats = {
            "user_profile": {"current_streak": 6},
        }

        progress = scoring_engine._calculate_achievement_progress(
            streak_req, above_stats
        )
        assert progress == 100.0  # Should cap at 100%

    def test_achievement_progress_with_float_values(self, scoring_engine):
        """Test achievement progress with floating point values."""
        # Test accuracy with decimal values
        decimal_stats = {
            "user_profile": {"questions_answered": 100, "questions_correct": 87},
            "accuracy_percentage": 87.5,
        }

        accuracy_req = {"type": "accuracy", "value": 90.0, "min_questions": 50}
        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, decimal_stats
        )

        # Should handle decimal accuracy correctly
        # 50 + (87.5/90.0 * 50) = 50 + 48.6 = 98.6
        assert progress == pytest.approx(98.6, rel=1e-1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
