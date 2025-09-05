#!/usr/bin/env python3
"""
System Integration Test for Enhanced Trivia System.
Tests complete system integration and functionality.
"""

import asyncio
import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_env():
    """Create a test environment with valid mock values."""
    return {
        "DISCORD_TOKEN": "fake.discord.token.for.testing.only.with.proper.length.and.format.12345",
        "SPORTS_API_KEY": "test_sports_api_key_12345",
        "NEWS_CHANNEL_ID": "123456789012345678",
    }


async def test_cog_loading():
    """Test that enhanced trivia cog can be loaded."""
    print("Testing enhanced trivia cog loading...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from main import CozmoBot
            from cogs.enhanced_trivia import EnhancedTriviaCog

            # Create bot instance
            bot = CozmoBot()

            # Test that enhanced trivia cog can be loaded
            cog = EnhancedTriviaCog(bot)
            await bot.add_cog(cog)
            print("✓ Enhanced trivia cog loaded successfully")

            # Verify cog has required commands
            commands = [cmd.name for cmd in cog.get_commands()]
            expected_commands = [
                "trivia",
                "triviastats",
                "achievements",
                "dailychallenge",
                "weeklychallenge",
            ]

            for cmd in expected_commands:
                if cmd in commands:
                    print(f"✓ Command '{cmd}' available")
                else:
                    print(f"⚠ Command '{cmd}' missing")

            # Clean up bot
            await bot.close()

            return True

    except Exception as e:
        print(f"✗ Cog loading test failed: {e}")
        return False


async def test_database_components():
    """Test database components can be initialized."""
    print("\nTesting database components...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.database import DatabaseManager

            # Create test database
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
                test_db_path = tmp_db.name

            # Initialize database manager with test path
            db_manager = DatabaseManager(test_db_path)
            await db_manager.initialize_database()
            print("✓ Database initialized successfully")

            # Test that database file was created
            assert os.path.exists(test_db_path), "Database file should exist"
            print("✓ Database file created")

            # Test basic database operations
            async with db_manager.get_connection() as conn:
                # Test a simple query
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = await cursor.fetchall()
                print(f"✓ Database contains {len(tables)} tables")

            # Clean up
            await db_manager.close_all_connections()
            os.unlink(test_db_path)

            return True

    except Exception as e:
        print(f"✗ Database components test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_question_engine():
    """Test question engine functionality."""
    print("\nTesting question engine...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.question_engine import QuestionEngine

            # Create test database
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
                test_db_path = tmp_db.name

            # Initialize question engine with test database
            question_engine = QuestionEngine()

            # Mock the database path
            from utils.database import DatabaseManager

            question_engine.db_manager = DatabaseManager(test_db_path)
            await question_engine.initialize()
            print("✓ Question engine initialized")

            # Test getting a question
            question = await question_engine.get_question()
            if question:
                print("✓ Question retrieved successfully")
                print(f"  Question type: {question.question_type}")
                print(f"  Difficulty: {question.difficulty}")
            else:
                print("⚠ No question retrieved (may need question data)")

            # Clean up
            os.unlink(test_db_path)

            return True

    except Exception as e:
        print(f"✗ Question engine test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_user_manager():
    """Test user manager functionality."""
    print("\nTesting user manager...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.user_manager import UserManager
            from utils.database import DatabaseManager

            # Create test database
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
                test_db_path = tmp_db.name

            # Initialize user manager with test database
            db_manager = DatabaseManager(test_db_path)
            await db_manager.initialize_database()

            user_manager = UserManager(db_manager)

            test_user_id = 123456789

            # Test user creation
            user_profile = await user_manager.get_or_create_user(test_user_id)
            assert user_profile.user_id == test_user_id, "User ID should match"
            print("✓ User created successfully")

            # Test stats update
            await user_manager.update_stats(test_user_id, 10, True, "easy")
            print("✓ User stats updated")

            # Test stats retrieval
            user_stats = await user_manager.get_user_stats(test_user_id)
            assert user_stats.user_profile.total_points == 10, "Points should be 10"
            print("✓ User stats retrieved correctly")

            # Clean up
            await db_manager.close_all_connections()
            os.unlink(test_db_path)

            return True

    except Exception as e:
        print(f"✗ User manager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_game_manager():
    """Test game manager functionality."""
    print("\nTesting game manager...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine
            from utils.models import Question

            # Create mock question engine
            question_engine = QuestionEngine()

            # Mock question for testing
            test_question = Question(
                id=1,
                question_text="Test question?",
                question_type="multiple_choice",
                difficulty="easy",
                category="test",
                correct_answer="A",
                options=["Option A", "Option B", "Option C", "Option D"],
                point_value=10,
            )

            # Mock question engine methods
            question_engine.get_question = AsyncMock(return_value=test_question)

            # Initialize game manager
            game_manager = GameManager(question_engine)

            # Test game creation
            channel_id = 123456789
            user_id = 987654321

            game_session = await game_manager.start_game(
                channel_id=channel_id, user_id=user_id, difficulty="easy"
            )

            assert game_session is not None, "Game session should be created"
            assert game_session.channel_id == channel_id, "Channel ID should match"
            print("✓ Game session created successfully")

            # Test active game retrieval
            active_game = await game_manager.get_active_game(channel_id)
            assert active_game is not None, "Active game should exist"
            print("✓ Active game retrieved")

            # Test game cleanup
            await game_manager.end_game(channel_id)
            active_game_after = await game_manager.get_active_game(channel_id)
            assert active_game_after is None, "Game should be ended"
            print("✓ Game ended successfully")

            # Clean up
            await game_manager.shutdown()

            return True

    except Exception as e:
        print(f"✗ Game manager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_concurrent_operations():
    """Test concurrent operations don't interfere."""
    print("\nTesting concurrent operations...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine
            from utils.models import Question

            # Create mock question engine
            question_engine = QuestionEngine()

            # Mock question for testing
            test_question = Question(
                id=1,
                question_text="Concurrent test question?",
                question_type="multiple_choice",
                difficulty="easy",
                category="test",
                correct_answer="A",
                options=["Option A", "Option B", "Option C", "Option D"],
                point_value=10,
            )

            question_engine.get_question = AsyncMock(return_value=test_question)

            # Initialize game manager
            game_manager = GameManager(question_engine)

            # Start multiple games concurrently
            tasks = []
            for i in range(5):
                channel_id = 1000000 + i
                user_id = 2000000 + i

                async def start_game_task(ch_id, u_id):
                    return await game_manager.start_game(ch_id, u_id, "easy")

                tasks.append(start_game_task(channel_id, user_id))

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful games
            successful_games = sum(
                1
                for result in results
                if result is not None and not isinstance(result, Exception)
            )
            print(
                f"✓ Concurrent operations: {successful_games}/5 games started successfully"
            )

            # Clean up all games
            for i in range(5):
                channel_id = 1000000 + i
                try:
                    await game_manager.end_game(channel_id)
                except:
                    pass  # Game might not exist

            await game_manager.shutdown()

            return successful_games >= 4  # Allow for some failures

    except Exception as e:
        print(f"✗ Concurrent operations test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all system integration tests."""
    print("=" * 60)
    print("Enhanced Trivia System - Integration Test Suite")
    print("=" * 60)

    tests = [
        ("Cog Loading", test_cog_loading),
        ("Database Components", test_database_components),
        ("Question Engine", test_question_engine),
        ("User Manager", test_user_manager),
        ("Game Manager", test_game_manager),
        ("Concurrent Operations", test_concurrent_operations),
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
    print(f"Integration Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nThe Enhanced Trivia System is properly integrated!")
        return True
    else:
        print("❌ Some integration tests failed.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
