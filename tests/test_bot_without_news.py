#!/usr/bin/env python3
"""
Test script for Cozmo Discord Bot without news feature.
Tests the three main features: matchday, stats, and trivia.
"""

import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress logging during tests
logging.disable(logging.CRITICAL)


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        from config import config

        print("✓ Config module imported successfully")
    except Exception as e:
        print(f"✗ Config import failed: {e}")
        return False

    try:
        from main import CozmoBot

        print("✓ Main bot class imported successfully")
    except Exception as e:
        print(f"✗ Main bot import failed: {e}")
        return False

    # Test individual cogs
    cogs_to_test = ["matchday", "stats", "trivia"]
    for cog_name in cogs_to_test:
        try:
            __import__(f"cogs.{cog_name}")
            print(f"✓ Cog cogs.{cog_name} imported successfully")
        except Exception as e:
            print(f"✗ Cog cogs.{cog_name} import failed: {e}")
            return False

    return True


async def test_bot_creation():
    """Test bot creation and cog loading."""
    print("\nTesting bot creation...")

    try:
        from main import CozmoBot

        bot = CozmoBot()
        print("✓ Bot instance created successfully")

        # Test setup hook (cog loading)
        await bot.setup_hook()
        print("✓ Setup hook completed (cogs loaded)")

        # Check loaded cogs
        loaded_cogs = [cog.__class__.__name__ for cog in bot.cogs.values()]
        print(f"Loaded cogs: {loaded_cogs}")

        expected_cogs = ["MatchdayCog", "StatsCog", "TriviaCog"]
        for expected_cog in expected_cogs:
            if expected_cog in loaded_cogs:
                print(f"✓ {expected_cog} loaded successfully")
            else:
                print(f"✗ {expected_cog} not loaded")
                return False

        # Check commands
        commands = [cmd.name for cmd in bot.commands]
        print(f"Registered commands: {commands}")

        expected_commands = ["nextmatch", "standings", "playerstats", "trivia"]
        for expected_cmd in expected_commands:
            if expected_cmd in commands:
                print(f"✓ Command '{expected_cmd}' registered")
            else:
                print(f"✗ Command '{expected_cmd}' not registered")
                return False

        # Cleanup
        await bot.close()
        print("✓ Bot cleanup completed")

        return True

    except Exception as e:
        print(f"✗ Bot creation failed: {e}")
        return False


def test_api_clients():
    """Test API client initialization."""
    print("\nTesting API clients...")

    try:
        from api.sports_api import sports_client
        from api.news_api import news_client

        print("✓ API clients imported successfully")
        return True
    except Exception as e:
        print(f"✗ API client import failed: {e}")
        return False


def test_trivia_questions():
    """Test trivia questions data."""
    print("\nTesting trivia questions...")

    try:
        from trivia_questions import QUESTIONS

        if not QUESTIONS:
            print("✗ No trivia questions found")
            return False

        print(f"✓ {len(QUESTIONS)} trivia questions loaded")

        # Validate question structure
        for i, question in enumerate(QUESTIONS):
            required_keys = ["question", "options", "correct_answer"]
            for key in required_keys:
                if key not in question:
                    print(f"✗ Question {i + 1} missing key: {key}")
                    return False

            if len(question["options"]) != 4:
                print(f"✗ Question {i + 1} doesn't have 4 options")
                return False

            if not (0 <= question["correct_answer"] <= 3):
                print(f"✗ Question {i + 1} has invalid correct_answer index")
                return False

        print("✓ All trivia questions validated")
        return True

    except Exception as e:
        print(f"✗ Trivia questions test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Cozmo Discord Bot Test (Without News Feature)")
    print("=" * 60)

    tests = [
        ("Import Tests", test_imports),
        ("API Client Tests", test_api_clients),
        ("Trivia Questions Tests", test_trivia_questions),
        ("Bot Creation Tests", test_bot_creation),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 All tests passed! The bot is ready to run.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
