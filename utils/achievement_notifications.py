"""
Achievement notification system for Discord embeds and user notifications.
Handles formatting and sending achievement unlock notifications.
"""

import discord
import logging
from typing import List, Optional
from datetime import datetime

from .achievement_system import Achievement, UserAchievement

logger = logging.getLogger(__name__)


class AchievementNotificationSystem:
    """Handles achievement notifications and Discord embed formatting."""

    def __init__(self):
        self.notification_color = 0xFFD700  # Gold color for achievements

    def create_achievement_unlock_embed(
        self, user: discord.Member, achievement: Achievement
    ) -> discord.Embed:
        """
        Create a Discord embed for achievement unlock notification.

        Args:
            user: The Discord member who unlocked the achievement
            achievement: The achievement that was unlocked

        Returns:
            Discord embed for the achievement notification
        """
        embed = discord.Embed(
            title="🏆 Achievement Unlocked!",
            description=f"**{user.display_name}** has unlocked a new achievement!",
            color=self.notification_color,
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name=f"{achievement.emoji} {achievement.name}",
            value=achievement.description,
            inline=False,
        )

        embed.add_field(
            name="💰 Bonus Points",
            value=f"+{achievement.reward_points} points",
            inline=True,
        )

        embed.add_field(
            name="📂 Category", value=achievement.category.title(), inline=True
        )

        embed.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )
        embed.set_footer(text="Keep playing to unlock more achievements!")

        return embed

    def create_multiple_achievements_embed(
        self, user: discord.Member, achievements: List[Achievement]
    ) -> discord.Embed:
        """
        Create a Discord embed for multiple achievement unlocks.

        Args:
            user: The Discord member who unlocked the achievements
            achievements: List of achievements that were unlocked

        Returns:
            Discord embed for multiple achievement notifications
        """
        total_bonus_points = sum(
            achievement.reward_points for achievement in achievements
        )

        embed = discord.Embed(
            title="🎉 Multiple Achievements Unlocked!",
            description=f"**{user.display_name}** has unlocked {len(achievements)} achievements!",
            color=self.notification_color,
            timestamp=datetime.utcnow(),
        )

        # Add each achievement as a field
        for achievement in achievements[:5]:  # Limit to 5 to avoid embed limits
            embed.add_field(
                name=f"{achievement.emoji} {achievement.name}",
                value=f"{achievement.description}\n💰 +{achievement.reward_points} points",
                inline=False,
            )

        if len(achievements) > 5:
            embed.add_field(
                name="And more...",
                value=f"+{len(achievements) - 5} additional achievements!",
                inline=False,
            )

        embed.add_field(
            name="💰 Total Bonus Points",
            value=f"+{total_bonus_points} points",
            inline=True,
        )

        embed.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )
        embed.set_footer(text="Amazing progress! Keep it up!")

        return embed

    def create_achievements_list_embed(
        self,
        user: discord.Member,
        user_achievements: List[UserAchievement],
        page: int = 1,
        per_page: int = 10,
    ) -> discord.Embed:
        """
        Create a Discord embed showing a user's achievements list.

        Args:
            user: The Discord member
            user_achievements: List of user's achievements
            page: Current page number
            per_page: Number of achievements per page

        Returns:
            Discord embed showing the achievements list
        """
        total_achievements = len(user_achievements)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_achievements = user_achievements[start_idx:end_idx]

        embed = discord.Embed(
            title=f"🏆 {user.display_name}'s Achievements",
            description=f"Showing {len(page_achievements)} of {total_achievements} achievements",
            color=self.notification_color,
            timestamp=datetime.utcnow(),
        )

        if not page_achievements:
            embed.add_field(
                name="No Achievements Yet",
                value="Start playing trivia to unlock your first achievement!",
                inline=False,
            )
        else:
            for user_achievement in page_achievements:
                if user_achievement.achievement:
                    achievement = user_achievement.achievement
                    unlock_date = user_achievement.unlocked_at.strftime("%B %d, %Y")

                    embed.add_field(
                        name=f"{achievement.emoji} {achievement.name}",
                        value=f"{achievement.description}\n📅 Unlocked: {unlock_date}\n💰 {achievement.reward_points} points",
                        inline=False,
                    )

        # Add pagination info if needed
        total_pages = (total_achievements + per_page - 1) // per_page
        if total_pages > 1:
            embed.set_footer(
                text=f"Page {page} of {total_pages} • Use reactions to navigate"
            )

        embed.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )

        return embed

    def create_achievement_progress_embed(
        self,
        user: discord.Member,
        achievement: Achievement,
        current_value: float,
        required_value: float,
    ) -> discord.Embed:
        """
        Create a Discord embed showing progress towards an achievement.

        Args:
            user: The Discord member
            achievement: The achievement to show progress for
            current_value: Current progress value
            required_value: Required value to unlock

        Returns:
            Discord embed showing achievement progress
        """
        progress_percentage = min((current_value / required_value) * 100, 100.0)
        progress_bar = self._create_progress_bar(progress_percentage)

        embed = discord.Embed(
            title=f"📊 Achievement Progress",
            description=f"**{user.display_name}**'s progress towards **{achievement.name}**",
            color=0x3498DB,  # Blue color for progress
            timestamp=datetime.utcnow(),
        )

        embed.add_field(
            name=f"{achievement.emoji} {achievement.name}",
            value=achievement.description,
            inline=False,
        )

        embed.add_field(
            name="Progress",
            value=f"{progress_bar}\n{current_value:.0f} / {required_value:.0f} ({progress_percentage:.1f}%)",
            inline=False,
        )

        embed.add_field(
            name="💰 Reward",
            value=f"{achievement.reward_points} bonus points",
            inline=True,
        )

        embed.add_field(
            name="📂 Category", value=achievement.category.title(), inline=True
        )

        embed.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )

        return embed

    def create_achievement_categories_embed(
        self, user: discord.Member, category_stats: dict
    ) -> discord.Embed:
        """
        Create a Discord embed showing achievement progress by category.

        Args:
            user: The Discord member
            category_stats: Dictionary with category statistics

        Returns:
            Discord embed showing category progress
        """
        embed = discord.Embed(
            title=f"📂 {user.display_name}'s Achievement Categories",
            description="Progress across all achievement categories",
            color=self.notification_color,
            timestamp=datetime.utcnow(),
        )

        for category, stats in category_stats.items():
            total = stats["total"]
            unlocked = stats["unlocked"]
            percentage = (unlocked / total) * 100 if total > 0 else 0
            progress_bar = self._create_progress_bar(percentage)

            embed.add_field(
                name=f"📁 {category.title()}",
                value=f"{progress_bar}\n{unlocked}/{total} ({percentage:.0f}%)",
                inline=True,
            )

        embed.set_thumbnail(
            url=user.avatar.url if user.avatar else user.default_avatar.url
        )

        return embed

    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """
        Create a visual progress bar using Unicode characters.

        Args:
            percentage: Progress percentage (0-100)
            length: Length of the progress bar

        Returns:
            String representation of the progress bar
        """
        filled_length = int(length * percentage / 100)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return f"[{bar}]"

    async def send_achievement_notification(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        achievements: List[Achievement],
    ) -> Optional[discord.Message]:
        """
        Send achievement notification to a Discord channel.

        Args:
            channel: Discord channel to send the notification to
            user: The user who unlocked the achievement(s)
            achievements: List of achievements unlocked

        Returns:
            The sent message, or None if failed
        """
        try:
            if len(achievements) == 1:
                embed = self.create_achievement_unlock_embed(user, achievements[0])
            else:
                embed = self.create_multiple_achievements_embed(user, achievements)

            message = await channel.send(embed=embed)
            logger.info(
                f"Sent achievement notification for {user.display_name} in {channel.name}"
            )
            return message

        except discord.Forbidden:
            logger.error(
                f"Missing permissions to send achievement notification in {channel.name}"
            )
            return None
        except discord.HTTPException as e:
            logger.error(f"Failed to send achievement notification: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending achievement notification: {e}")
            return None

    async def add_navigation_reactions(
        self, message: discord.Message, total_pages: int
    ):
        """
        Add navigation reactions to a paginated message.

        Args:
            message: The Discord message to add reactions to
            total_pages: Total number of pages
        """
        try:
            if total_pages > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")
        except discord.Forbidden:
            logger.warning("Missing permissions to add navigation reactions")
        except discord.HTTPException as e:
            logger.warning(f"Failed to add navigation reactions: {e}")


# Global notification system instance
notification_system = AchievementNotificationSystem()
