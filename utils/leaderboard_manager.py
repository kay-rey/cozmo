"""
Leaderboard management system for the Enhanced Trivia System.
Handles leaderboard calculation, caching, and ranking operations with weekly/monthly periods.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from utils.database import db_manager
from utils.models import LeaderboardEntry, UserProfile
import aiosqlite
import asyncio

logger = logging.getLogger(__name__)


class LeaderboardManager:
    """Manages leaderboard calculations, caching, and ranking operations."""

    def __init__(self):
        self.db_manager = db_manager
        self._cache = {}
        self._cache_expiry = {}
        self.cache_duration = 300  # 5 minutes in seconds

    async def get_leaderboard(
        self,
        period: str = "all_time",
        limit: int = 10,
        offset: int = 0,
        user_context: Optional[int] = None,
    ) -> List[LeaderboardEntry]:
        """
        Get leaderboard entries for specified period.

        Args:
            period: "all_time", "weekly", or "monthly"
            limit: Number of entries to return
            offset: Offset for pagination
            user_context: If provided, include user's position even if not in top results
        """
        try:
            cache_key = f"leaderboard_{period}_{limit}_{offset}"

            # Check cache first
            if self._is_cache_valid(cache_key):
                cached_result = self._cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Returning cached leaderboard for {period}")
                    return cached_result

            async with self.db_manager.get_connection() as conn:
                if period == "all_time":
                    entries = await self._get_all_time_leaderboard(conn, limit, offset)
                elif period == "weekly":
                    entries = await self._get_weekly_leaderboard(conn, limit, offset)
                elif period == "monthly":
                    entries = await self._get_monthly_leaderboard(conn, limit, offset)
                else:
                    raise ValueError(f"Invalid period: {period}")

                # Cache the result
                self._cache[cache_key] = entries
                self._cache_expiry[cache_key] = datetime.now() + timedelta(
                    seconds=self.cache_duration
                )

                # If user_context provided and user not in results, add their position
                if user_context and not any(
                    entry.user_id == user_context for entry in entries
                ):
                    user_entry = await self._get_user_position(
                        conn, user_context, period
                    )
                    if user_entry:
                        entries.append(user_entry)

                return entries

        except Exception as e:
            logger.error(f"Error getting leaderboard for period {period}: {e}")
            raise

    async def _get_all_time_leaderboard(
        self, conn: aiosqlite.Connection, limit: int, offset: int
    ) -> List[LeaderboardEntry]:
        """Get all-time leaderboard based on total points."""
        cursor = await conn.execute(
            """
            SELECT 
                ROW_NUMBER() OVER (ORDER BY total_points DESC) as rank,
                user_id,
                total_points,
                questions_answered,
                questions_correct,
                current_streak,
                CASE 
                    WHEN questions_answered > 0 
                    THEN ROUND((questions_correct * 100.0) / questions_answered, 1)
                    ELSE 0.0
                END as accuracy_percentage
            FROM users
            WHERE total_points > 0
            ORDER BY total_points DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        rows = await cursor.fetchall()
        return [
            LeaderboardEntry(
                rank=row[0],
                user_id=row[1],
                username=f"User#{row[1]}",  # Will be updated with actual username
                total_points=row[2],
                accuracy_percentage=row[6],
                questions_answered=row[3],
                current_streak=row[5],
            )
            for row in rows
        ]

    async def _get_weekly_leaderboard(
        self, conn: aiosqlite.Connection, limit: int, offset: int
    ) -> List[LeaderboardEntry]:
        """Get weekly leaderboard for current week."""
        week_start = self._get_week_start()

        # First, ensure weekly rankings are up to date
        await self._update_weekly_rankings(conn, week_start)

        cursor = await conn.execute(
            """
            SELECT 
                wr.rank,
                wr.user_id,
                wr.points,
                u.questions_answered,
                u.questions_correct,
                u.current_streak,
                CASE 
                    WHEN u.questions_answered > 0 
                    THEN ROUND((u.questions_correct * 100.0) / u.questions_answered, 1)
                    ELSE 0.0
                END as accuracy_percentage
            FROM weekly_rankings wr
            JOIN users u ON wr.user_id = u.user_id
            WHERE wr.week_start = ? AND wr.points > 0
            ORDER BY wr.rank
            LIMIT ? OFFSET ?
            """,
            (week_start, limit, offset),
        )

        rows = await cursor.fetchall()
        return [
            LeaderboardEntry(
                rank=row[0],
                user_id=row[1],
                username=f"User#{row[1]}",
                total_points=row[2],
                accuracy_percentage=row[6],
                questions_answered=row[3],
                current_streak=row[5],
            )
            for row in rows
        ]

    async def _get_monthly_leaderboard(
        self, conn: aiosqlite.Connection, limit: int, offset: int
    ) -> List[LeaderboardEntry]:
        """Get monthly leaderboard for current month."""
        month_start = date.today().replace(day=1)

        cursor = await conn.execute(
            """
            SELECT 
                ROW_NUMBER() OVER (ORDER BY monthly_points DESC) as rank,
                user_id,
                monthly_points,
                questions_answered,
                questions_correct,
                current_streak,
                accuracy_percentage
            FROM (
                SELECT 
                    u.user_id,
                    u.questions_answered,
                    u.questions_correct,
                    u.current_streak,
                    CASE 
                        WHEN u.questions_answered > 0 
                        THEN ROUND((u.questions_correct * 100.0) / u.questions_answered, 1)
                        ELSE 0.0
                    END as accuracy_percentage,
                    COALESCE(SUM(
                        CASE q.difficulty
                            WHEN 'easy' THEN 10
                            WHEN 'medium' THEN 20
                            WHEN 'hard' THEN 30
                            ELSE 0
                        END
                    ), 0) as monthly_points
                FROM users u
                LEFT JOIN game_sessions gs ON u.user_id = gs.user_id 
                    AND gs.is_completed = 1 
                    AND DATE(gs.end_time) >= ?
                LEFT JOIN questions q ON gs.question_id = q.id
                GROUP BY u.user_id, u.questions_answered, u.questions_correct, u.current_streak
            ) monthly_stats
            WHERE monthly_points > 0
            ORDER BY monthly_points DESC
            LIMIT ? OFFSET ?
            """,
            (month_start, limit, offset),
        )

        rows = await cursor.fetchall()
        return [
            LeaderboardEntry(
                rank=row[0],
                user_id=row[1],
                username=f"User#{row[1]}",
                total_points=row[2],
                accuracy_percentage=row[6],
                questions_answered=row[3],
                current_streak=row[5],
            )
            for row in rows
        ]

    async def get_user_rank(
        self, user_id: int, period: str = "all_time"
    ) -> Optional[Tuple[int, int]]:
        """
        Get user's rank and total participants for specified period.

        Returns:
            Tuple of (rank, total_participants) or None if user not found
        """
        try:
            async with self.db_manager.get_connection() as conn:
                if period == "all_time":
                    return await self._get_user_all_time_rank(conn, user_id)
                elif period == "weekly":
                    return await self._get_user_weekly_rank(conn, user_id)
                elif period == "monthly":
                    return await self._get_user_monthly_rank(conn, user_id)
                else:
                    raise ValueError(f"Invalid period: {period}")

        except Exception as e:
            logger.error(f"Error getting rank for user {user_id}, period {period}: {e}")
            return None

    async def _get_user_all_time_rank(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Optional[Tuple[int, int]]:
        """Get user's all-time rank."""
        # Get user's rank
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

        rank_result = await cursor.fetchone()
        if not rank_result:
            return None

        # Get total participants
        cursor = await conn.execute("SELECT COUNT(*) FROM users WHERE total_points > 0")
        total_result = await cursor.fetchone()

        return (rank_result[0], total_result[0])

    async def _get_user_weekly_rank(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Optional[Tuple[int, int]]:
        """Get user's weekly rank."""
        week_start = self._get_week_start()
        await self._update_weekly_rankings(conn, week_start)

        cursor = await conn.execute(
            """
            SELECT rank FROM weekly_rankings 
            WHERE user_id = ? AND week_start = ?
            """,
            (user_id, week_start),
        )

        rank_result = await cursor.fetchone()
        if not rank_result:
            return None

        # Get total weekly participants
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM weekly_rankings WHERE week_start = ? AND points > 0",
            (week_start,),
        )
        total_result = await cursor.fetchone()

        return (rank_result[0], total_result[0])

    async def _get_user_monthly_rank(
        self, conn: aiosqlite.Connection, user_id: int
    ) -> Optional[Tuple[int, int]]:
        """Get user's monthly rank."""
        month_start = date.today().replace(day=1)

        cursor = await conn.execute(
            """
            SELECT rank, total_participants FROM (
                SELECT 
                    user_id,
                    ROW_NUMBER() OVER (ORDER BY monthly_points DESC) as rank,
                    COUNT(*) OVER () as total_participants
                FROM (
                    SELECT 
                        u.user_id,
                        COALESCE(SUM(
                            CASE q.difficulty
                                WHEN 'easy' THEN 10
                                WHEN 'medium' THEN 20
                                WHEN 'hard' THEN 30
                                ELSE 0
                            END
                        ), 0) as monthly_points
                    FROM users u
                    LEFT JOIN game_sessions gs ON u.user_id = gs.user_id 
                        AND gs.is_completed = 1 
                        AND DATE(gs.end_time) >= ?
                    LEFT JOIN questions q ON gs.question_id = q.id
                    GROUP BY u.user_id
                ) monthly_stats
                WHERE monthly_points > 0
            ) ranked_monthly
            WHERE user_id = ?
            """,
            (month_start, user_id),
        )

        result = await cursor.fetchone()
        return (result[0], result[1]) if result else None

    async def _get_user_position(
        self, conn: aiosqlite.Connection, user_id: int, period: str
    ) -> Optional[LeaderboardEntry]:
        """Get user's position entry for leaderboard context."""
        rank_info = await self.get_user_rank(user_id, period)
        if not rank_info:
            return None

        rank, _ = rank_info

        # Get user details
        cursor = await conn.execute(
            """
            SELECT total_points, questions_answered, questions_correct, current_streak
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        )

        user_data = await cursor.fetchone()
        if not user_data:
            return None

        accuracy = (user_data[2] / user_data[1] * 100) if user_data[1] > 0 else 0.0

        return LeaderboardEntry(
            rank=rank,
            user_id=user_id,
            username=f"User#{user_id}",
            total_points=user_data[0],
            accuracy_percentage=accuracy,
            questions_answered=user_data[1],
            current_streak=user_data[3],
        )

    async def update_weekly_rankings(self) -> None:
        """Update weekly rankings for current week."""
        try:
            async with self.db_manager.get_connection() as conn:
                week_start = self._get_week_start()
                await self._update_weekly_rankings(conn, week_start)
                logger.info(f"Updated weekly rankings for week starting {week_start}")

        except Exception as e:
            logger.error(f"Error updating weekly rankings: {e}")
            raise

    async def _update_weekly_rankings(
        self, conn: aiosqlite.Connection, week_start: date
    ) -> None:
        """Update weekly rankings table for specified week."""
        # Calculate weekly points for all users
        cursor = await conn.execute(
            """
            SELECT 
                u.user_id,
                COALESCE(SUM(
                    CASE q.difficulty
                        WHEN 'easy' THEN 10
                        WHEN 'medium' THEN 20
                        WHEN 'hard' THEN 30
                        ELSE 0
                    END
                ), 0) as weekly_points
            FROM users u
            LEFT JOIN game_sessions gs ON u.user_id = gs.user_id 
                AND gs.is_completed = 1 
                AND DATE(gs.end_time) >= ? 
                AND DATE(gs.end_time) < ?
            LEFT JOIN questions q ON gs.question_id = q.id
            GROUP BY u.user_id
            """,
            (week_start, week_start + timedelta(days=7)),
        )

        weekly_data = await cursor.fetchall()

        # Sort by points and assign ranks
        sorted_data = sorted(weekly_data, key=lambda x: x[1], reverse=True)

        # Update or insert weekly rankings
        for rank, (user_id, points) in enumerate(sorted_data, 1):
            if points > 0:  # Only include users with points
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO weekly_rankings 
                    (user_id, week_start, points, rank)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, week_start, points, rank),
                )

        await conn.commit()

    async def reset_weekly_rankings(self) -> None:
        """Reset weekly rankings (called at start of new week)."""
        try:
            async with self.db_manager.get_connection() as conn:
                # Archive old rankings (keep for historical data)
                # For now, we just ensure current week is calculated
                week_start = self._get_week_start()
                await self._update_weekly_rankings(conn, week_start)

                # Clear cache
                self._clear_cache()

                logger.info("Weekly rankings reset completed")

        except Exception as e:
            logger.error(f"Error resetting weekly rankings: {e}")
            raise

    def _get_week_start(self) -> date:
        """Get the start date of current week (Monday)."""
        today = date.today()
        days_since_monday = today.weekday()
        return today - timedelta(days=days_since_monday)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]

    def _clear_cache(self) -> None:
        """Clear all cached leaderboard data."""
        self._cache.clear()
        self._cache_expiry.clear()
        logger.debug("Leaderboard cache cleared")

    async def get_nearby_ranks(
        self, user_id: int, period: str = "all_time", context_size: int = 2
    ) -> List[LeaderboardEntry]:
        """
        Get users ranked near the specified user.

        Args:
            user_id: Target user ID
            period: Leaderboard period
            context_size: Number of users above and below to include
        """
        try:
            rank_info = await self.get_user_rank(user_id, period)
            if not rank_info:
                return []

            user_rank, total_participants = rank_info

            # Calculate range
            start_rank = max(1, user_rank - context_size)
            end_rank = min(total_participants, user_rank + context_size)

            # Get entries in range
            offset = start_rank - 1
            limit = end_rank - start_rank + 1

            return await self.get_leaderboard(period, limit, offset)

        except Exception as e:
            logger.error(f"Error getting nearby ranks for user {user_id}: {e}")
            return []

    async def get_rank_change(
        self, user_id: int, period: str = "weekly"
    ) -> Optional[int]:
        """
        Get user's rank change compared to previous period.

        Returns:
            Positive number for rank improvement, negative for decline, None if no data
        """
        try:
            if period != "weekly":
                return None  # Only implemented for weekly for now

            async with self.db_manager.get_connection() as conn:
                current_week = self._get_week_start()
                previous_week = current_week - timedelta(days=7)

                # Get current and previous ranks
                cursor = await conn.execute(
                    """
                    SELECT 
                        curr.rank as current_rank,
                        prev.rank as previous_rank
                    FROM weekly_rankings curr
                    LEFT JOIN weekly_rankings prev ON curr.user_id = prev.user_id 
                        AND prev.week_start = ?
                    WHERE curr.user_id = ? AND curr.week_start = ?
                    """,
                    (previous_week, user_id, current_week),
                )

                result = await cursor.fetchone()
                if not result or not result[1]:  # No previous rank data
                    return None

                # Rank change is previous - current (positive = improvement)
                return result[1] - result[0]

        except Exception as e:
            logger.error(f"Error getting rank change for user {user_id}: {e}")
            return None


# Global leaderboard manager instance
leaderboard_manager = LeaderboardManager()
