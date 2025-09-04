"""
Achievement integration utilities for the Enhanced Trivia System.
Provides integration between trivia gameplay and achievement checking.
"""

import logging
from typing import Dict, Any, List, Optional
import discord

from .achievement_system import achievement_system, Achievement
from .achievement_notifications import notification_system
from .user_manager import user_manager

logger = logging.getLogger(__name__)


class AchievementIntegration:
    """Handles integration between trivia gameplay and achievement system."""

    def __init__(self):
        self.achievement_system = achievement_system
        self.notification_system = notification_system

    async def check_and_notify_achievements(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        context: Dict[str, Any],
    ) -> List[Achievement]:
        """
        Check for new achievements and send notifications.

        Args:
            channel: Discord channel to send notifications to
            user: The Discord member
            context: Context data for achievement checking

        Returns:
            List of newly unlocked achievements
        """
        try:
            # Check for newly unlocked achievements
            new_achievements = await self.achievement_system.check_achievements(
                user.id, context
            )

            # Send notifications for new achievements
            if new_achievements:
                await self.notification_system.send_achievement_notification(
                    channel, user, new_achievements
                )
                logger.info(
                    f"User {user.display_name} unlocked {len(new_achievements)} achievements"
                )

            return new_achievements

        except Exception as e:
            logger.error(
                f"Error checking achievements for user {user.display_name}: {e}"
            )
            return []

    async def create_trivia_result_context(
        self,
        user_id: int,
        is_correct: bool,
        difficulty: str = "medium",
        points_earned: int = 0,
    ) -> Dict[str, Any]:
        """
        Create context data for achievement checking after a trivia answer.

        Args:
            user_id: The user's Discord ID
            is_correct: Whether the answer was correct
            difficulty: The question difficulty
            points_earned: Points earned from the question

        Returns:
            Context dictionary for achievement checking
        """
        try:
            # Get current user stats
            user_stats = await user_manager.get_user_stats(user_id)
            user_profile = await user_manager.get_or_create_user(user_id)

            context = {
                "is_correct": is_correct,
                "difficulty": difficulty,
                "points_earned": points_earned,
                "total_points": user_profile.total_points,
                "questions_answered": user_profile.questions_answered,
                "questions_correct": user_profile.questions_correct,
                "current_streak": user_profile.current_streak,
                "best_streak": user_profile.best_streak,
                "accuracy": user_stats.accuracy_percentage if user_stats else 0.0,
                "last_played": user_profile.last_played,
                "daily_challenge_completed": user_profile.daily_challenge_completed,
                "weekly_challenge_completed": user_profile.weekly_challenge_completed,
            }

            return context

        except Exception as e:
            logger.error(
                f"Error creating trivia result context for user {user_id}: {e}"
            )
            return {}

    async def handle_trivia_answer(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        is_correct: bool,
        difficulty: str = "medium",
        points_earned: int = 0,
    ) -> List[Achievement]:
        """
        Handle a trivia answer and check for achievements.

        Args:
            channel: Discord channel where the trivia was played
            user: The Discord member who answered
            is_correct: Whether the answer was correct
            difficulty: The question difficulty
            points_earned: Points earned from the question

        Returns:
            List of newly unlocked achievements
        """
        try:
            # Update user stats first
            await user_manager.update_stats(
                user.id, points_earned, is_correct, difficulty
            )

            # Create context for achievement checking
            context = await self.create_trivia_result_context(
                user.id, is_correct, difficulty, points_earned
            )

            # Check and notify achievements
            new_achievements = await self.check_and_notify_achievements(
                channel, user, context
            )

            return new_achievements

        except Exception as e:
            logger.error(
                f"Error handling trivia answer for user {user.display_name}: {e}"
            )
            return []

    async def handle_daily_challenge_completion(
        self, channel: discord.TextChannel, user: discord.Member, points_earned: int
    ) -> List[Achievement]:
        """
        Handle daily challenge completion and check for related achievements.

        Args:
            channel: Discord channel where the challenge was completed
            user: The Discord member who completed the challenge
            points_earned: Points earned from the challenge

        Returns:
            List of newly unlocked achievements
        """
        try:
            # Create context for daily challenge completion
            context = await self.create_trivia_result_context(
                user.id, True, "medium", points_earned
            )
            context["challenge_completed"] = "daily"

            # Check and notify achievements
            new_achievements = await self.check_and_notify_achievements(
                channel, user, context
            )

            return new_achievements

        except Exception as e:
            logger.error(
                f"Error handling daily challenge completion for user {user.display_name}: {e}"
            )
            return []

    async def handle_weekly_challenge_completion(
        self, channel: discord.TextChannel, user: discord.Member, points_earned: int
    ) -> List[Achievement]:
        """
        Handle weekly challenge completion and check for related achievements.

        Args:
            channel: Discord channel where the challenge was completed
            user: The Discord member who completed the challenge
            points_earned: Points earned from the challenge

        Returns:
            List of newly unlocked achievements
        """
        try:
            # Create context for weekly challenge completion
            context = await self.create_trivia_result_context(
                user.id, True, "hard", points_earned
            )
            context["challenge_completed"] = "weekly"

            # Check and notify achievements
            new_achievements = await self.check_and_notify_achievements(
                channel, user, context
            )

            return new_achievements

        except Exception as e:
            logger.error(
                f"Error handling weekly challenge completion for user {user.display_name}: {e}"
            )
            return []

    async def get_user_achievement_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Get a comprehensive achievement summary for a user.

        Args:
            user_id: The user's Discord ID

        Returns:
            Dictionary containing achievement summary data
        """
        try:
            # Get user achievements and stats
            user_achievements = await self.achievement_system.get_user_achievements(
                user_id
            )
            achievement_stats = (
                await self.achievement_system.get_user_achievement_stats(user_id)
            )

            # Get progress on incomplete achievements
            incomplete_achievements = []
            for (
                achievement_id,
                achievement,
            ) in self.achievement_system.achievements.items():
                if not any(
                    ua.achievement_id == achievement_id for ua in user_achievements
                ):
                    progress = await self.achievement_system.get_achievement_progress(
                        user_id, achievement_id
                    )
                    if progress and progress.progress_percentage > 0:
                        incomplete_achievements.append(
                            {"achievement": achievement, "progress": progress}
                        )

            # Sort incomplete achievements by progress percentage
            incomplete_achievements.sort(
                key=lambda x: x["progress"].progress_percentage, reverse=True
            )

            return {
                "user_achievements": user_achievements,
                "achievement_stats": achievement_stats,
                "incomplete_achievements": incomplete_achievements[
                    :5
                ],  # Top 5 closest to completion
                "total_bonus_points": sum(
                    self.achievement_system.achievements[
                        ua.achievement_id
                    ].reward_points
                    for ua in user_achievements
                    if ua.achievement_id in self.achievement_system.achievements
                ),
            }

        except Exception as e:
            logger.error(f"Error getting achievement summary for user {user_id}: {e}")
            return {}


# Global achievement integration instance
achievement_integration = AchievementIntegration()
