"""
Enhanced Trivia Cog for the Enhanced Trivia System.
Provides trivia commands with challenge system integration.
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from utils.game_manager import GameManager
from utils.user_manager import user_manager
from utils.question_engine import QuestionEngine
from utils.challenge_system import ChallengeSystem
from utils.database import db_manager

logger = logging.getLogger(__name__)


class EnhancedTriviaCog(commands.Cog):
    """Enhanced trivia cog with challenge system support."""

    def __init__(self, bot):
        self.bot = bot
        self.question_engine = None
        self.game_manager = None
        self.challenge_system = None
        logger.info("EnhancedTriviaCog initialized")

    async def cog_load(self):
        """Initialize components when cog is loaded."""
        try:
            # Initialize database
            await db_manager.initialize_database()

            # Initialize question engine
            self.question_engine = QuestionEngine()
            await self.question_engine.initialize()

            # Initialize game manager
            self.game_manager = GameManager(self.question_engine)

            # Initialize challenge system
            self.challenge_system = ChallengeSystem(self.question_engine, user_manager)

            logger.info("Enhanced trivia system components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced trivia components: {e}")
            raise

    async def cog_unload(self):
        """Clean up when cog is unloaded."""
        try:
            if self.game_manager:
                await self.game_manager.shutdown()
            if self.challenge_system:
                await self.challenge_system.shutdown()
            logger.info("Enhanced trivia system components shut down")
        except Exception as e:
            logger.error(f"Error during enhanced trivia shutdown: {e}")

    @commands.command(name="dailychallenge", aliases=["daily"])
    async def daily_challenge(self, ctx):
        """Start a daily challenge with double point rewards."""
        try:
            user_id = ctx.author.id
            channel_id = ctx.channel.id

            # Check if user can attempt daily challenge
            status = await self.challenge_system.get_challenge_status(user_id)

            if not status["daily"]["available"]:
                if status["daily"]["completed_today"]:
                    embed = discord.Embed(
                        title="✅ Daily Challenge Complete",
                        description="You've already completed today's daily challenge! Come back tomorrow for a new one.",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="💡 Tip",
                        value="Try the weekly challenge or regular trivia while you wait!",
                        inline=False,
                    )
                elif status["daily"]["active"]:
                    embed = discord.Embed(
                        title="🎮 Daily Challenge Active",
                        description="You already have an active daily challenge! Complete it first.",
                        color=discord.Color.orange(),
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Daily Challenge Unavailable",
                        description="Daily challenge is not available right now. Please try again later.",
                        color=discord.Color.red(),
                    )
                await ctx.send(embed=embed)
                return

            # Check if there's already an active game in this channel
            if await self.game_manager.get_active_game(channel_id):
                embed = discord.Embed(
                    title="🎮 Game Already Active",
                    description="There's already a trivia game active in this channel! Finish it first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                return

            # Get daily challenge question
            question = await self.challenge_system.get_daily_challenge(user_id)
            if not question:
                embed = discord.Embed(
                    title="❌ Challenge Unavailable",
                    description="Unable to generate daily challenge question. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Start the challenge game
            game_session = await self.game_manager.start_game(
                channel_id=channel_id,
                user_id=user_id,
                difficulty=question.difficulty,
                is_challenge=True,
                timeout_duration=45,  # Longer timeout for challenges
                timeout_callback=lambda: self._handle_challenge_timeout(
                    ctx, user_id, "daily"
                ),
                countdown_callback=lambda remaining: self._handle_countdown(
                    ctx, remaining
                ),
            )

            if not game_session:
                embed = discord.Embed(
                    title="❌ Failed to Start Challenge",
                    description="Unable to start daily challenge. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create and send challenge embed
            embed = await self._create_challenge_embed(question, "daily")
            message = await ctx.send(embed=embed)

            # Add reactions for multiple choice questions
            if question.question_type == "multiple_choice":
                reactions = ["🇦", "🇧", "🇨", "🇩"]
                for i, reaction in enumerate(reactions[: len(question.options)]):
                    await message.add_reaction(reaction)

            logger.info(
                f"Started daily challenge for user {user_id} in channel {channel_id}"
            )

        except Exception as e:
            logger.error(f"Error in daily challenge command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while starting the daily challenge. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    @commands.command(name="weeklychallenge", aliases=["weekly"])
    async def weekly_challenge(self, ctx):
        """Start a weekly challenge with 5 questions and triple point rewards."""
        try:
            user_id = ctx.author.id
            channel_id = ctx.channel.id

            # Check if user can attempt weekly challenge
            status = await self.challenge_system.get_challenge_status(user_id)

            if not status["weekly"]["available"]:
                if status["weekly"]["completed_this_week"]:
                    embed = discord.Embed(
                        title="✅ Weekly Challenge Complete",
                        description="You've already completed this week's challenge! New challenges are posted every Monday.",
                        color=discord.Color.green(),
                    )
                elif status["weekly"]["active"]:
                    progress = status["weekly"]["progress"]
                    embed = discord.Embed(
                        title="🎮 Weekly Challenge In Progress",
                        description=f"You're currently on question {progress['current_question']}/5 of this week's challenge!",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(
                        name="Progress",
                        value=f"✅ Correct: {progress['correct_answers']}\n💰 Points: {progress['points_so_far']}",
                        inline=True,
                    )
                    embed.add_field(
                        name="Next Step",
                        value="Continue your challenge in any channel!",
                        inline=True,
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Weekly Challenge Unavailable",
                        description="Weekly challenge is not available right now. Please try again later.",
                        color=discord.Color.red(),
                    )
                await ctx.send(embed=embed)
                return

            # Check if there's already an active game in this channel
            if await self.game_manager.get_active_game(channel_id):
                embed = discord.Embed(
                    title="🎮 Game Already Active",
                    description="There's already a trivia game active in this channel! Finish it first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                return

            # Get weekly challenge questions (first time) or current question (continuing)
            current_question = await self.challenge_system.get_current_weekly_question(
                user_id
            )

            if not current_question:
                # Start new weekly challenge
                questions = await self.challenge_system.get_weekly_challenge(user_id)
                if not questions:
                    embed = discord.Embed(
                        title="❌ Challenge Unavailable",
                        description="Unable to generate weekly challenge questions. Please try again later.",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
                    return
                current_question = questions[0]

            # Start the challenge game
            game_session = await self.game_manager.start_game(
                channel_id=channel_id,
                user_id=user_id,
                difficulty=current_question.difficulty,
                is_challenge=True,
                timeout_duration=60,  # Longer timeout for weekly challenges
                timeout_callback=lambda: self._handle_challenge_timeout(
                    ctx, user_id, "weekly"
                ),
                countdown_callback=lambda remaining: self._handle_countdown(
                    ctx, remaining
                ),
            )

            if not game_session:
                embed = discord.Embed(
                    title="❌ Failed to Start Challenge",
                    description="Unable to start weekly challenge. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Create and send challenge embed
            embed = await self._create_challenge_embed(current_question, "weekly")
            message = await ctx.send(embed=embed)

            # Add reactions for multiple choice questions
            if current_question.question_type == "multiple_choice":
                reactions = ["🇦", "🇧", "🇨", "🇩"]
                for i, reaction in enumerate(
                    reactions[: len(current_question.options)]
                ):
                    await message.add_reaction(reaction)

            logger.info(
                f"Started weekly challenge for user {user_id} in channel {channel_id}"
            )

        except Exception as e:
            logger.error(f"Error in weekly challenge command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while starting the weekly challenge. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    async def _create_challenge_embed(
        self, question, challenge_type: str
    ) -> discord.Embed:
        """Create an embed for a challenge question."""
        # Determine colors and titles
        if challenge_type == "daily":
            color = 0xFFD700  # Gold
            title = "🌟 Daily Challenge"
            reward_text = "Double Points!"
        else:  # weekly
            color = 0x9932CC  # Purple
            title = "👑 Weekly Challenge"
            reward_text = "Triple Points!"

        embed = discord.Embed(
            title=title,
            description=question.question_text,
            color=color,
        )

        # Add difficulty and category info
        embed.add_field(
            name="📊 Info",
            value=f"**Difficulty:** {question.difficulty.title()}\n**Category:** {question.category.title()}",
            inline=True,
        )

        embed.add_field(
            name="🎁 Reward",
            value=reward_text,
            inline=True,
        )

        # Add options for multiple choice
        if question.question_type == "multiple_choice" and question.options:
            options_text = ""
            reactions = ["🇦", "🇧", "🇨", "🇩"]
            for i, option in enumerate(question.options):
                options_text += f"{reactions[i]} {option}\n"

            embed.add_field(
                name="Options",
                value=options_text,
                inline=False,
            )
            embed.set_footer(text="React with 🇦, 🇧, 🇨, or 🇩 to answer!")
        elif question.question_type == "true_false":
            embed.set_footer(text="Type 'true' or 'false' to answer!")
        else:
            embed.set_footer(text="Type your answer!")

        return embed

    async def _handle_challenge_timeout(self, ctx, user_id: int, challenge_type: str):
        """Handle challenge timeout."""
        try:
            # Cancel the active challenge
            await self.challenge_system.cancel_active_challenge(user_id, challenge_type)

            embed = discord.Embed(
                title="⏰ Challenge Timed Out",
                description=f"Your {challenge_type} challenge has timed out. You can try again tomorrow!"
                if challenge_type == "daily"
                else "Your weekly challenge question has timed out. You can continue later!",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling challenge timeout: {e}")

    async def _handle_countdown(self, ctx, remaining: int):
        """Handle countdown notifications."""
        try:
            if remaining == 20:
                await ctx.send("⏰ 20 seconds remaining!")
            elif remaining == 10:
                await ctx.send("⏰ 10 seconds remaining!")
        except Exception as e:
            logger.error(f"Error in countdown handler: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle trivia answer reactions for challenges."""
        try:
            # Ignore bot reactions
            if user.bot:
                return

            channel_id = reaction.message.channel.id
            user_id = user.id

            # Check if there's an active game in this channel
            game_session = await self.game_manager.get_active_game(channel_id)
            if not game_session or not game_session.is_challenge:
                return

            # Process the reaction answer
            result = await self.game_manager.process_reaction_answer(
                channel_id, user_id, reaction, user
            )

            if result:
                await self._handle_challenge_result(
                    reaction.message.channel, user, result, game_session
                )

        except Exception as e:
            logger.error(f"Error handling challenge reaction: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle text-based answers for challenges."""
        try:
            # Ignore bot messages
            if message.author.bot:
                return

            # Skip if it's a command
            if message.content.startswith("!"):
                return

            channel_id = message.channel.id
            user_id = message.author.id

            # Check if there's an active game in this channel
            game_session = await self.game_manager.get_active_game(channel_id)
            if not game_session or not game_session.is_challenge:
                return

            # Process the text answer
            result = await self.game_manager.process_text_answer(
                channel_id, user_id, message
            )

            if result:
                await self._handle_challenge_result(
                    message.channel, message.author, result, game_session
                )

        except Exception as e:
            logger.error(f"Error handling challenge text answer: {e}", exc_info=True)

    @commands.command(name="challengeprogress", aliases=["progress"])
    async def challenge_progress(self, ctx):
        """Display current challenge progress and status."""
        try:
            user_id = ctx.author.id

            # Get challenge status
            status = await self.challenge_system.get_challenge_status(user_id)

            embed = discord.Embed(
                title="📊 Challenge Progress",
                description=f"Challenge status for **{ctx.author.display_name}**",
                color=0x00BFFF,  # Deep sky blue
            )

            # Daily challenge status
            daily_status = (
                "✅ Completed"
                if status["daily"]["completed_today"]
                else "🎯 Available"
                if status["daily"]["available"]
                else "🎮 Active"
            )
            embed.add_field(
                name="🌟 Daily Challenge",
                value=f"Status: {daily_status}\nReward: Double points",
                inline=True,
            )

            # Weekly challenge status
            if status["weekly"]["active"] and status["weekly"]["progress"]:
                progress = status["weekly"]["progress"]
                weekly_status = f"🎮 In Progress ({progress['current_question']}/5)"
                weekly_details = f"Correct: {progress['correct_answers']}\nPoints: {progress['points_so_far']}"

                # Get detailed progress
                detailed_progress = (
                    await self.challenge_system.get_weekly_challenge_progress(user_id)
                )
                if detailed_progress:
                    accuracy = detailed_progress["accuracy"]
                    potential_badge = detailed_progress.get("potential_badge", "None")
                    weekly_details += f"\nAccuracy: {accuracy:.1f}%\nPotential Badge: {potential_badge.replace('_', ' ').title() if potential_badge else 'None'}"

            elif status["weekly"]["completed_this_week"]:
                weekly_status = "✅ Completed"
                weekly_details = "Come back next Monday!"
            else:
                weekly_status = "🎯 Available"
                weekly_details = "5 questions, triple points!"

            embed.add_field(
                name="👑 Weekly Challenge",
                value=f"Status: {weekly_status}\n{weekly_details}",
                inline=True,
            )

            # Add tips
            tips = []
            if status["daily"]["available"]:
                tips.append("Use `!dailychallenge` for double points!")
            if status["weekly"]["available"]:
                tips.append("Use `!weeklychallenge` for triple points!")
            if not tips:
                tips.append("Great job completing your challenges!")

            embed.add_field(
                name="💡 Tips",
                value="\n".join(tips),
                inline=False,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in challenge progress command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An error occurred while getting challenge progress. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)

    async def _handle_challenge_result(self, channel, user, result, game_session):
        """Handle the result of a challenge answer."""
        try:
            user_id = user.id

            # Determine challenge type based on active challenges
            challenge_type = None
            if user_id in self.challenge_system.active_daily_challenges:
                challenge_type = "daily"
            elif user_id in self.challenge_system.active_weekly_challenges:
                challenge_type = "weekly"

            if not challenge_type:
                logger.warning(f"Could not determine challenge type for user {user_id}")
                return

            # Process challenge-specific result
            if challenge_type == "daily":
                challenge_result = (
                    await self.challenge_system.process_daily_challenge_answer(
                        user_id, result.is_correct, result.time_taken
                    )
                )
            else:  # weekly
                challenge_result = (
                    await self.challenge_system.process_weekly_challenge_answer(
                        user_id, result.is_correct, result.time_taken
                    )
                )

            if not challenge_result.get("success"):
                logger.error(f"Challenge processing failed: {challenge_result}")
                return

            # Create result embed
            embed = await self._create_result_embed(user, result, challenge_result)
            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling challenge result: {e}", exc_info=True)

    async def _create_result_embed(
        self, user, result, challenge_result
    ) -> discord.Embed:
        """Create an embed for challenge results."""
        challenge_type = challenge_result["challenge_type"]

        if result.is_correct:
            color = discord.Color.green()
            title = "🎉 Correct!"
            description = f"**{user.display_name}** got it right!"
        else:
            color = discord.Color.red()
            title = "❌ Incorrect!"
            description = f"Sorry **{user.display_name}**, that's not right."

        embed = discord.Embed(title=title, description=description, color=color)

        # Add points information
        if challenge_type == "daily":
            embed.add_field(
                name="💰 Points Earned",
                value=f"{challenge_result['challenge_points']} points (2x bonus!)",
                inline=True,
            )
        else:  # weekly
            embed.add_field(
                name="💰 Points This Question",
                value=f"{challenge_result['points']} points",
                inline=True,
            )

            if challenge_result.get("is_completed"):
                # Weekly challenge completed
                embed.add_field(
                    name="🏆 Challenge Complete!",
                    value=f"Final Score: {challenge_result['final_score']}\nTotal Points: {challenge_result['final_points']} (3x bonus!)",
                    inline=False,
                )

                if challenge_result.get("badge_awarded"):
                    badge_name = (
                        challenge_result["badge_awarded"].replace("_", " ").title()
                    )
                    embed.add_field(
                        name="🏅 Badge Earned",
                        value=badge_name,
                        inline=True,
                    )
            else:
                # Show weekly progress
                embed.add_field(
                    name="📊 Progress",
                    value=f"Question {challenge_result['question_number']}/{challenge_result['total_questions']}\nCorrect: {challenge_result['correct_so_far']}",
                    inline=True,
                )

        # Add explanation if available
        if result.explanation:
            embed.add_field(
                name="💡 Explanation",
                value=result.explanation,
                inline=False,
            )

        return embed


async def setup(bot):
    """Set up the enhanced trivia cog."""
    await bot.add_cog(EnhancedTriviaCog(bot))
    logger.info("EnhancedTriviaCog added to bot")
