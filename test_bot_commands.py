#!/usr/bin/env python3
"""
Test script for Discord bot command integration.
Tests the enhanced trivia cog commands without actually running Discord.
"""

import asyncio
import logging
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cogs.enhanced_trivia import EnhancedTriviaCog
from utils.models import Question

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockBot:
    """Mock Discord bot for testing."""

    pass


class MockContext:
    """Mock Discord context for testing."""

    def __init__(self, user_id=12345, channel_id=67890):
        self.author = MagicMock()
        self.author.id = user_id
        self.author.display_name = "TestUser"
        self.channel = MagicMock()
        self.channel.id = channel_id
        self.send = AsyncMock()


async def test_cog_initialization():
    """Test that the enhanced trivia cog initializes correctly."""
    logger.info("=== Testing Cog Initialization ===")

    try:
        # Create mock bot
        bot = MockBot()

        # Create cog
        cog = EnhancedTriviaCog(bot)

        # Mock the initialization components
        cog.question_engine = MagicMock()
        cog.game_manager = MagicMock()
        cog.challenge_system = MagicMock()

        logger.info("✅ Enhanced trivia cog initialized successfully")
        return cog

    except Exception as e:
        logger.error(f"❌ Cog initialization failed: {e}")
        raise


async def test_daily_challenge_command():
    """Test the daily challenge command."""
    logger.info("=== Testing Daily Challenge Command ===")

    try:
        # Create cog and mock context
        cog = await test_cog_initialization()
        ctx = MockContext()

        # Mock challenge system responses
        cog.challenge_system.get_challenge_status = AsyncMock(
            return_value={
                "daily": {"available": True, "completed_today": False, "active": False},
                "weekly": {
                    "available": True,
                    "completed_this_week": False,
                    "active": False,
                },
            }
        )

        cog.challenge_system.get_daily_challenge = AsyncMock(
            return_value=Question(
                id=1,
                question_text="Test daily challenge question?",
                question_type="multiple_choice",
                difficulty="medium",
                category="test",
                options=["A", "B", "C", "D"],
                point_value=20,
            )
        )

        cog.game_manager.get_active_game = AsyncMock(return_value=None)
        cog.game_manager.start_game = AsyncMock(return_value=MagicMock())

        # Test the command
        await cog.daily_challenge(ctx)

        # Verify the command was processed
        assert ctx.send.called, "Should send a response"
        call_args = (
            ctx.send.call_args[1] if ctx.send.call_args[1] else ctx.send.call_args[0]
        )
        embed = call_args.get("embed") if isinstance(call_args, dict) else call_args[0]
        assert embed is not None, "Should send an embed"
        assert "Daily Challenge" in embed.title, "Should be a daily challenge embed"

        logger.info("✅ Daily challenge command test passed")

    except Exception as e:
        logger.error(f"❌ Daily challenge command test failed: {e}")
        raise


async def test_weekly_challenge_command():
    """Test the weekly challenge command."""
    logger.info("=== Testing Weekly Challenge Command ===")

    try:
        # Create cog and mock context
        cog = await test_cog_initialization()
        ctx = MockContext()

        # Mock challenge system responses
        cog.challenge_system.get_challenge_status = AsyncMock(
            return_value={
                "daily": {"available": True, "completed_today": False, "active": False},
                "weekly": {
                    "available": True,
                    "completed_this_week": False,
                    "active": False,
                },
            }
        )

        cog.challenge_system.get_current_weekly_question = AsyncMock(return_value=None)
        cog.challenge_system.get_weekly_challenge = AsyncMock(
            return_value=[
                Question(
                    id=i,
                    question_text=f"Question {i}?",
                    difficulty="medium",
                    point_value=20,
                )
                for i in range(1, 6)
            ]
        )

        cog.game_manager.get_active_game = AsyncMock(return_value=None)
        cog.game_manager.start_game = AsyncMock(return_value=MagicMock())

        # Test the command
        await cog.weekly_challenge(ctx)

        # Verify the command was processed
        assert ctx.send.called, "Should send a response"
        call_args = (
            ctx.send.call_args[1] if ctx.send.call_args[1] else ctx.send.call_args[0]
        )
        embed = call_args.get("embed") if isinstance(call_args, dict) else call_args[0]
        assert embed is not None, "Should send an embed"
        assert "Weekly Challenge" in embed.title, "Should be a weekly challenge embed"

        logger.info("✅ Weekly challenge command test passed")

    except Exception as e:
        logger.error(f"❌ Weekly challenge command test failed: {e}")
        raise


async def test_challenge_progress_command():
    """Test the challenge progress command."""
    logger.info("=== Testing Challenge Progress Command ===")

    try:
        # Create cog and mock context
        cog = await test_cog_initialization()
        ctx = MockContext()

        # Mock challenge system responses
        cog.challenge_system.get_challenge_status = AsyncMock(
            return_value={
                "daily": {"available": True, "completed_today": False, "active": False},
                "weekly": {
                    "available": False,
                    "completed_this_week": False,
                    "active": True,
                    "progress": {
                        "current_question": 3,
                        "correct_answers": 2,
                        "points_so_far": 40,
                    },
                },
            }
        )

        cog.challenge_system.get_weekly_challenge_progress = AsyncMock(
            return_value={
                "current_question": 3,
                "correct_answers": 2,
                "accuracy": 66.7,
                "potential_badge": "weekly_good",
            }
        )

        # Test the command
        await cog.challenge_progress(ctx)

        # Verify the command was processed
        assert ctx.send.called, "Should send a response"
        call_args = (
            ctx.send.call_args[1] if ctx.send.call_args[1] else ctx.send.call_args[0]
        )
        embed = call_args.get("embed") if isinstance(call_args, dict) else call_args[0]
        assert embed is not None, "Should send an embed"
        assert "Challenge Progress" in embed.title, "Should be a progress embed"

        logger.info("✅ Challenge progress command test passed")

    except Exception as e:
        logger.error(f"❌ Challenge progress command test failed: {e}")
        raise


async def test_challenge_already_completed():
    """Test daily challenge when already completed."""
    logger.info("=== Testing Already Completed Challenge ===")

    try:
        # Create cog and mock context
        cog = await test_cog_initialization()
        ctx = MockContext()

        # Mock challenge system to show daily challenge already completed
        cog.challenge_system.get_challenge_status = AsyncMock(
            return_value={
                "daily": {"available": False, "completed_today": True, "active": False},
                "weekly": {
                    "available": True,
                    "completed_this_week": False,
                    "active": False,
                },
            }
        )

        # Test the command
        await cog.daily_challenge(ctx)

        # Verify the command was processed
        assert ctx.send.called, "Should send a response"
        call_args = (
            ctx.send.call_args[1] if ctx.send.call_args[1] else ctx.send.call_args[0]
        )
        embed = call_args.get("embed") if isinstance(call_args, dict) else call_args[0]
        assert embed is not None, "Should send an embed"
        assert "Complete" in embed.title, "Should indicate challenge is complete"

        logger.info("✅ Already completed challenge test passed")

    except Exception as e:
        logger.error(f"❌ Already completed challenge test failed: {e}")
        raise


async def main():
    """Run all command tests."""
    logger.info("🚀 Starting Discord Bot Command Tests")

    try:
        await test_cog_initialization()
        await test_daily_challenge_command()
        await test_weekly_challenge_command()
        await test_challenge_progress_command()
        await test_challenge_already_completed()

        logger.info("🎉 All Discord bot command tests passed!")

    except Exception as e:
        logger.error(f"❌ Command tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
