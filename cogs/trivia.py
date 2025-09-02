import discord
from discord.ext import commands
import random
from trivia_questions import QUESTIONS


class TriviaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Track active games per channel
        self.active_games = {}

    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """Start a new trivia game if no game is currently active in this channel"""
        channel_id = ctx.channel.id

        # Check if a game is already active in this channel
        if channel_id in self.active_games:
            await ctx.send(
                "A trivia game is already active in this channel! Answer the current question first."
            )
            return

        # Select a random question
        question_data = random.choice(QUESTIONS)

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
                name=f"{option_letters[i]} {chr(65 + i)}", value=option, inline=False
            )

        embed.set_footer(text="React with 🇦, 🇧, 🇨, or 🇩 to answer!")

        # Send the question
        message = await ctx.send(embed=embed)

        # Store the active game data
        self.active_games[channel_id] = {
            "message_id": message.id,
            "correct_answer": question_data["answer"],
            "question": question_data["question"],
            "options": options,
        }

        # Add reaction emojis for user interaction
        for emoji in option_letters:
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle trivia answer reactions"""
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

        # Send the result
        await reaction.message.channel.send(embed=embed)

        # Clean up the completed game
        del self.active_games[channel_id]

        # Clear reactions from the original message
        try:
            await reaction.message.clear_reactions()
        except discord.Forbidden:
            # Bot doesn't have permission to clear reactions
            pass


async def setup(bot):
    await bot.add_cog(TriviaCog(bot))
