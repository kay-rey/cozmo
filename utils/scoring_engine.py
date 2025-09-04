"""
Scoring and streak tracking system for the Enhanced Trivia System.
Handles difficulty-based point calculation, streak tracking, and bonus calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from utils.models import POINT_VALUES, ACHIEVEMENTS

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Manages scoring calculations, streak tracking, and bonus point systems."""

    def __init__(self):
        self.base_point_values = POINT_VALUES
        self.achievements = ACHIEVEMENTS

    def calculate_base_points(self, difficulty: str, is_correct: bool) -> int:
        """Calculate base points for a question based on difficulty."""
        if not is_correct:
            return 0

        return self.base_point_values.get(difficulty, 20)

    def calculate_time_bonus(self, time_taken: float, max_time: int = 30) -> float:
        """Calculate time bonus multiplier based on how quickly question was answered."""
        if time_taken >= max_time:
            return 1.0  # No bonus for taking full time

        # Bonus ranges from 1.0 to 1.5 based on speed
        # Answered in first 5 seconds = 1.5x multiplier
        # Answered in 10 seconds = 1.3x multiplier
        # Answered in 20 seconds = 1.1x multiplier
        # Answered in 30 seconds = 1.0x multiplier

        time_ratio = time_taken / max_time
        if time_ratio <= 0.17:  # First 5 seconds (5/30)
            return 1.5
        elif time_ratio <= 0.33:  # First 10 seconds
            return 1.3
        elif time_ratio <= 0.67:  # First 20 seconds
            return 1.1
        else:
            return 1.0

    def calculate_streak_bonus(self, current_streak: int) -> int:
        """Calculate bonus points for answer streaks."""
        if current_streak < 3:
            return 0
        elif current_streak < 5:
            return 5  # Small bonus for 3-4 streak
        elif current_streak < 10:
            return 10  # Medium bonus for 5-9 streak
        elif current_streak < 20:
            return 20  # Large bonus for 10-19 streak
        else:
            return 30  # Maximum bonus for 20+ streak

    def calculate_difficulty_progression_bonus(
        self, difficulty: str, user_accuracy: float
    ) -> float:
        """Calculate bonus multiplier for playing higher difficulties with good accuracy."""
        if user_accuracy < 60:  # Poor accuracy, no bonus
            return 1.0

        if difficulty == "hard" and user_accuracy >= 70:
            return 1.2  # 20% bonus for hard questions with good accuracy
        elif difficulty == "medium" and user_accuracy >= 80:
            return 1.1  # 10% bonus for medium questions with high accuracy

        return 1.0

    def calculate_total_score(
        self,
        difficulty: str,
        is_correct: bool,
        time_taken: float,
        current_streak: int,
        user_accuracy: float = 0.0,
        max_time: int = 30,
        is_challenge: bool = False,
    ) -> Dict[str, Any]:
        """Calculate total score with all bonuses and multipliers."""
        result = {
            "base_points": 0,
            "time_bonus_multiplier": 1.0,
            "streak_bonus": 0,
            "difficulty_bonus_multiplier": 1.0,
            "challenge_multiplier": 1.0,
            "total_points": 0,
            "breakdown": [],
        }

        if not is_correct:
            result["breakdown"].append("Incorrect answer: 0 points")
            return result

        # Base points
        base_points = self.calculate_base_points(difficulty, is_correct)
        result["base_points"] = base_points
        result["breakdown"].append(f"Base points ({difficulty}): {base_points}")

        # Time bonus
        time_multiplier = self.calculate_time_bonus(time_taken, max_time)
        result["time_bonus_multiplier"] = time_multiplier
        if time_multiplier > 1.0:
            result["breakdown"].append(f"Speed bonus: {time_multiplier:.1f}x")

        # Streak bonus
        streak_bonus = self.calculate_streak_bonus(current_streak)
        result["streak_bonus"] = streak_bonus
        if streak_bonus > 0:
            result["breakdown"].append(
                f"Streak bonus ({current_streak} streak): +{streak_bonus}"
            )

        # Difficulty progression bonus
        difficulty_multiplier = self.calculate_difficulty_progression_bonus(
            difficulty, user_accuracy
        )
        result["difficulty_bonus_multiplier"] = difficulty_multiplier
        if difficulty_multiplier > 1.0:
            result["breakdown"].append(
                f"Difficulty mastery bonus: {difficulty_multiplier:.1f}x"
            )

        # Challenge multiplier
        if is_challenge:
            result["challenge_multiplier"] = 2.0  # Double points for challenges
            result["breakdown"].append("Challenge bonus: 2.0x")

        # Calculate total
        total_points = (
            int(
                base_points
                * time_multiplier
                * difficulty_multiplier
                * result["challenge_multiplier"]
            )
            + streak_bonus
        )

        result["total_points"] = total_points
        result["breakdown"].append(f"Total: {total_points} points")

        return result

    def check_streak_achievements(self, current_streak: int, user_id: int) -> List[str]:
        """Check if current streak qualifies for any achievements."""
        unlocked_achievements = []

        for achievement_id, achievement_data in self.achievements.items():
            requirement = achievement_data.get("requirement", {})

            if requirement.get("type") == "streak":
                required_streak = requirement.get("value", 0)
                if current_streak >= required_streak:
                    unlocked_achievements.append(achievement_id)

        return unlocked_achievements

    def calculate_performance_analytics(
        self, user_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate detailed performance analytics and reporting."""
        analytics = {
            "overall_performance": "Unknown",
            "strongest_difficulty": None,
            "weakest_difficulty": None,
            "improvement_suggestions": [],
            "achievement_progress": {},
            "efficiency_score": 0.0,
            "consistency_score": 0.0,
        }

        try:
            # Overall performance rating
            accuracy = user_stats.get("accuracy_percentage", 0)
            if accuracy >= 90:
                analytics["overall_performance"] = "Excellent"
            elif accuracy >= 80:
                analytics["overall_performance"] = "Very Good"
            elif accuracy >= 70:
                analytics["overall_performance"] = "Good"
            elif accuracy >= 60:
                analytics["overall_performance"] = "Fair"
            else:
                analytics["overall_performance"] = "Needs Improvement"

            # Difficulty analysis
            difficulty_breakdown = user_stats.get("difficulty_breakdown", {})
            if difficulty_breakdown:
                difficulty_scores = {}
                for difficulty, stats in difficulty_breakdown.items():
                    if stats.get("total", 0) > 0:
                        accuracy = (
                            stats.get("correct", 0) / stats.get("total", 1)
                        ) * 100
                        difficulty_scores[difficulty] = accuracy

                if difficulty_scores:
                    analytics["strongest_difficulty"] = max(
                        difficulty_scores, key=difficulty_scores.get
                    )
                    analytics["weakest_difficulty"] = min(
                        difficulty_scores, key=difficulty_scores.get
                    )

            # Improvement suggestions
            if accuracy < 70:
                analytics["improvement_suggestions"].append(
                    "Focus on easier questions to build confidence"
                )

            if analytics["weakest_difficulty"]:
                analytics["improvement_suggestions"].append(
                    f"Practice more {analytics['weakest_difficulty']} difficulty questions"
                )

            current_streak = user_stats.get("user_profile", {}).get("current_streak", 0)
            if current_streak < 3:
                analytics["improvement_suggestions"].append(
                    "Try to build a streak by answering consecutively"
                )

            # Achievement progress
            for achievement_id, achievement_data in self.achievements.items():
                requirement = achievement_data.get("requirement", {})
                progress = self._calculate_achievement_progress(requirement, user_stats)
                if progress < 100:  # Only show incomplete achievements
                    analytics["achievement_progress"][achievement_id] = {
                        "name": achievement_data.get("name", ""),
                        "description": achievement_data.get("description", ""),
                        "progress": progress,
                        "reward_points": achievement_data.get("reward_points", 0),
                    }

            # Efficiency score (points per question)
            total_points = user_stats.get("user_profile", {}).get("total_points", 0)
            questions_answered = user_stats.get("user_profile", {}).get(
                "questions_answered", 1
            )
            analytics["efficiency_score"] = total_points / questions_answered

            # Consistency score (based on recent performance)
            recent_performance = user_stats.get("recent_performance", [])
            if recent_performance:
                # Calculate variance in recent performance
                correct_count = sum(recent_performance)
                consistency = (correct_count / len(recent_performance)) * 100
                analytics["consistency_score"] = consistency

        except Exception as e:
            logger.error(f"Error calculating performance analytics: {e}")

        return analytics

    def _calculate_achievement_progress(
        self, requirement: Dict[str, Any], user_stats: Dict[str, Any]
    ) -> float:
        """Calculate progress towards a specific achievement."""
        req_type = requirement.get("type")
        req_value = requirement.get("value", 1)

        user_profile = user_stats.get("user_profile", {})

        if req_type == "streak":
            current_streak = user_profile.get("current_streak", 0)
            return min(100, (current_streak / req_value) * 100)

        elif req_type == "total_correct":
            questions_correct = user_profile.get("questions_correct", 0)
            return min(100, (questions_correct / req_value) * 100)

        elif req_type == "accuracy":
            accuracy = user_stats.get("accuracy_percentage", 0)
            min_questions = requirement.get("min_questions", 1)
            questions_answered = user_profile.get("questions_answered", 0)

            if questions_answered < min_questions:
                # Progress based on questions answered towards minimum
                return (
                    questions_answered / min_questions
                ) * 50  # 50% for reaching min questions
            else:
                # Progress based on accuracy
                if accuracy >= req_value:
                    return 100
                else:
                    return 50 + (
                        (accuracy / req_value) * 50
                    )  # 50-100% based on accuracy

        elif req_type == "daily_streak":
            # This would need to be calculated based on play history
            # For now, return 0 as it requires more complex tracking
            return 0

        return 0

    def get_next_milestone_suggestion(
        self, user_stats: Dict[str, Any]
    ) -> Optional[str]:
        """Suggest the next achievable milestone for the user."""
        user_profile = user_stats.get("user_profile", {})
        current_streak = user_profile.get("current_streak", 0)
        questions_correct = user_profile.get("questions_correct", 0)
        accuracy = user_stats.get("accuracy_percentage", 0)

        suggestions = []

        # Streak-based suggestions
        if current_streak < 5:
            suggestions.append(
                f"Reach a {5 - current_streak} more correct answers for Hot Streak achievement!"
            )
        elif current_streak < 10:
            suggestions.append(
                f"Just {10 - current_streak} more correct answers for Galaxy Expert achievement!"
            )

        # Total correct suggestions
        if questions_correct < 100:
            remaining = 100 - questions_correct
            if remaining <= 20:
                suggestions.append(
                    f"Only {remaining} more correct answers for Trivia Master achievement!"
                )

        # Accuracy suggestions
        if accuracy < 90 and user_profile.get("questions_answered", 0) >= 20:
            suggestions.append(
                f"Improve accuracy to 90% for Perfectionist achievement (currently {accuracy:.1f}%)"
            )

        # Return the most achievable suggestion
        return suggestions[0] if suggestions else None

    def calculate_weekly_performance_summary(
        self, weekly_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate a summary of weekly performance."""
        summary = {
            "total_points_earned": 0,
            "questions_answered": 0,
            "accuracy_percentage": 0.0,
            "best_streak": 0,
            "achievements_unlocked": 0,
            "favorite_difficulty": None,
            "improvement_from_last_week": 0,
            "performance_rating": "Unknown",
        }

        try:
            # Basic stats
            summary["total_points_earned"] = weekly_stats.get("points_earned", 0)
            summary["questions_answered"] = weekly_stats.get("questions_answered", 0)
            summary["best_streak"] = weekly_stats.get("best_streak", 0)
            summary["achievements_unlocked"] = weekly_stats.get(
                "achievements_unlocked", 0
            )

            # Calculate accuracy
            questions_correct = weekly_stats.get("questions_correct", 0)
            if summary["questions_answered"] > 0:
                summary["accuracy_percentage"] = (
                    questions_correct / summary["questions_answered"]
                ) * 100

            # Determine favorite difficulty
            difficulty_counts = weekly_stats.get("difficulty_breakdown", {})
            if difficulty_counts:
                summary["favorite_difficulty"] = max(
                    difficulty_counts, key=difficulty_counts.get
                )

            # Performance rating
            if (
                summary["accuracy_percentage"] >= 85
                and summary["questions_answered"] >= 10
            ):
                summary["performance_rating"] = "Outstanding"
            elif (
                summary["accuracy_percentage"] >= 75
                and summary["questions_answered"] >= 5
            ):
                summary["performance_rating"] = "Great"
            elif summary["accuracy_percentage"] >= 65:
                summary["performance_rating"] = "Good"
            else:
                summary["performance_rating"] = "Keep Practicing"

        except Exception as e:
            logger.error(f"Error calculating weekly performance summary: {e}")

        return summary


# Global scoring engine instance
scoring_engine = ScoringEngine()
