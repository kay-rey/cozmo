"""
Achievement System for the Enhanced Trivia System.
Handles achievement definitions, progress tracking, unlock logic, and reward distribution.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .database import db_manager

logger = logging.getLogger(__name__)


class AchievementType(Enum):
    """Types of achievements available in the system."""

    STREAK = "streak"
    DAILY_STREAK = "daily_streak"
    TOTAL_POINTS = "total_points"
    TOTAL_QUESTIONS = "total_questions"
    ACCURACY = "accuracy"
    DIFFICULTY_MASTER = "difficulty_master"
    CATEGORY_EXPERT = "category_expert"
    CHALLENGE_COMPLETION = "challenge_completion"


@dataclass
class Achievement:
    """Represents an achievement definition."""

    id: str
    name: str
    description: str
    achievement_type: AchievementType
    requirement: Dict[str, Any]
    reward_points: int
    emoji: str
    is_hidden: bool = False
    category: str = "general"


@dataclass
class UserAchievement:
    """Represents a user's unlocked achievement."""

    id: int
    user_id: int
    achievement_id: str
    unlocked_at: datetime
    achievement: Optional[Achievement] = None


@dataclass
class AchievementProgress:
    """Represents progress towards an achievement."""

    achievement_id: str
    current_value: float
    required_value: float
    progress_percentage: float
    is_completed: bool


class AchievementSystem:
    """Manages achievements, progress tracking, and rewards."""

    def __init__(self):
        self.achievements = self._load_achievement_definitions()
        self._progress_cache = {}  # Cache for achievement progress

    def _load_achievement_definitions(self) -> Dict[str, Achievement]:
        """Load all achievement definitions."""
        achievements = {
            # Streak Achievements
            "hot_streak": Achievement(
                id="hot_streak",
                name="Hot Streak",
                description="Answer 5 questions correctly in a row",
                achievement_type=AchievementType.STREAK,
                requirement={"value": 5},
                reward_points=50,
                emoji="🔥",
                category="streaks",
            ),
            "galaxy_expert": Achievement(
                id="galaxy_expert",
                name="Galaxy Expert",
                description="Answer 10 questions correctly in a row",
                achievement_type=AchievementType.STREAK,
                requirement={"value": 10},
                reward_points=100,
                emoji="⭐",
                category="streaks",
            ),
            "unstoppable": Achievement(
                id="unstoppable",
                name="Unstoppable",
                description="Answer 20 questions correctly in a row",
                achievement_type=AchievementType.STREAK,
                requirement={"value": 20},
                reward_points=250,
                emoji="🚀",
                category="streaks",
            ),
            # Daily Streak Achievements
            "dedicated_fan": Achievement(
                id="dedicated_fan",
                name="Dedicated Fan",
                description="Play trivia for 7 consecutive days",
                achievement_type=AchievementType.DAILY_STREAK,
                requirement={"value": 7},
                reward_points=200,
                emoji="💙",
                category="dedication",
            ),
            "super_fan": Achievement(
                id="super_fan",
                name="Super Fan",
                description="Play trivia for 30 consecutive days",
                achievement_type=AchievementType.DAILY_STREAK,
                requirement={"value": 30},
                reward_points=1000,
                emoji="👑",
                category="dedication",
            ),
            # Point Achievements
            "point_collector": Achievement(
                id="point_collector",
                name="Point Collector",
                description="Earn 1,000 total points",
                achievement_type=AchievementType.TOTAL_POINTS,
                requirement={"value": 1000},
                reward_points=100,
                emoji="💰",
                category="points",
            ),
            "point_master": Achievement(
                id="point_master",
                name="Point Master",
                description="Earn 5,000 total points",
                achievement_type=AchievementType.TOTAL_POINTS,
                requirement={"value": 5000},
                reward_points=500,
                emoji="💎",
                category="points",
            ),
            "point_legend": Achievement(
                id="point_legend",
                name="Point Legend",
                description="Earn 10,000 total points",
                achievement_type=AchievementType.TOTAL_POINTS,
                requirement={"value": 10000},
                reward_points=1000,
                emoji="🏆",
                category="points",
            ),
            # Question Count Achievements
            "trivia_rookie": Achievement(
                id="trivia_rookie",
                name="Trivia Rookie",
                description="Answer 50 questions",
                achievement_type=AchievementType.TOTAL_QUESTIONS,
                requirement={"value": 50},
                reward_points=50,
                emoji="🌟",
                category="participation",
            ),
            "trivia_veteran": Achievement(
                id="trivia_veteran",
                name="Trivia Veteran",
                description="Answer 500 questions",
                achievement_type=AchievementType.TOTAL_QUESTIONS,
                requirement={"value": 500},
                reward_points=300,
                emoji="🎖️",
                category="participation",
            ),
            "trivia_master": Achievement(
                id="trivia_master",
                name="Trivia Master",
                description="Answer 1,000 questions",
                achievement_type=AchievementType.TOTAL_QUESTIONS,
                requirement={"value": 1000},
                reward_points=750,
                emoji="🏅",
                category="participation",
            ),
            # Accuracy Achievements
            "sharp_shooter": Achievement(
                id="sharp_shooter",
                name="Sharp Shooter",
                description="Maintain 80% accuracy over 100 questions",
                achievement_type=AchievementType.ACCURACY,
                requirement={"value": 80, "min_questions": 100},
                reward_points=200,
                emoji="🎯",
                category="accuracy",
            ),
            "perfectionist": Achievement(
                id="perfectionist",
                name="Perfectionist",
                description="Maintain 90% accuracy over 200 questions",
                achievement_type=AchievementType.ACCURACY,
                requirement={"value": 90, "min_questions": 200},
                reward_points=500,
                emoji="💯",
                category="accuracy",
            ),
            # Difficulty Master Achievements
            "easy_master": Achievement(
                id="easy_master",
                name="Easy Master",
                description="Answer 100 easy questions correctly",
                achievement_type=AchievementType.DIFFICULTY_MASTER,
                requirement={"difficulty": "easy", "correct_answers": 100},
                reward_points=100,
                emoji="📚",
                category="difficulty",
            ),
            "medium_master": Achievement(
                id="medium_master",
                name="Medium Master",
                description="Answer 100 medium questions correctly",
                achievement_type=AchievementType.DIFFICULTY_MASTER,
                requirement={"difficulty": "medium", "correct_answers": 100},
                reward_points=200,
                emoji="🧠",
                category="difficulty",
            ),
            "hard_master": Achievement(
                id="hard_master",
                name="Hard Master",
                description="Answer 100 hard questions correctly",
                achievement_type=AchievementType.DIFFICULTY_MASTER,
                requirement={"difficulty": "hard", "correct_answers": 100},
                reward_points=400,
                emoji="🔥",
                category="difficulty",
            ),
            # Challenge Achievements
            "daily_challenger": Achievement(
                id="daily_challenger",
                name="Daily Challenger",
                description="Complete 10 daily challenges",
                achievement_type=AchievementType.CHALLENGE_COMPLETION,
                requirement={"challenge_type": "daily", "count": 10},
                reward_points=300,
                emoji="📅",
                category="challenges",
            ),
            "weekly_warrior": Achievement(
                id="weekly_warrior",
                name="Weekly Warrior",
                description="Complete 5 weekly challenges",
                achievement_type=AchievementType.CHALLENGE_COMPLETION,
                requirement={"challenge_type": "weekly", "count": 5},
                reward_points=500,
                emoji="⚔️",
                category="challenges",
            ),
        }

        logger.info(f"Loaded {len(achievements)} achievement definitions")
        return achievements

    async def check_achievements(
        self, user_id: int, context: Dict[str, Any]
    ) -> List[Achievement]:
        """
        Check for newly unlocked achievements based on user context.

        Args:
            user_id: The user's Discord ID
            context: Context data including current stats, recent actions, etc.

        Returns:
            List of newly unlocked achievements
        """
        try:
            # Get user's current achievements to avoid duplicates
            current_achievements = await self.get_user_achievements(user_id)
            current_achievement_ids = {ua.achievement_id for ua in current_achievements}

            newly_unlocked = []

            for achievement_id, achievement in self.achievements.items():
                if achievement_id in current_achievement_ids:
                    continue  # Already unlocked

                if await self._check_achievement_requirement(
                    user_id, achievement, context
                ):
                    # Unlock the achievement
                    if await self.unlock_achievement(user_id, achievement_id):
                        newly_unlocked.append(achievement)
                        logger.info(
                            f"User {user_id} unlocked achievement: {achievement.name}"
                        )

            return newly_unlocked

        except Exception as e:
            logger.error(f"Error checking achievements for user {user_id}: {e}")
            return []

    async def _check_achievement_requirement(
        self, user_id: int, achievement: Achievement, context: Dict[str, Any]
    ) -> bool:
        """Check if a specific achievement requirement is met."""
        try:
            if achievement.achievement_type == AchievementType.STREAK:
                current_streak = context.get("current_streak", 0)
                return current_streak >= achievement.requirement["value"]

            elif achievement.achievement_type == AchievementType.DAILY_STREAK:
                return await self._check_daily_streak_requirement(
                    user_id, achievement.requirement["value"]
                )

            elif achievement.achievement_type == AchievementType.TOTAL_POINTS:
                total_points = context.get("total_points", 0)
                return total_points >= achievement.requirement["value"]

            elif achievement.achievement_type == AchievementType.TOTAL_QUESTIONS:
                questions_answered = context.get("questions_answered", 0)
                return questions_answered >= achievement.requirement["value"]

            elif achievement.achievement_type == AchievementType.ACCURACY:
                questions_answered = context.get("questions_answered", 0)
                questions_correct = context.get("questions_correct", 0)
                min_questions = achievement.requirement.get("min_questions", 1)

                if questions_answered < min_questions:
                    return False

                accuracy = (questions_correct / questions_answered) * 100
                return accuracy >= achievement.requirement["value"]

            elif achievement.achievement_type == AchievementType.DIFFICULTY_MASTER:
                return await self._check_difficulty_master_requirement(
                    user_id, achievement.requirement
                )

            elif achievement.achievement_type == AchievementType.CHALLENGE_COMPLETION:
                return await self._check_challenge_completion_requirement(
                    user_id, achievement.requirement
                )

            return False

        except Exception as e:
            logger.error(
                f"Error checking requirement for achievement {achievement.id}: {e}"
            )
            return False

    async def _check_daily_streak_requirement(
        self, user_id: int, required_days: int
    ) -> bool:
        """Check if user has played trivia for required consecutive days."""
        try:
            async with db_manager.get_connection() as conn:
                # Get the last N days of play activity
                cursor = await conn.execute(
                    """
                    SELECT DISTINCT DATE(last_played) as play_date
                    FROM users 
                    WHERE user_id = ? AND last_played IS NOT NULL
                    ORDER BY play_date DESC
                    LIMIT ?
                """,
                    (user_id, required_days),
                )

                play_dates = [row[0] for row in await cursor.fetchall()]

                if len(play_dates) < required_days:
                    return False

                # Check if dates are consecutive
                today = date.today()
                for i in range(required_days):
                    expected_date = (today - timedelta(days=i)).isoformat()
                    if expected_date not in play_dates:
                        return False

                return True

        except Exception as e:
            logger.error(f"Error checking daily streak for user {user_id}: {e}")
            return False

    async def _check_difficulty_master_requirement(
        self, user_id: int, requirement: Dict[str, Any]
    ) -> bool:
        """Check if user has mastered a specific difficulty level."""
        try:
            difficulty = requirement["difficulty"]
            required_correct = requirement["correct_answers"]

            # This would require tracking difficulty-specific stats
            # For now, we'll implement a basic check
            # In a full implementation, we'd need additional tables to track per-difficulty stats

            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT COUNT(*) FROM game_sessions gs
                    JOIN questions q ON gs.question_id = q.id
                    WHERE gs.user_id = ? AND q.difficulty = ? AND gs.is_completed = TRUE
                """,
                    (user_id, difficulty),
                )

                result = await cursor.fetchone()
                completed_count = result[0] if result else 0

                return completed_count >= required_correct

        except Exception as e:
            logger.error(f"Error checking difficulty master requirement: {e}")
            return False

    async def _check_challenge_completion_requirement(
        self, user_id: int, requirement: Dict[str, Any]
    ) -> bool:
        """Check if user has completed required number of challenges."""
        try:
            challenge_type = requirement["challenge_type"]
            required_count = requirement["count"]

            async with db_manager.get_connection() as conn:
                if challenge_type == "daily":
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(DISTINCT daily_challenge_completed) 
                        FROM users 
                        WHERE user_id = ? AND daily_challenge_completed IS NOT NULL
                    """,
                        (user_id,),
                    )
                elif challenge_type == "weekly":
                    cursor = await conn.execute(
                        """
                        SELECT COUNT(DISTINCT weekly_challenge_completed) 
                        FROM users 
                        WHERE user_id = ? AND weekly_challenge_completed IS NOT NULL
                    """,
                        (user_id,),
                    )
                else:
                    return False

                result = await cursor.fetchone()
                completion_count = result[0] if result else 0

                return completion_count >= required_count

        except Exception as e:
            logger.error(f"Error checking challenge completion requirement: {e}")
            return False

    async def unlock_achievement(self, user_id: int, achievement_id: str) -> bool:
        """
        Unlock an achievement for a user and award bonus points.

        Args:
            user_id: The user's Discord ID
            achievement_id: The achievement to unlock

        Returns:
            True if successfully unlocked, False otherwise
        """
        try:
            if achievement_id not in self.achievements:
                logger.error(f"Unknown achievement ID: {achievement_id}")
                return False

            achievement = self.achievements[achievement_id]

            async with db_manager.get_connection() as conn:
                # Insert the achievement unlock record
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                    VALUES (?, ?)
                """,
                    (user_id, achievement_id),
                )

                # Award bonus points to the user
                await conn.execute(
                    """
                    UPDATE users 
                    SET total_points = total_points + ?
                    WHERE user_id = ?
                """,
                    (achievement.reward_points, user_id),
                )

                await conn.commit()

                # Clear progress cache for this user
                self._progress_cache.pop(user_id, None)

                logger.info(
                    f"Achievement {achievement_id} unlocked for user {user_id}, awarded {achievement.reward_points} points"
                )
                return True

        except Exception as e:
            logger.error(
                f"Error unlocking achievement {achievement_id} for user {user_id}: {e}"
            )
            return False

    async def get_user_achievements(self, user_id: int) -> List[UserAchievement]:
        """Get all achievements unlocked by a user."""
        try:
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, user_id, achievement_id, unlocked_at
                    FROM user_achievements
                    WHERE user_id = ?
                    ORDER BY unlocked_at DESC
                """,
                    (user_id,),
                )

                achievements = []
                for row in await cursor.fetchall():
                    user_achievement = UserAchievement(
                        id=row[0],
                        user_id=row[1],
                        achievement_id=row[2],
                        unlocked_at=datetime.fromisoformat(row[3]),
                        achievement=self.achievements.get(row[2]),
                    )
                    achievements.append(user_achievement)

                return achievements

        except Exception as e:
            logger.error(f"Error getting achievements for user {user_id}: {e}")
            return []

    async def get_achievement_progress(
        self, user_id: int, achievement_id: str
    ) -> Optional[AchievementProgress]:
        """Get progress towards a specific achievement."""
        try:
            if achievement_id not in self.achievements:
                return None

            achievement = self.achievements[achievement_id]

            # Check if already unlocked
            user_achievements = await self.get_user_achievements(user_id)
            if any(ua.achievement_id == achievement_id for ua in user_achievements):
                return AchievementProgress(
                    achievement_id=achievement_id,
                    current_value=achievement.requirement.get("value", 1),
                    required_value=achievement.requirement.get("value", 1),
                    progress_percentage=100.0,
                    is_completed=True,
                )

            # Calculate current progress based on achievement type
            current_value = await self._get_current_progress_value(user_id, achievement)
            required_value = achievement.requirement.get("value", 1)

            progress_percentage = min((current_value / required_value) * 100, 100.0)

            return AchievementProgress(
                achievement_id=achievement_id,
                current_value=current_value,
                required_value=required_value,
                progress_percentage=progress_percentage,
                is_completed=progress_percentage >= 100.0,
            )

        except Exception as e:
            logger.error(
                f"Error getting progress for achievement {achievement_id}: {e}"
            )
            return None

    async def _get_current_progress_value(
        self, user_id: int, achievement: Achievement
    ) -> float:
        """Get the current progress value for an achievement."""
        try:
            async with db_manager.get_connection() as conn:
                if achievement.achievement_type == AchievementType.STREAK:
                    cursor = await conn.execute(
                        "SELECT current_streak FROM users WHERE user_id = ?", (user_id,)
                    )
                    result = await cursor.fetchone()
                    return result[0] if result else 0

                elif achievement.achievement_type == AchievementType.TOTAL_POINTS:
                    cursor = await conn.execute(
                        "SELECT total_points FROM users WHERE user_id = ?", (user_id,)
                    )
                    result = await cursor.fetchone()
                    return result[0] if result else 0

                elif achievement.achievement_type == AchievementType.TOTAL_QUESTIONS:
                    cursor = await conn.execute(
                        "SELECT questions_answered FROM users WHERE user_id = ?",
                        (user_id,),
                    )
                    result = await cursor.fetchone()
                    return result[0] if result else 0

                elif achievement.achievement_type == AchievementType.DAILY_STREAK:
                    # Calculate consecutive days played
                    return await self._calculate_daily_streak(user_id)

                # Add other achievement types as needed
                return 0.0

        except Exception as e:
            logger.error(f"Error getting current progress value: {e}")
            return 0.0

    async def _calculate_daily_streak(self, user_id: int) -> int:
        """Calculate the current daily streak for a user."""
        try:
            async with db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT DISTINCT DATE(last_played) as play_date
                    FROM users 
                    WHERE user_id = ? AND last_played IS NOT NULL
                    ORDER BY play_date DESC
                    LIMIT 365
                """,
                    (user_id,),
                )

                play_dates = [row[0] for row in await cursor.fetchall()]

                if not play_dates:
                    return 0

                # Count consecutive days from today backwards
                today = date.today()
                streak = 0

                for i in range(len(play_dates)):
                    expected_date = (today - timedelta(days=i)).isoformat()
                    if expected_date in play_dates:
                        streak += 1
                    else:
                        break

                return streak

        except Exception as e:
            logger.error(f"Error calculating daily streak: {e}")
            return 0

    async def get_all_achievements(self) -> List[Achievement]:
        """Get all available achievements."""
        return list(self.achievements.values())

    async def get_achievement_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """Get a specific achievement by ID."""
        return self.achievements.get(achievement_id)

    async def get_achievements_by_category(self, category: str) -> List[Achievement]:
        """Get all achievements in a specific category."""
        return [
            achievement
            for achievement in self.achievements.values()
            if achievement.category == category
        ]

    async def get_user_achievement_stats(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive achievement statistics for a user."""
        try:
            user_achievements = await self.get_user_achievements(user_id)
            total_achievements = len(self.achievements)
            unlocked_count = len(user_achievements)

            # Calculate total bonus points earned from achievements
            total_bonus_points = sum(
                self.achievements[ua.achievement_id].reward_points
                for ua in user_achievements
                if ua.achievement_id in self.achievements
            )

            # Group by category
            category_stats = {}
            for achievement in self.achievements.values():
                if achievement.category not in category_stats:
                    category_stats[achievement.category] = {"total": 0, "unlocked": 0}
                category_stats[achievement.category]["total"] += 1

            for user_achievement in user_achievements:
                if user_achievement.achievement_id in self.achievements:
                    category = self.achievements[
                        user_achievement.achievement_id
                    ].category
                    if category in category_stats:
                        category_stats[category]["unlocked"] += 1

            return {
                "total_achievements": total_achievements,
                "unlocked_count": unlocked_count,
                "completion_percentage": (unlocked_count / total_achievements) * 100
                if total_achievements > 0
                else 0,
                "total_bonus_points": total_bonus_points,
                "category_stats": category_stats,
                "recent_achievements": user_achievements[:5],  # Last 5 achievements
            }

        except Exception as e:
            logger.error(f"Error getting achievement stats for user {user_id}: {e}")
            return {}


# Global achievement system instance
achievement_system = AchievementSystem()
