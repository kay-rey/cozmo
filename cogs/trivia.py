import discord
from discord.ext import commands
import random
import logging
from data.trivia_questions import QUESTIONS

logger = logging.getLogger(__name__)


class TriviaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Track active games per channel
        self.active_games = {}
        logger.info("TriviaCog initialized")

    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """Start a new trivia game if no game is currently active in this channel"""
        logger.info(f"Trivia command invoked by {ctx.author} in {ctx.guild}")

        try:
            channel_id = ctx.channel.id

            # Check if a game is already active in this channel
            if channel_id in self.active_games:
                embed = discord.Embed(
                    title="🎮 Trivia Game Active",
                    description="A trivia game is already active in this channel! Answer the current question first.",
                    color=discord.Color.orange(),
                )
                await ctx.send(embed=embed)
                logger.info(f"Trivia game already active in channel {channel_id}")
                return

            # Validate trivia questions are available
            if not QUESTIONS:
                logger.error("No trivia questions available")
                embed = discord.Embed(
                    title="❌ Trivia Unavailable",
                    description="Sorry, trivia questions are not available right now. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Flatten all questions from all difficulty levels
            all_questions = []
            for difficulty_level in QUESTIONS.values():
                all_questions.extend(difficulty_level)

            if not all_questions:
                logger.error("No trivia questions found in any difficulty level")
                embed = discord.Embed(
                    title="❌ Trivia Unavailable",
                    description="Sorry, trivia questions are not available right now. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Filter for multiple choice questions only (for now)
            multiple_choice_questions = [
                q for q in all_questions if q.get("question_type") == "multiple_choice"
            ]

            if not multiple_choice_questions:
                logger.error("No multiple choice questions available")
                embed = discord.Embed(
                    title="❌ Trivia Unavailable",
                    description="Sorry, no multiple choice questions are available right now. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                return

            # Select a random multiple choice question
            question_data = random.choice(multiple_choice_questions)

            # Validate question data structure
            required_keys = ["question", "options", "correct_answer"]
            if not all(key in question_data for key in required_keys):
                logger.error(f"Invalid question data structure: {question_data}")
                raise ValueError("Invalid trivia question format")

            if len(question_data["options"]) != 4:
                logger.error(f"Question must have exactly 4 options: {question_data}")
                raise ValueError("Invalid number of options in trivia question")

            # Create Discord embed for the trivia question
            embed = discord.Embed(
                title="🏆 LA Galaxy Trivia",
                description=question_data["question"],
                color=0x00274C,  # LA Galaxy navy blue
            )

            # Add options as fields
            options = question_data["options"]
            option_letters = ["🇦", "🇧", "🇨", "🇩"]

            for i, option in enumerate(options):
                embed.add_field(
                    name=f"{option_letters[i]} {chr(65 + i)}",
                    value=option,
                    inline=False,
                )

            embed.set_footer(text="React with 🇦, 🇧, 🇨, or 🇩 to answer!")

            # Send the question
            message = await ctx.send(embed=embed)

            # Store the active game data
            self.active_games[channel_id] = {
                "message_id": message.id,
                "correct_answer": question_data["correct_answer"],
                "question": question_data["question"],
                "options": options,
            }

            # Add reaction emojis for user interaction
            try:
                for emoji in option_letters:
                    await message.add_reaction(emoji)
                logger.info(f"Successfully started trivia game in channel {channel_id}")
            except discord.Forbidden:
                logger.error("Missing permissions to add reactions")
                embed = discord.Embed(
                    title="❌ Permission Error",
                    description="I don't have permission to add reactions. Please ensure I have the 'Add Reactions' permission.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                # Clean up the game since we can't add reactions
                del self.active_games[channel_id]
            except discord.HTTPException as e:
                logger.error(f"Failed to add reactions: {e}")
                embed = discord.Embed(
                    title="❌ Error Starting Game",
                    description="Failed to set up the trivia game. Please try again.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)
                # Clean up the game
                if channel_id in self.active_games:
                    del self.active_games[channel_id]

        except Exception as e:
            logger.error(f"Unexpected error in trivia command: {e}", exc_info=True)
            embed = discord.Embed(
                title="❌ Something Went Wrong",
                description="An unexpected error occurred while starting the trivia game. The issue has been logged.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            # Clean up any partial game state
            if ctx.channel.id in self.active_games:
                del self.active_games[ctx.channel.id]

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle trivia answer reactions"""
        try:
            # Ignore bot reactions
            if user.bot:
                return

            channel_id = reaction.message.channel.id
            message_id = reaction.message.id

            # Check if this reaction is for an active trivia game
            if channel_id not in self.active_games:
                return

            game_data = self.active_games[channel_id]

            # Check if this is the correct message
            if message_id != game_data["message_id"]:
                return

            # Map emoji to answer index
            emoji_to_index = {"🇦": 0, "🇧": 1, "🇨": 2, "🇩": 3}

            # Check if the reaction is a valid answer option
            if str(reaction.emoji) not in emoji_to_index:
                return

            user_answer = emoji_to_index[str(reaction.emoji)]
            correct_answer = game_data["correct_answer"]

            # Validate correct answer index
            if not (0 <= correct_answer < len(game_data["options"])):
                logger.error(f"Invalid correct answer index: {correct_answer}")
                return

            # Create response embed
            if user_answer == correct_answer:
                # Correct answer
                embed = discord.Embed(
                    title="🎉 Correct!",
                    description=f"**{user.display_name}** got it right!",
                    color=0x00FF00,  # Green
                )
                embed.add_field(
                    name="Answer",
                    value=f"🇦🇧🇨🇩"[correct_answer]
                    + f" {game_data['options'][correct_answer]}",
                    inline=False,
                )
                logger.info(
                    f"User {user.display_name} answered trivia correctly in channel {channel_id}"
                )
            else:
                # Incorrect answer
                embed = discord.Embed(
                    title="❌ Incorrect!",
                    description=f"Sorry **{user.display_name}**, that's not right.",
                    color=0xFF0000,  # Red
                )
                embed.add_field(
                    name="Correct Answer",
                    value=f"🇦🇧🇨🇩"[correct_answer]
                    + f" {game_data['options'][correct_answer]}",
                    inline=False,
                )
                logger.info(
                    f"User {user.display_name} answered trivia incorrectly in channel {channel_id}"
                )

            # Send the result
            try:
                await reaction.message.channel.send(embed=embed)
            except discord.Forbidden:
                logger.error("Missing permissions to send messages in trivia channel")
            except discord.HTTPException as e:
                logger.error(f"Failed to send trivia result message: {e}")

            # Clean up the completed game
            del self.active_games[channel_id]
            logger.info(f"Trivia game completed and cleaned up in channel {channel_id}")

            # Clear reactions from the original message
            try:
                await reaction.message.clear_reactions()
            except discord.Forbidden:
                logger.warning(
                    "Missing permissions to clear reactions from trivia message"
                )
            except discord.NotFound:
                logger.warning(
                    "Trivia message was deleted before reactions could be cleared"
                )
            except discord.HTTPException as e:
                logger.warning(f"Failed to clear reactions from trivia message: {e}")

        except Exception as e:
            logger.error(
                f"Unexpected error in trivia reaction handler: {e}", exc_info=True
            )
            # Clean up game state if there was an error
            if (
                hasattr(reaction, "message")
                and reaction.message.channel.id in self.active_games
            ):
                del self.active_games[reaction.message.channel.id]
                logger.info("Cleaned up trivia game state after error")

    @trivia.error
    async def trivia_error(self, ctx: commands.Context, error: commands.CommandError):
        """Error handler for the trivia command."""
        logger.error(f"Command error in trivia: {error}")

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"⏰ Please wait {error.retry_after:.1f} seconds before starting another trivia game."
            )
        else:
            embed = discord.Embed(
                title="❌ Command Error",
                description="There was an error starting the trivia game. Please try again.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TriviaCog(bot))
    logger.info("TriviaCog added to bot")
