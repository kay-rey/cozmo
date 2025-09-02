#!/usr/bin/env python3
"""
Integration test for Cozmo Discord Bot.
Tests that all components can be imported and initialized properly.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        # Test config import
        from config import config

        print("✓ Config module imported successfully")

        # Test API imports
        from api.sports_api import (
            sports_client,
            get_next_match,
            get_standings,
            get_player_stats,
        )
        from api.news_api import news_client, get_latest_news

        print("✓ API modules imported successfully")

        # Test main bot import
        from main import CozmoBot

        print("✓ Main bot class imported successfully")

        # Test cog imports
        cogs_dir = Path("cogs")
        cog_files = [f for f in cogs_dir.glob("*.py") if f.name != "__init__.py"]

        for cog_file in cog_files:
            cog_module = f"cogs.{cog_file.stem}"
            try:
                __import__(cog_module)
                print(f"✓ Cog {cog_module} imported successfully")
            except Exception as e:
                print(f"✗ Failed to import cog {cog_module}: {e}")
                return False

        return True

    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


async def test_bot_initialization():
    """Test that the bot can be initialized without errors."""
    print("\nTesting bot initialization...")

    try:
        from main import CozmoBot

        # Create bot instance
        bot = CozmoBot()
        print("✓ Bot instance created successfully")

        # Test that bot has required attributes
        assert hasattr(bot, "command_prefix"), "Bot missing command_prefix"
        assert hasattr(bot, "intents"), "Bot missing intents"
        assert bot.command_prefix == "!", "Incorrect command prefix"
        print("✓ Bot configuration validated")

        # Clean up
        await bot.close()
        print("✓ Bot cleanup completed")

        return True

    except Exception as e:
        print(f"✗ Bot initialization failed: {e}")
        return False


async def test_api_clients():
    """Test that API clients can be initialized."""
    print("\nTesting API client initialization...")

    try:
        from api.sports_api import sports_client
        from api.news_api import news_client

        # Test sports client
        assert hasattr(sports_client, "base_url"), "Sports client missing base_url"
        assert hasattr(sports_client, "api_key"), "Sports client missing api_key"
        print("✓ Sports API client initialized")

        # Test news client
        assert hasattr(news_client, "rss_url"), "News client missing rss_url"
        print("✓ News API client initialized")

        # Test cleanup
        await sports_client.close()
        await news_client.close()
        print("✓ API clients cleanup completed")

        return True

    except Exception as e:
        print(f"✗ API client test failed: {e}")
        return False


async def test_configuration():
    """Test that configuration is properly loaded."""
    print("\nTesting configuration...")

    try:
        from config import config

        # Check required config attributes exist
        required_attrs = ["DISCORD_TOKEN", "SPORTS_API_KEY", "NEWS_CHANNEL_ID"]

        for attr in required_attrs:
            assert hasattr(config, attr), f"Config missing {attr}"
            value = getattr(config, attr)
            assert value is not None, f"Config {attr} is None"
            print(f"✓ Config {attr} is set")

        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("=" * 50)
    print("Cozmo Discord Bot Integration Tests")
    print("=" * 50)

    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("API Client Tests", test_api_clients),
        ("Bot Initialization Tests", test_bot_initialization),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))

        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 50)

    if passed == total:
        print("🎉 All integration tests passed! Bot is ready to run.")
        return True
    else:
        print("❌ Some tests failed. Please check the configuration and dependencies.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
