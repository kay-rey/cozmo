"""
Unit tests for the ScoringEngine class.
Tests scoring calculations, streak tracking, and performance analytics.
"""

import pytest
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import our modules
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.scoring_engine import ScoringEngine
from utils.models import UserProfile, UserStats


class TestScoringEngine:
    """Test suite for ScoringEngine class."""

    @pytest.fixture
    def scoring_engine(self):
        """Create ScoringEngine instance for testing."""
        return ScoringEngine()

    def test_calculate_base_points_correct_answers(self, scoring_engine):
        """Test base point calculation for correct answers."""
        assert scoring_engine.calculate_base_points("easy", True) == 10
        assert scoring_engine.calculate_base_points("medium", True) == 20
        assert scoring_engine.calculate_base_points("hard", True) == 30

    def test_calculate_base_points_incorrect_answers(self, scoring_engine):
        """Test base point calculation for incorrect answers."""
        assert scoring_engine.calculate_base_points("easy", False) == 0
        assert scoring_engine.calculate_base_points("medium", False) == 0
        assert scoring_engine.calculate_base_points("hard", False) == 0

    def test_calculate_base_points_unknown_difficulty(self, scoring_engine):
        """Test base point calculation for unknown difficulty."""
        assert (
            scoring_engine.calculate_base_points("unknown", True) == 20
        )  # Default value

    def test_calculate_time_bonus_fast_answer(self, scoring_engine):
        """Test time bonus for very fast answers."""
        # Answer in 3 seconds (first 5 seconds)
        bonus = scoring_engine.calculate_time_bonus(3.0, 30)
        assert bonus == 1.5

    def test_calculate_time_bonus_medium_speed(self, scoring_engine):
        """Test time bonus for medium speed answers."""
        # Answer in 8 seconds (first 10 seconds)
        bonus = scoring_engine.calculate_time_bonus(8.0, 30)
        assert bonus == 1.3

        # Answer in 15 seconds (first 20 seconds)
        bonus = scoring_engine.calculate_time_bonus(15.0, 30)
        assert bonus == 1.1

    def test_calculate_time_bonus_slow_answer(self, scoring_engine):
        """Test time bonus for slow answers."""
        # Answer in 25 seconds
        bonus = scoring_engine.calculate_time_bonus(25.0, 30)
        assert bonus == 1.0

        # Answer at time limit
        bonus = scoring_engine.calculate_time_bonus(30.0, 30)
        assert bonus == 1.0

    def test_calculate_streak_bonus(self, scoring_engine):
        """Test streak bonus calculations."""
        assert scoring_engine.calculate_streak_bonus(0) == 0
        assert scoring_engine.calculate_streak_bonus(2) == 0
        assert scoring_engine.calculate_streak_bonus(3) == 5
        assert scoring_engine.calculate_streak_bonus(4) == 5
        assert scoring_engine.calculate_streak_bonus(5) == 10
        assert scoring_engine.calculate_streak_bonus(9) == 10
        assert scoring_engine.calculate_streak_bonus(10) == 20
        assert scoring_engine.calculate_streak_bonus(19) == 20
        assert scoring_engine.calculate_streak_bonus(20) == 30
        assert scoring_engine.calculate_streak_bonus(50) == 30

    def test_calculate_difficulty_progression_bonus(self, scoring_engine):
        """Test difficulty progression bonus calculations."""
        # Poor accuracy - no bonus
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("hard", 50.0) == 1.0
        )

        # Good accuracy on hard questions
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("hard", 75.0) == 1.2
        )

        # High accuracy on medium questions
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("medium", 85.0) == 1.1
        )

        # Good accuracy on easy questions - no bonus
        assert (
            scoring_engine.calculate_difficulty_progression_bonus("easy", 90.0) == 1.0
        )

    def test_calculate_total_score_incorrect_answer(self, scoring_engine):
        """Test total score calculation for incorrect answer."""
        result = scoring_engine.calculate_total_score(
            difficulty="medium", is_correct=False, time_taken=10.0, current_streak=5
        )

        assert result["total_points"] == 0
        assert result["base_points"] == 0
        assert "Incorrect answer: 0 points" in result["breakdown"]

    def test_calculate_total_score_basic_correct_answer(self, scoring_engine):
        """Test total score calculation for basic correct answer."""
        result = scoring_engine.calculate_total_score(
            difficulty="medium", is_correct=True, time_taken=25.0, current_streak=1
        )

        assert result["base_points"] == 20
        assert result["total_points"] == 20  # No bonuses
        assert result["streak_bonus"] == 0
        assert result["time_bonus_multiplier"] == 1.0

    def test_calculate_total_score_with_all_bonuses(self, scoring_engine):
        """Test total score calculation with all bonuses."""
        result = scoring_engine.calculate_total_score(
            difficulty="hard",
            is_correct=True,
            time_taken=4.0,  # Fast answer for time bonus
            current_streak=7,  # Streak bonus
            user_accuracy=80.0,  # Difficulty bonus
            is_challenge=True,  # Challenge multiplier
        )

        # Base: 30, Time: 1.5x, Difficulty: 1.2x, Challenge: 2.0x, Streak: +10
        # (30 * 1.5 * 1.2 * 2.0) + 10 = 108 + 10 = 118
        assert result["base_points"] == 30
        assert result["time_bonus_multiplier"] == 1.5
        assert result["difficulty_bonus_multiplier"] == 1.2
        assert result["challenge_multiplier"] == 2.0
        assert result["streak_bonus"] == 10
        assert result["total_points"] == 118

    def test_check_streak_achievements(self, scoring_engine):
        """Test streak achievement checking."""
        # No achievements for low streak
        achievements = scoring_engine.check_streak_achievements(3, 12345)
        assert "hot_streak" not in achievements

        # Hot streak achievement
        achievements = scoring_engine.check_streak_achievements(5, 12345)
        assert "hot_streak" in achievements

        # Galaxy expert achievement
        achievements = scoring_engine.check_streak_achievements(10, 12345)
        assert "hot_streak" in achievements
        assert "galaxy_expert" in achievements

    def test_calculate_performance_analytics_excellent(self, scoring_engine):
        """Test performance analytics for excellent performance."""
        user_stats = {
            "accuracy_percentage": 95.0,
            "difficulty_breakdown": {
                "easy": {"total": 10, "correct": 9, "points": 90},
                "medium": {"total": 10, "correct": 8, "points": 160},
                "hard": {"total": 5, "correct": 5, "points": 150},
            },
            "user_profile": {
                "total_points": 430,
                "questions_answered": 25,
                "current_streak": 8,
            },
            "recent_performance": [
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                True,
                False,
                True,
            ],
        }

        analytics = scoring_engine.calculate_performance_analytics(user_stats)

        assert analytics["overall_performance"] == "Excellent"
        assert analytics["strongest_difficulty"] == "hard"  # 100% accuracy (5/5)
        assert analytics["weakest_difficulty"] == "medium"  # 80% accuracy (8/10)
        assert analytics["efficiency_score"] == 430 / 25  # Points per question
        assert analytics["consistency_score"] == 90.0  # 9/10 recent correct

    def test_calculate_performance_analytics_needs_improvement(self, scoring_engine):
        """Test performance analytics for poor performance."""
        user_stats = {
            "accuracy_percentage": 45.0,
            "difficulty_breakdown": {"easy": {"total": 20, "correct": 9, "points": 90}},
            "user_profile": {
                "total_points": 90,
                "questions_answered": 20,
                "current_streak": 1,
            },
            "recent_performance": [False, True, False, False, True],
        }

        analytics = scoring_engine.calculate_performance_analytics(user_stats)

        assert analytics["overall_performance"] == "Needs Improvement"
        assert (
            "Focus on easier questions to build confidence"
            in analytics["improvement_suggestions"]
        )
        assert (
            "Try to build a streak by answering consecutively"
            in analytics["improvement_suggestions"]
        )

    def test_get_next_milestone_suggestion_streak(self, scoring_engine):
        """Test milestone suggestions for streak achievements."""
        user_stats = {
            "user_profile": {"current_streak": 3, "questions_correct": 50},
            "accuracy_percentage": 75.0,
        }

        suggestion = scoring_engine.get_next_milestone_suggestion(user_stats)
        assert "2 more correct answers for Hot Streak" in suggestion

    def test_get_next_milestone_suggestion_total_correct(self, scoring_engine):
        """Test milestone suggestions for total correct achievements."""
        user_stats = {
            "user_profile": {
                "current_streak": 15,  # Already has streak achievements
                "questions_correct": 85,
            },
            "accuracy_percentage": 75.0,
        }

        suggestion = scoring_engine.get_next_milestone_suggestion(user_stats)
        assert "15 more correct answers for Trivia Master" in suggestion

    def test_get_next_milestone_suggestion_accuracy(self, scoring_engine):
        """Test milestone suggestions for accuracy achievements."""
        user_stats = {
            "user_profile": {
                "current_streak": 15,  # Already has streak achievements
                "questions_correct": 150,  # Already has total correct achievements
                "questions_answered": 200,
            },
            "accuracy_percentage": 85.0,
        }

        suggestion = scoring_engine.get_next_milestone_suggestion(user_stats)
        assert "Improve accuracy to 90%" in suggestion

    def test_calculate_weekly_performance_summary(self, scoring_engine):
        """Test weekly performance summary calculation."""
        weekly_stats = {
            "points_earned": 500,
            "questions_answered": 25,
            "questions_correct": 20,
            "best_streak": 8,
            "achievements_unlocked": 2,
            "difficulty_breakdown": {"easy": 5, "medium": 15, "hard": 5},
        }

        summary = scoring_engine.calculate_weekly_performance_summary(weekly_stats)

        assert summary["total_points_earned"] == 500
        assert summary["questions_answered"] == 25
        assert summary["accuracy_percentage"] == 80.0  # 20/25
        assert summary["best_streak"] == 8
        assert summary["achievements_unlocked"] == 2
        assert summary["favorite_difficulty"] == "medium"  # Most played
        assert summary["performance_rating"] == "Great"  # 80% accuracy, 25 questions

    def test_calculate_weekly_performance_summary_outstanding(self, scoring_engine):
        """Test weekly performance summary for outstanding performance."""
        weekly_stats = {
            "points_earned": 600,
            "questions_answered": 20,
            "questions_correct": 18,
            "best_streak": 12,
            "achievements_unlocked": 3,
            "difficulty_breakdown": {"hard": 20},
        }

        summary = scoring_engine.calculate_weekly_performance_summary(weekly_stats)

        assert summary["accuracy_percentage"] == 90.0  # 18/20
        assert (
            summary["performance_rating"] == "Outstanding"
        )  # 90% accuracy, 20 questions

    def test_calculate_weekly_performance_summary_keep_practicing(self, scoring_engine):
        """Test weekly performance summary for poor performance."""
        weekly_stats = {
            "points_earned": 100,
            "questions_answered": 10,
            "questions_correct": 5,
            "best_streak": 2,
            "achievements_unlocked": 0,
            "difficulty_breakdown": {"easy": 10},
        }

        summary = scoring_engine.calculate_weekly_performance_summary(weekly_stats)

        assert summary["accuracy_percentage"] == 50.0  # 5/10
        assert summary["performance_rating"] == "Keep Practicing"  # 50% accuracy

    def test_achievement_progress_calculation(self, scoring_engine):
        """Test achievement progress calculation."""
        user_stats = {
            "user_profile": {
                "current_streak": 3,
                "questions_correct": 50,
                "questions_answered": 60,
            },
            "accuracy_percentage": 83.33,
        }

        # Test streak achievement progress
        streak_req = {"type": "streak", "value": 5}
        progress = scoring_engine._calculate_achievement_progress(
            streak_req, user_stats
        )
        assert progress == 60.0  # 3/5 * 100

        # Test total correct achievement progress
        total_req = {"type": "total_correct", "value": 100}
        progress = scoring_engine._calculate_achievement_progress(total_req, user_stats)
        assert progress == 50.0  # 50/100 * 100

        # Test accuracy achievement progress
        accuracy_req = {"type": "accuracy", "value": 90, "min_questions": 50}
        progress = scoring_engine._calculate_achievement_progress(
            accuracy_req, user_stats
        )
        # Has enough questions (60 >= 50), accuracy is 83.33/90 = 92.6% of target
        # 50 + (83.33/90 * 50) = 50 + 46.3 = 96.3
        assert progress == pytest.approx(96.3, rel=1e-1)

    def test_challenge_scoring(self, scoring_engine):
        """Test scoring for challenge questions."""
        # Regular question
        regular_result = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=15.0,
            current_streak=0,
            is_challenge=False,
        )

        # Challenge question (same parameters)
        challenge_result = scoring_engine.calculate_total_score(
            difficulty="medium",
            is_correct=True,
            time_taken=15.0,
            current_streak=0,
            is_challenge=True,
        )

        # Challenge should have double points
        assert challenge_result["total_points"] == regular_result["total_points"] * 2
        assert challenge_result["challenge_multiplier"] == 2.0
        assert "Challenge bonus: 2.0x" in challenge_result["breakdown"]

    def test_scoring_breakdown_format(self, scoring_engine):
        """Test that scoring breakdown is properly formatted."""
        result = scoring_engine.calculate_total_score(
            difficulty="hard",
            is_correct=True,
            time_taken=5.0,
            current_streak=6,
            user_accuracy=85.0,
            is_challenge=True,
        )

        breakdown = result["breakdown"]
        assert any("Base points (hard): 30" in item for item in breakdown)
        assert any("Speed bonus: 1.5x" in item for item in breakdown)
        assert any("Streak bonus (6 streak): +10" in item for item in breakdown)
        assert any("Difficulty mastery bonus: 1.2x" in item for item in breakdown)
        assert any("Challenge bonus: 2.0x" in item for item in breakdown)
        assert any("Total:" in item for item in breakdown)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
