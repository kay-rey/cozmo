"""
Enhanced unit tests for the ScoringEngine class.
Comprehensive tests for scoring calculations, bonuses, analytics, and edge cases.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.scoring_engine import ScoringEngine
from utils.models import UserProfile, UserStats, ACHIEVEMENTS


class TestEnhancedScoringEngine:
    """Enhanced test suite for ScoringEngine class."""

    @pytest.fixture
    def scoring_engine(self):
        """Create ScoringEngine instance for testing."""
        return ScoringEngine()

    @pytest.fixture
    def sample_user_stats(self):
        """Create sample user statistics for testing."""
        return {
            "accuracy_percentage": 85.0,
            "difficulty_breakdown": {
                "easy": {"total": 20, "correct": 18, "points": 180},
                "medium": {"total": 15, "correct": 12, "points": 240},
                "hard": {"total": 10, "correct": 7, "points": 210},
            },
            "user_profile": {
                "total_points": 630,
                "questions_answered": 45,
                "questions_correct": 37,
                "current_streak": 5,
                "best_streak": 12,
            },
            "recent_performance": [
                True,
                True,
                False,
                True,
                True,
                True,
                False,
                True,
                True,
                True,
            ],
            "points_per_category": {
                "science": 200,
                "history": 180,
                "math": 150,
                "general": 100,
            },
        }

    def test_base_points_all_difficulties(self, scoring_engine):
        """Test base point calculation for all difficulty levels."""
        # Test correct answers
        assert scoring_engine.calculate_base_points("easy", True) == 10
        assert scoring_engine.calculate_base_points("medium", True) == 20
        assert scoring_engine.calculate_base_points("hard", True) == 30

        # Test incorrect answers
        assert scoring_engine.calculate_base_points("easy", False) == 0
        assert scoring_engine.calculate_base_points("medium", False) == 0
        assert scoring_engine.calculate_base_points("hard", False) == 0

        # Test invalid difficulty (should default to medium)
        assert scoring_engine.calculate_base_points("invalid", True) == 20
        assert scoring_engine.calculate_base_points("", True) == 20
        assert scoring_engine.calculate_base_points(None, True) == 20

    def test_time_bonus_comprehensive(self, scoring_engine):
        """Test comprehensive time bonus calculations."""
        # Test very fast answers (0-5 seconds)
        assert scoring_engine.calculate_time_bonus(0.0, 30) == 1.5
        assert scoring_engine.calculate_time_bonus(2.5, 30) == 1.5
        assert scoring_engine.calculate_time_bonus(5.0, 30) == 1.5

        # Test fast answers (5-10 seconds)
        assert scoring_engine.calculate_time_bonus(7.5, 30) == 1.3
        assert scoring_engine.calculate_time_bonus(10.0, 30) == 1.3

        # Test medium speed (10-20 seconds)
        assert scoring_engine.calculate_time_bonus(15.0, 30) == 1.1
        assert scoring_engine.calculate_time_bonus(20.0, 30) == 1.1

        # Test slow answers (20+ seconds)
        assert scoring_engine.calculate_time_bonus(25.0, 30) == 1.0
        assert scoring_engine.calculate_time_bonus(30.0, 30) == 1.0
        assert scoring_engine.calculate_time_bonus(35.0, 30) == 1.0  # Over time limit

        # Test with different max times
        assert (
            scoring_engine.calculate_time_bonus(5.0, 60) == 1.5
        )  # Still in first 5 seconds
        assert (
            scoring_engine.calculate_time_bonus(10.0, 60) == 1.3
        )  # Still in first 10 seconds

    def test_streak_bonus_comprehensive(self, scoring_engine):
        """Test comprehensive streak bonus calculations."""
        # Test no bonus range
        for streak in range(0, 3):
            assert scoring_engine.calculate_streak_bonus(streak) == 0

        # Test small bonus range (3-4)
        for streak in range(3, 5):
            assert scoring_engine.calculate_streak_bonus(streak) == 5

        # Test medium bonus range (5-9)
        for streak in range(5, 10):
            assert scoring_engine.calculate_streak_bonus(streak) == 10

        # Test large bonus range (10-19)
        for streak in range(10, 20):
            assert scoring_engine.calculate_streak_bonus(streak) == 20

        # Test maximum bonus range (20+)
        for streak in [20, 25, 50, 100]:
            assert scoring_engine.calculate_streak_bonus(streak) == 30

    def test_difficulty_progression_bonus_comprehensive(self, scoring_engine):
        """Test comprehensive difficulty progression bonus."""
        # Test poor accuracy (no bonus)
        for difficulty in ["easy", "medium", "hard"]:
            for accuracy in [0, 30, 59]:
                assert (
                    scoring_engine.calculate_difficulty_progression_bonus(
                        difficulty, accuracy
                    )
                    == 1.0
                )

        # Test hard difficulty with good accuracy
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("hard", 70.0) == 1.2
        )
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("hard", 85.0) == 1.2
        )
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("hard", 100.0) == 1.2
        )

        # Test medium difficulty with high accuracy
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("medium", 80.0) == 1.1
        )
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("medium", 90.0) == 1.1
        )

        # Test medium with lower accuracy (no bonus)
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("medium", 75.0) == 1.0
        )

        # Test easy difficulty (never gets bonus)
        for accuracy in [70, 80, 90, 100]:
            assert (
                scoring_engine.calculate_difficulty_progression_bonus("easy", accuracy)
                == 1.0
            )

    def test_total_score_calculation_comprehensive(self, scoring_engine):
        """Test comprehensive total score calculations."""
        # Test basic correct answer (no bonuses)
        result = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=25.0,
            current_streak=1,
            user_accuracy=50.0,
            max_time=30,
            is_challenge=False,
        )

        assert result["base_points"] == 20
        assert result["time_bonus_multiplier"] == 1.0
        assert result["streak_bonus"] == 0
        assert result["difficulty_bonus_multiplier"] == 1.0
        assert result["challenge_multiplier"] == 1.0
        assert result["total_points"] == 20

        # Test with all bonuses
        result = scoring_engine.calculate_total_score(
            difficulty="hard",
            is_correct=True,
            time_taken=3.0,  # Fast answer
            current_streak=8,  # Medium streak
            user_accuracy=85.0,  # High accuracy
            max_time=30,
            is_challenge=True,  # Challenge mode
        )

        # Base: 30, Time: 1.5x, Difficulty: 1.2x, Challenge: 2.0x, Streak: +10
        # (30 * 1.5 * 1.2 * 2.0) + 10 = 108 + 10 = 118
        assert result["base_points"] == 30
        assert result["time_bonus_multiplier"] == 1.5
        assert result["streak_bonus"] == 10
        assert result["difficulty_bonus_multiplier"] == 1.2
        assert result["challenge_multiplier"] == 2.0
        assert result["total_points"] == 118

    def test_total_score_incorrect_answer(self, scoring_engine):
        """Test total score for incorrect answers."""
        result = scoring_engine.calculate_total_score(
            difficulty="hard",
            is_correct=False,
            time_taken=5.0,
            current_streak=10,
            user_accuracy=90.0,
            is_challenge=True,
        )

        assert result["base_points"] == 0
        assert result["total_points"] == 0
        assert "Incorrect answer: 0 points" in result["breakdown"]

    def test_breakdown_formatting(self, scoring_engine):
        """Test that score breakdown is properly formatted."""
        result = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=8.0,
            current_streak=6,
            user_accuracy=82.0,
            is_challenge=False,
        )

        breakdown = result["breakdown"]

        # Check that all expected breakdown items are present
        assert any("Base points (medium): 20" in item for item in breakdown)
        assert any("Speed bonus: 1.3x" in item for item in breakdown)
        assert any("Streak bonus (6 streak): +10" in item for item in breakdown)
        assert any("Total:" in item for item in breakdown)

    def test_streak_achievements_checking(self, scoring_engine):
        """Test streak achievement checking."""
        # Test no achievements for low streaks
        achievements = scoring_engine.check_streak_achievements(2, 12345)
        assert len(achievements) == 0

        # Test hot streak achievement
        achievements = scoring_engine.check_streak_achievements(5, 12345)
        assert "hot_streak" in achievements

        # Test multiple achievements
        achievements = scoring_engine.check_streak_achievements(10, 12345)
        assert "hot_streak" in achievements
        assert "galaxy_expert" in achievements

        # Test very high streak
        achievements = scoring_engine.check_streak_achievements(25, 12345)
        assert "hot_streak" in achievements
        assert "galaxy_expert" in achievements

    def test_performance_analytics_comprehensive(
        self, scoring_engine, sample_user_stats
    ):
        """Test comprehensive performance analytics."""
        analytics = scoring_engine.calculate_performance_analytics(sample_user_stats)

        # Test structure
        required_keys = [
            "overall_performance",
            "strongest_difficulty",
            "weakest_difficulty",
            "improvement_suggestions",
            "achievement_progress",
            "efficiency_score",
            "consistency_score",
        ]
        for key in required_keys:
            assert key in analytics

        # Test performance rating
        assert analytics["overall_performance"] == "Very Good"  # 85% accuracy

        # Test difficulty analysis
        # easy: 18/20 = 90%, medium: 12/15 = 80%, hard: 7/10 = 70%
        assert analytics["strongest_difficulty"] == "easy"
        assert analytics["weakest_difficulty"] == "hard"

        # Test efficiency score
        expected_efficiency = 630 / 45  # total_points / questions_answered
        assert analytics["efficiency_score"] == expected_efficiency

        # Test consistency score
        recent_correct = sum(sample_user_stats["recent_performance"])
        expected_consistency = (
            recent_correct / len(sample_user_stats["recent_performance"])
        ) * 100
        assert analytics["consistency_score"] == expected_consistency

    def test_performance_analytics_edge_cases(self, scoring_engine):
        """Test performance analytics with edge cases."""
        # Test with minimal data
        minimal_stats = {
            "accuracy_percentage": 0.0,
            "difficulty_breakdown": {},
            "user_profile": {
                "total_points": 0,
                "questions_answered": 0,
                "current_streak": 0,
            },
            "recent_performance": [],
        }

        analytics = scoring_engine.calculate_performance_analytics(minimal_stats)
        assert analytics["overall_performance"] == "Needs Improvement"
        assert analytics["efficiency_score"] == 0.0
        assert analytics["consistency_score"] == 0.0

    def test_achievement_progress_calculation(self, scoring_engine, sample_user_stats):
        """Test achievement progress calculations."""
        # Test streak achievement progress
        streak_req = {"type": "streak", "value": 10}
        progress = scoring_engine._calculate_achievement_progress(
            streak_req, sample_user_stats
        )
        expected = min(100, (5 / 10) * 100)  # current_streak = 5, required = 10
        assert progress == expected

        # Test total correct achievement progress
        total_req = {"type": "total_correct", "value": 100}
        progress = scoring_engine._calculate_achievement_progress(
            total_req, sample_user_stats
        )
        expected = min(100, (37 / 100) * 100)  # questions_correct = 37, required = 100
        assert progress == expected

        # Test accuracy achievement progress
        accuracy_req = {"type": "accuracy", "value": 90, "min_questions": 20}
        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, sample_user_stats
        )
        # Has enough questions (45 >= 20), accuracy is 85/90 = 94.4% of target
        # 50 + (85/90 * 50) = 50 + 47.2 = 97.2
        assert progress == pytest.approx(97.2, rel=1e-1)

    def test_milestone_suggestions(self, scoring_engine):
        """Test milestone suggestion generation."""
        # Test streak milestone
        stats_streak = {
            "user_profile": {"current_streak": 3, "questions_correct": 50},
            "accuracy_percentage": 75.0,
        }
        suggestion = scoring_engine.get_next_milestone_suggestion(stats_streak)
        assert "2 more correct answers for Hot Streak" in suggestion

        # Test total correct milestone
        stats_total = {
            "user_profile": {"current_streak": 15, "questions_correct": 85},
            "accuracy_percentage": 75.0,
        }
        suggestion = scoring_engine.get_next_milestone_suggestion(stats_total)
        assert "15 more correct answers for Trivia Master" in suggestion

        # Test accuracy milestone
        stats_accuracy = {
            "user_profile": {
                "current_streak": 15,
                "questions_correct": 150,
                "questions_answered": 200,
            },
            "accuracy_percentage": 85.0,
        }
        suggestion = scoring_engine.get_next_milestone_suggestion(stats_accuracy)
        assert "Improve accuracy to 90%" in suggestion

    def test_weekly_performance_summary(self, scoring_engine):
        """Test weekly performance summary calculations."""
        weekly_stats = {
            "points_earned": 450,
            "questions_answered": 30,
            "questions_correct": 24,
            "best_streak": 8,
            "achievements_unlocked": 2,
            "difficulty_breakdown": {"easy": 10, "medium": 15, "hard": 5},
        }

        summary = scoring_engine.calculate_weekly_performance_summary(weekly_stats)

        # Test basic stats
        assert summary["total_points_earned"] == 450
        assert summary["questions_answered"] == 30
        assert summary["accuracy_percentage"] == 80.0  # 24/30
        assert summary["best_streak"] == 8
        assert summary["achievements_unlocked"] == 2
        assert summary["favorite_difficulty"] == "medium"  # Most played (15)

        # Test performance rating
        assert summary["performance_rating"] == "Great"  # 80% accuracy, 30 questions

    def test_weekly_performance_ratings(self, scoring_engine):
        """Test different weekly performance ratings."""
        # Outstanding performance
        outstanding_stats = {
            "points_earned": 600,
            "questions_answered": 20,
            "questions_correct": 18,  # 90% accuracy
            "best_streak": 12,
            "achievements_unlocked": 3,
            "difficulty_breakdown": {"hard": 20},
        }
        summary = scoring_engine.calculate_weekly_performance_summary(outstanding_stats)
        assert summary["performance_rating"] == "Outstanding"

        # Good performance
        good_stats = {
            "points_earned": 300,
            "questions_answered": 15,
            "questions_correct": 10,  # 66.7% accuracy
            "best_streak": 4,
            "achievements_unlocked": 1,
            "difficulty_breakdown": {"easy": 15},
        }
        summary = scoring_engine.calculate_weekly_performance_summary(good_stats)
        assert summary["performance_rating"] == "Good"

        # Keep practicing
        poor_stats = {
            "points_earned": 100,
            "questions_answered": 10,
            "questions_correct": 4,  # 40% accuracy
            "best_streak": 1,
            "achievements_unlocked": 0,
            "difficulty_breakdown": {"easy": 10},
        }
        summary = scoring_engine.calculate_weekly_performance_summary(poor_stats)
        assert summary["performance_rating"] == "Keep Practicing"

    def test_challenge_scoring_multipliers(self, scoring_engine):
        """Test challenge scoring multipliers."""
        # Regular question
        regular = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=15.0,
            current_streak=0,
            is_challenge=False,
        )

        # Challenge question
        challenge = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=15.0,
            current_streak=0,
            is_challenge=True,
        )

        # Challenge should have 2x multiplier
        assert challenge["challenge_multiplier"] == 2.0
        assert challenge["total_points"] == regular["total_points"] * 2

    def test_error_handling_in_analytics(self, scoring_engine):
        """Test error handling in analytics calculations."""
        # Test with malformed data
        malformed_stats = {
            "accuracy_percentage": "invalid",
            "difficulty_breakdown": None,
            "user_profile": {},
        }

        # Should not raise exception
        analytics = scoring_engine.calculate_performance_analytics(malformed_stats)
        assert isinstance(analytics, dict)
        assert "overall_performance" in analytics

    def test_achievement_progress_edge_cases(self, scoring_engine):
        """Test achievement progress calculation edge cases."""
        empty_stats = {
            "user_profile": {},
            "accuracy_percentage": 0,
        }

        # Test with empty requirements
        progress = scoring_engine._calculate_achievement_progress({}, empty_stats)
        assert progress == 0

        # Test with unknown requirement type
        unknown_req = {"type": "unknown_type", "value": 10}
        progress = scoring_engine._calculate_achievement_progress(
            unknown_req, empty_stats
        )
        assert progress == 0

    def test_scoring_with_extreme_values(self, scoring_engine):
        """Test scoring with extreme input values."""
        # Test with very large streak
        result = scoring_engine.calculate_total_score(
            difficulty="easy",
            is_correct=True,
            time_taken=1.0,
            current_streak=1000,
            user_accuracy=100.0,
        )
        assert result["streak_bonus"] == 30  # Should cap at maximum

        # Test with negative time (should handle gracefully)
        result = scoring_engine.calculate_total_score(
            difficulty="easy",
            is_correct=True,
            time_taken=-5.0,
            current_streak=0,
            user_accuracy=50.0,
        )
        assert result["time_bonus_multiplier"] == 1.5  # Should treat as very fast

        # Test with very large time
        result = scoring_engine.calculate_total_score(
            difficulty="easy",
            is_correct=True,
            time_taken=1000.0,
            current_streak=0,
            user_accuracy=50.0,
        )
        assert result["time_bonus_multiplier"] == 1.0  # Should be no bonus


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
