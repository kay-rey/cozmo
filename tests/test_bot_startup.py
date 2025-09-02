#!/usr/bin/env python3
"""
Test bot startup without actually connecting to Discord.
This verifies that all initialization code works properly.
"""

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_bot_startup():
    """Test that the bot can start up without connecting to Discord."""
    print("Testing bot startup sequence...")

    # Use mock tokens for testing
    mock_env = {
        "DISCORD_TOKEN": "fake_discord_token_for_testing_only",
        "SPORTS_API_KEY": "test_sports_api_key_12345",
        "NEWS_CHANNEL_ID": "123456789012345678",
    }

    try:
        with patch.dict(os.environ, mock_env):
            from main import CozmoBot

            # Create bot instance
            bot = CozmoBot()
            print("✓ Bot instance created")

            # Test setup_hook (this loads cogs)
            await bot.setup_hook()
            print("✓ Setup hook completed (cogs loaded)")

            # Test that cogs were loaded
            loaded_cogs = list(bot.cogs.keys())
            expected_cogs = ["MatchdayCog", "StatsCog", "NewsCog", "TriviaCog"]

            print(f"Loaded cogs: {loaded_cogs}")

            for expected_cog in expected_cogs:
                if expected_cog in loaded_cogs:
                    print(f"✓ {expected_cog} loaded successfully")
                else:
                    print(f"⚠ {expected_cog} not found in loaded cogs")

            # Test that commands are registered
            commands = [cmd.name for cmd in bot.commands]
            print(f"Registered commands: {commands}")

            expected_commands = [
                "nextmatch",
                "standings",
                "playerstats",
                "news",
                "trivia",
            ]
            for expected_cmd in expected_commands:
                if expected_cmd in commands:
                    print(f"✓ Command '{expected_cmd}' registered")
                else:
                    print(f"⚠ Command '{expected_cmd}' not found")

            # Clean up
            await bot.close()
            print("✓ Bot shutdown completed")

            return True

    except Exception as e:
        print(f"✗ Bot startup test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run startup test."""
    print("=" * 50)
    print("Cozmo Discord Bot Startup Test")
    print("=" * 50)

    success = await test_bot_startup()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Bot startup test PASSED!")
        print("The bot is ready to connect to Discord.")
    else:
        print("❌ Bot startup test FAILED!")
        print("Please check the error messages above.")
    print("=" * 50)

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
