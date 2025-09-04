"""
User management and statistics system for the Enhanced Trivia System.
Handles user profile creation, statistics tracking, and personalization features.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from utils.database import db_manager
from utils.models import UserProfile, UserStats, POINT_VALUES
import aiosqlite

logger = logging.getLogger(__name__)


class UserManager:
    """Manages user profiles, statistics, and personalization features."""

    def __init__(self):
        self.db_manager = db_manager

    async def get_or_create_user(self, user_id: int) -> UserProfile:
        """Get existing user profile or create a new one."""
        try:
            async with self.db_manager.get_connection() as conn:
                # Try to get existing user
                cursor = await conn.execute(
                    """
                    SELECT user_id, total_points, questions_answered, questions_correct,
                           current_streak, best_streak, last_played, daily_challenge_completed,
                           weekly_challenge_completed, preferred_difficulty, created_at
                    FROM users WHERE user_id = ?
                    """,
                    (user_id,),
                )

                row = await cursor.fetchone()

                if row:
                    # Convert row to UserProfile
                    return self._row_to_user_profile(row)
                else:
                    # Create new user
                    return await self._create_new_user(conn, user_id)

        except Exception as e:
            logger.error(f"Error getting/creating user {user_id}: {e}")
            raise

    async def _create_new_user(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> UserProfile:
        """Create a new user profile in the database."""
        now = datetime.now()

        await conn.execute(
            """
            INSERT INTO users (user_id, created_at)
            VALUES (?, ?)
            """,
            (user_id, now),
        )
        await conn.commit()

        logger.info(f"Created new user profile for user {user_id}")

        return UserProfile(user_id=user_id, created_at=now)

    def _row_to_user_profile(self, row: tuple) -> UserProfile:
        """Convert database row to UserProfile object."""
        return UserProfile(
            user_id=row[0],
            total_points=row[1] or 0,
            questions_answered=row[2] or 0,
            questions_correct=row[3] or 0,
            current_streak=row[4] or 0,
            best_streak=row[5] or 0,
            last_played=datetime.fromisoformat(row[6]) if row[6] else None,
            daily_challenge_completed=date.fromisoformat(row[7]) if row[7] else None,
            weekly_challenge_completed=date.fromisoformat(row[8]) if row[8] else None,
            preferred_difficulty=row[9],
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
        )

    async def update_stats(
        self,
        user_id: int,
        points: int,
        is_correct: bool,
        difficulty: str,
        category: str = "general",
    ) -> UserProfile:
        """Update user statistics after answering a question."""
        try:
            async with self.db_manager.get_connection() as conn:
                # Get current user data
                user = await self.get_or_create_user(user_id)

                # Update basic stats
                new_total_points = user.total_points + points
                new_questions_answered = user.questions_answered + 1
                new_questions_correct = user.questions_correct + (
                    1 if is_correct else 0
                )

                # Update streak
                if is_correct:
                    new_current_streak = user.current_streak + 1
                    new_best_streak = max(user.best_streak, new_current_streak)
                else:
                    new_current_streak = 0
                    new_best_streak = user.best_streak

                # Update last played
                now = datetime.now()

                # Update preferred difficulty based on recent performance
                new_preferred_difficulty = await self._calculate_preferred_difficulty(
                    conn, user_id, difficulty, is_correct
                )

                # Update database
                await conn.execute(
                    """
                    UPDATE users SET
                        total_points = ?,
                        questions_answered = ?,
                        questions_correct = ?,
                        current_streak = ?,
                        best_streak = ?,
                        last_played = ?,
                        preferred_difficulty = ?
                    WHERE user_id = ?
                    """,
                    (
                        new_total_points,
                        new_questions_answered,
                        new_questions_correct,
                        new_current_streak,
                        new_best_streak,
                        now,
                        new_preferred_difficulty,
                        user_id,
                    ),
                )
                await conn.commit()

                logger.info(
                    f"Updated stats for user {user_id}: +{points} points, correct={is_correct}"
                )

                # Return updated user profile
                user.total_points = new_total_points
                user.questions_answered = new_questions_answered
                user.questions_correct = new_questions_correct
                user.current_streak = new_current_streak
                user.best_streak = new_best_streak
                user.last_played = now
                user.preferred_difficulty = new_preferred_difficulty

                return user

        except Exception as e:
            logger.error(f"Error updating stats for user {user_id}: {e}")
            raise

    async def _calculate_preferred_difficulty(
        self,
        conn: aiosqlite.Connection,
        user_id: int,
        current_difficulty: str,
        is_correct: bool,
    ) -> Optional[str]:
        """Calculate user's preferred difficulty based on recent performance."""
        try:
            # For now, return the current difficulty if correct, or suggest easier if incorrect
            # This is a simplified version - a full implementation would track game history
            if is_correct:
                return current_difficulty
            else:
                # Suggest easier difficulty if they got it wrong
                if current_difficulty == "hard":
                    return "medium"
                elif current_difficulty == "medium":
                    return "easy"
                else:
                    return "easy"

        except Exception as e:
            logger.error(
                f"Error calculating preferred difficulty for user {user_id}: {e}"
            )
            return None

    async def get_user_stats(self, user_id: int) -> UserStats:
        """Get comprehensive user statistics."""
        try:
            async with self.db_manager.get_connection() as conn:
                # Get user profile
                user_profile = await self.get_or_create_user(user_id)

                # Get points per category
                points_per_category = await self._get_points_per_category(conn, user_id)

                # Get difficulty breakdown
                difficulty_breakdown = await self._get_difficulty_breakdown(
                    conn, user_id
                )

                # Get recent performance (last 10 answers)
                recent_performance = await self._get_recent_performance(conn, user_id)

                # Get achievements count
                achievements_count = await self._get_achievements_count(conn, user_id)

                # Get current rank
                current_rank = await self._get_user_rank(conn, user_id)

                return UserStats(
                    user_profile=user_profile,
                    accuracy_percentage=user_profile.accuracy_percentage,
                    points_per_category=points_per_category,
                    difficulty_breakdown=difficulty_breakdown,
                    recent_performance=recent_performance,
                    achievements_count=achievements_count,
                    current_rank=current_rank,
                )

        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            raise

    async def _get_points_per_category(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Dict[str, int]:
        """Get points earned per category."""
        try:
            cursor = await conn.execute(
                """
                SELECT q.category, SUM(
                    CASE 
                        WHEN q.difficulty = 'easy' THEN 10
                        WHEN q.difficulty = 'medium' THEN 20
                        WHEN q.difficulty = 'hard' THEN 30
                        ELSE 0
                    END
                ) as points
                FROM game_sessions gs
                JOIN questions q ON gs.question_id = q.id
                WHERE gs.user_id = ? AND gs.is_completed = 1
                  AND EXISTS (
                      SELECT 1 FROM users u 
                      WHERE u.user_id = gs.user_id 
                      AND gs.end_time <= u.last_played
                  )
                GROUP BY q.category
                """,
                (user_id,),
            )

            rows = await cursor.fetchall()
            return {category: points for category, points in rows}

        except Exception as e:
            logger.error(f"Error getting points per category for user {user_id}: {e}")
            return {}

    async def _get_difficulty_breakdown(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Dict[str, Dict[str, int]]:
        """Get performance breakdown by difficulty."""
        try:
            cursor = await conn.execute(
                """
                SELECT q.difficulty,
                       COUNT(*) as total,
                       SUM(CASE WHEN gs.is_completed = 1 THEN 1 ELSE 0 END) as completed,
                       SUM(
                           CASE 
                               WHEN q.difficulty = 'easy' AND gs.is_completed = 1 THEN 10
                               WHEN q.difficulty = 'medium' AND gs.is_completed = 1 THEN 20
                               WHEN q.difficulty = 'hard' AND gs.is_completed = 1 THEN 30
                               ELSE 0
                           END
                       ) as points
                FROM game_sessions gs
                JOIN questions q ON gs.question_id = q.id
                WHERE gs.user_id = ?
                GROUP BY q.difficulty
                """,
                (user_id,),
            )

            rows = await cursor.fetchall()
            breakdown = {}

            for difficulty, total, completed, points in rows:
                breakdown[difficulty] = {
                    "total": total,
                    "correct": completed,
                    "points": points,
                    "accuracy": (completed / total * 100) if total > 0 else 0,
                }

            return breakdown

        except Exception as e:
            logger.error(f"Error getting difficulty breakdown for user {user_id}: {e}")
            return {}

    async def _get_recent_performance(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> List[bool]:
        """Get recent performance (last 10 answers)."""
        try:
            cursor = await conn.execute(
                """
                SELECT is_completed
                FROM game_sessions
                WHERE user_id = ? AND question_id IS NOT NULL
                ORDER BY end_time DESC
                LIMIT 10
                """,
                (user_id,),
            )

            rows = await cursor.fetchall()
            return [bool(row[0]) for row in rows]

        except Exception as e:
            logger.error(f"Error getting recent performance for user {user_id}: {e}")
            return []

    async def _get_achievements_count(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> int:
        """Get total number of achievements earned."""
        try:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM user_achievements WHERE user_id = ?", (user_id,)
            )

            result = await cursor.fetchone()
            return result[0] if result else 0

        except Exception as e:
            logger.error(f"Error getting achievements count for user {user_id}: {e}")
            return 0

    async def _get_user_rank(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Optional[int]:
        """Get user's current rank in the leaderboard."""
        try:
            cursor = await conn.execute(
                """
                SELECT rank FROM (
                    SELECT user_id, 
                           ROW_NUMBER() OVER (ORDER BY total_points DESC) as rank
                    FROM users
                    WHERE total_points > 0
                ) ranked_users
                WHERE user_id = ?
                """,
                (user_id,),
            )

            result = await cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            logger.error(f"Error getting rank for user {user_id}: {e}")
            return None

    async def update_streak(self, user_id: int, is_correct: bool) -> int:
        """Update user's streak and return new streak value."""
        try:
            user = await self.get_or_create_user(user_id)

            if is_correct:
                new_streak = user.current_streak + 1
            else:
                new_streak = 0

            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE users SET 
                        current_streak = ?,
                        best_streak = CASE 
                            WHEN ? > best_streak THEN ?
                            ELSE best_streak
                        END
                    WHERE user_id = ?
                    """,
                    (new_streak, new_streak, new_streak, user_id),
                )
                await conn.commit()

            return new_streak

        except Exception as e:
            logger.error(f"Error updating streak for user {user_id}: {e}")
            raise

    async def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get user's current rank in the overall leaderboard."""
        try:
            async with self.db_manager.get_connection() as conn:
                return await self._get_user_rank(conn, user_id)
        except Exception as e:
            logger.error(f"Error getting rank for user {user_id}: {e}")
            return None

    async def reset_user_stats(self, user_id: int) -> bool:
        """Reset user's statistics (admin function)."""
        try:
            async with self.db_manager.get_connection() as conn:
                # Reset user stats but keep profile
                await conn.execute(
                    """
                    UPDATE users SET
                        total_points = 0,
                        questions_answered = 0,
                        questions_correct = 0,
                        current_streak = 0,
                        best_streak = 0,
                        daily_challenge_completed = NULL,
                        weekly_challenge_completed = NULL
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )

                # Remove achievements
                await conn.execute(
                    "DELETE FROM user_achievements WHERE user_id = ?", (user_id,)
                )

                # Remove game sessions
                await conn.execute(
                    "DELETE FROM game_sessions WHERE user_id = ?", (user_id,)
                )

                await conn.commit()
                logger.info(f"Reset stats for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Error resetting stats for user {user_id}: {e}")
            return False

    async def update_challenge_completion(
        self, user_id: int, challenge_type: str
    ) -> bool:
        """Update challenge completion status."""
        try:
            async with self.db_manager.get_connection() as conn:
                today = date.today()

                if challenge_type == "daily":
                    await conn.execute(
                        "UPDATE users SET daily_challenge_completed = ? WHERE user_id = ?",
                        (today, user_id),
                    )
                elif challenge_type == "weekly":
                    await conn.execute(
                        "UPDATE users SET weekly_challenge_completed = ? WHERE user_id = ?",
                        (today, user_id),
                    )
                else:
                    return False

                await conn.commit()
                return True

        except Exception as e:
            logger.error(f"Error updating challenge completion for user {user_id}: {e}")
            return False

    async def can_attempt_challenge(self, user_id: int, challenge_type: str) -> bool:
        """Check if user can attempt a challenge."""
        try:
            user = await self.get_or_create_user(user_id)
            today = date.today()

            if challenge_type == "daily":
                return user.daily_challenge_completed != today
            elif challenge_type == "weekly":
                # Check if it's a new week (Monday start)
                if user.weekly_challenge_completed is None:
                    return True

                # Get the Monday of current week
                days_since_monday = today.weekday()
                current_week_start = today - timedelta(days=days_since_monday)

                # Get the Monday of the week when challenge was completed
                completed_date = user.weekly_challenge_completed
                completed_days_since_monday = completed_date.weekday()
                completed_week_start = completed_date - timedelta(
                    days=completed_days_since_monday
                )

                return current_week_start > completed_week_start

            return False

        except Exception as e:
            logger.error(
                f"Error checking challenge availability for user {user_id}: {e}"
            )
            return False

    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences and personalization data."""
        try:
            user = await self.get_or_create_user(user_id)
            stats = await self.get_user_stats(user_id)

            # Analyze weak areas (categories with low accuracy)
            weak_areas = []
            for category, breakdown in stats.difficulty_breakdown.items():
                if breakdown.get("total", 0) >= 5 and breakdown.get("accuracy", 0) < 60:
                    weak_areas.append(category)

            # Suggest next goals based on current performance
            next_goals = []
            if user.current_streak >= 3:
                next_goals.append(
                    "Reach a 5-question streak for the Hot Streak achievement!"
                )
            if user.questions_correct >= 50 and user.accuracy_percentage >= 85:
                next_goals.append(
                    "Try some hard difficulty questions to boost your points!"
                )
            if stats.achievements_count < 3:
                next_goals.append("Unlock more achievements by playing consistently!")

            return {
                "preferred_difficulty": user.preferred_difficulty,
                "weak_areas": weak_areas,
                "next_goals": next_goals,
                "play_streak_days": self._calculate_play_streak(user),
                "favorite_categories": self._get_favorite_categories(
                    stats.points_per_category
                ),
            }

        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            return {}

    def _calculate_play_streak(self, user: UserProfile) -> int:
        """Calculate consecutive days played (simplified version)."""
        if not user.last_played:
            return 0

        days_since_last_play = (datetime.now().date() - user.last_played.date()).days

        # If played today or yesterday, assume streak continues
        # This is a simplified version - a full implementation would track daily play
        if days_since_last_play <= 1:
            return max(1, user.current_streak // 3)  # Rough estimate
        else:
            return 0

    def _get_favorite_categories(
        self, points_per_category: Dict[str, int]
    ) -> List[str]:
        """Get user's favorite categories based on points earned."""
        if not points_per_category:
            return []

        # Sort categories by points and return top 3
        sorted_categories = sorted(
            points_per_category.items(), key=lambda x: x[1], reverse=True
        )
        return [category for category, _ in sorted_categories[:3]]


# Global user manager instance
user_manager = UserManager()
