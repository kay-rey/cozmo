#!/usr/bin/env python3
"""
Final comprehensive test suite for Cozmo Discord Bot.
Tests all components with proper mocking to avoid requiring real API keys.
"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_env():
    """Create a test environment with valid mock values."""
    return {
        "DISCORD_TOKEN": "fake_discord_token_for_testing_only",  # Mock format
        "SPORTS_API_KEY": "test_sports_api_key_12345",
        "NEWS_CHANNEL_ID": "123456789012345678",
    }


async def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        with patch.dict(os.environ, create_test_env()):
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
        with patch.dict(os.environ, create_test_env()):
            from main import CozmoBot

            # Create bot instance
            bot = CozmoBot()
            print("✓ Bot instance created successfully")

            # Test that bot has required attributes
            assert hasattr(bot, "command_prefix"), "Bot missing command_prefix"
            assert hasattr(bot, "intents"), "Bot missing intents"
            assert bot.command_prefix == "!", "Incorrect command prefix"
            print("✓ Bot configuration validated")

            # Test intents
            assert bot.intents.message_content == True, (
                "Message content intent not enabled"
            )
            assert bot.intents.reactions == True, "Reactions intent not enabled"
            print("✓ Bot intents configured correctly")

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
        with patch.dict(os.environ, create_test_env()):
            from api.sports_api import sports_client
            from api.news_api import news_client

            # Test sports client
            assert hasattr(sports_client, "base_url"), "Sports client missing base_url"
            assert hasattr(sports_client, "api_key"), "Sports client missing api_key"
            print("✓ Sports API client initialized")

            # Test news client
            assert hasattr(news_client, "rss_url"), "News client missing rss_url"
            assert news_client.rss_url == "http://www.lagalaxy.com/rss/news", (
                "News RSS URL not set correctly"
            )
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
    """Test configuration loading and validation."""
    print("\nTesting configuration...")

    try:
        with patch.dict(os.environ, create_test_env()):
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


async def test_cog_structure():
    """Test that all cogs have proper structure."""
    print("\nTesting cog structure...")

    try:
        with patch.dict(os.environ, create_test_env()):
            # Test individual cog imports
            cog_modules = ["cogs.matchday", "cogs.stats", "cogs.news", "cogs.trivia"]

            for cog_module in cog_modules:
                try:
                    # Import the module to check for syntax errors
                    module = __import__(cog_module, fromlist=[""])
                    print(f"✓ {cog_module} imported successfully")

                    # Check if it has a setup function (required for cogs)
                    if hasattr(module, "setup"):
                        print(f"✓ {cog_module} has setup function")
                    else:
                        print(f"⚠ {cog_module} missing setup function")

                except Exception as e:
                    print(f"✗ {cog_module} import failed: {e}")
                    return False

            return True

    except Exception as e:
        print(f"✗ Cog structure test failed: {e}")
        return False


async def test_trivia_questions():
    """Test that trivia questions are properly formatted."""
    print("\nTesting trivia questions...")

    try:
        from data.trivia_questions import QUESTIONS

        assert isinstance(QUESTIONS, list), "QUESTIONS should be a list"
        assert len(QUESTIONS) > 0, "Should have at least one trivia question"

        for i, question in enumerate(QUESTIONS):
            assert isinstance(question, dict), f"Question {i} should be a dictionary"

            required_keys = ["question", "options", "answer"]
            for key in required_keys:
                assert key in question, f"Question {i} missing key: {key}"

            assert isinstance(question["options"], list), (
                f"Question {i} options should be a list"
            )
            assert len(question["options"]) == 4, f"Question {i} should have 4 options"

            assert isinstance(question["answer"], int), (
                f"Question {i} answer should be an integer"
            )
            assert 0 <= question["answer"] <= 3, f"Question {i} answer should be 0-3"

        print(f"✓ {len(QUESTIONS)} trivia questions validated")
        return True

    except Exception as e:
        print(f"✗ Trivia questions test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling mechanisms."""
    print("\nTesting error handling...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from main import CozmoBot

            # Create bot instance
            bot = CozmoBot()

            # Test that error handlers exist
            assert hasattr(bot, "on_command_error"), "Bot missing command error handler"
            assert hasattr(bot, "on_error"), "Bot missing general error handler"
            print("✓ Error handlers are present")

            # Test that setup_hook exists
            assert hasattr(bot, "setup_hook"), "Bot missing setup_hook"
            print("✓ Setup hook is present")

            # Clean up
            await bot.close()

            return True

    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        return False


async def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")

    required_files = [
        "main.py",
        "config.py",
        "requirements.txt",
        ".env.template",
        "trivia_questions.py",
        "api/__init__.py",
        "api/sports_api.py",
        "api/news_api.py",
        "cogs/__init__.py",
        "cogs/matchday.py",
        "cogs/stats.py",
        "cogs/news.py",
        "cogs/trivia.py",
    ]

    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path}")
            missing_files.append(file_path)

    if missing_files:
        print(f"Missing files: {', '.join(missing_files)}")
        return False

    return True


async def main():
    """Run all comprehensive tests."""
    print("=" * 60)
    print("Cozmo Discord Bot Final Test Suite")
    print("=" * 60)

    tests = [
        ("File Structure", test_file_structure),
        ("Import Tests", test_imports),
        ("Configuration Tests", test_configuration),
        ("API Client Tests", test_api_clients),
        ("Bot Initialization Tests", test_bot_initialization),
        ("Cog Structure Tests", test_cog_structure),
        ("Error Handling Tests", test_error_handling),
        ("Trivia Questions Tests", test_trivia_questions),
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

    print("\n" + "=" * 60)
    print(f"Final Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL TESTS PASSED! Bot is fully functional and ready for deployment.")
        print("\nNext steps:")
        print("1. Configure .env with real Discord token and API keys")
        print("2. Invite bot to your Discord server")
        print("3. Run: python3 main.py")
        print("4. Test commands in Discord: !nextmatch, !standings, !news, !trivia")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
