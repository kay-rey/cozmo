#!/usr/bin/env python3
"""
Simple Load Test for Enhanced Trivia System.
Tests basic load handling with proper channel separation.
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_test_env():
    """Create a test environment with valid mock values."""
    return {
        "DISCORD_TOKEN": "fake.discord.token.for.testing.only.with.proper.length.and.format.12345",
        "SPORTS_API_KEY": "test_sports_api_key_12345",
        "NEWS_CHANNEL_ID": "123456789012345678",
    }


async def test_concurrent_games_simple():
    """Test concurrent games with proper channel separation."""
    print("Testing concurrent games with proper channel separation...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            # Test concurrent games in different channels
            num_games = 10
            start_time = time.time()

            # Start games concurrently
            tasks = []
            for i in range(num_games):
                channel_id = 1000000 + i  # Different channel for each game
                user_id = 2000000 + i

                async def start_and_complete_game(ch_id, u_id):
                    try:
                        # Start game
                        game_session = await game_manager.start_game(
                            ch_id, u_id, "easy"
                        )
                        if not game_session:
                            return False

                        # Process answer
                        result = await game_manager.process_answer(ch_id, u_id, "A")

                        # End game
                        await game_manager.end_game(ch_id)

                        return True
                    except Exception as e:
                        print(f"Game error: {e}")
                        return False

                tasks.append(start_and_complete_game(channel_id, user_id))

            # Execute all games concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time
            successful_games = sum(1 for r in results if r is True)

            print(f"✓ Completed {successful_games}/{num_games} concurrent games")
            print(f"✓ Total time: {total_time:.2f} seconds")
            print(f"✓ Success rate: {successful_games / num_games * 100:.1f}%")
            print(f"✓ Games per second: {num_games / total_time:.2f}")

            # Clean up
            await game_manager.shutdown()

            return successful_games >= num_games * 0.8  # 80% success rate

    except Exception as e:
        print(f"✗ Concurrent games test failed: {e}")
        return False


async def test_sequential_games():
    """Test sequential games for baseline performance."""
    print("\nTesting sequential games...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            num_games = 20
            successful_games = 0
            start_time = time.time()

            for i in range(num_games):
                channel_id = 1000000  # Same channel, sequential games
                user_id = 2000000 + i

                try:
                    # Start game
                    game_session = await game_manager.start_game(
                        channel_id, user_id, "easy"
                    )
                    if game_session:
                        # Process answer
                        await game_manager.process_answer(channel_id, user_id, "A")
                        # End game
                        await game_manager.end_game(channel_id)
                        successful_games += 1

                    # Small delay between games
                    await asyncio.sleep(0.01)

                except Exception as e:
                    print(f"Sequential game {i} error: {e}")

            total_time = time.time() - start_time

            print(f"✓ Completed {successful_games}/{num_games} sequential games")
            print(f"✓ Total time: {total_time:.2f} seconds")
            print(f"✓ Success rate: {successful_games / num_games * 100:.1f}%")
            print(f"✓ Games per second: {num_games / total_time:.2f}")

            # Clean up
            await game_manager.shutdown()

            return (
                successful_games >= num_games * 0.9
            )  # 90% success rate for sequential

    except Exception as e:
        print(f"✗ Sequential games test failed: {e}")
        return False


async def test_user_operations():
    """Test user management operations."""
    print("\nTesting user operations...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.user_manager import user_manager

            num_users = 50
            start_time = time.time()

            # Test concurrent user operations
            async def user_operations(user_id):
                try:
                    # Create/get user
                    await user_manager.get_or_create_user(user_id)

                    # Update stats multiple times
                    for _ in range(3):
                        await user_manager.update_stats(user_id, 10, True, "easy")

                    # Get final stats
                    await user_manager.get_user_stats(user_id)

                    return True
                except Exception as e:
                    print(f"User operation error: {e}")
                    return False

            # Run operations concurrently
            tasks = [user_operations(3000000 + i) for i in range(num_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time
            successful_ops = sum(1 for r in results if r is True)

            print(f"✓ Completed {successful_ops}/{num_users} user operations")
            print(f"✓ Total time: {total_time:.2f} seconds")
            print(f"✓ Success rate: {successful_ops / num_users * 100:.1f}%")
            print(
                f"✓ Operations per second: {num_users * 4 / total_time:.2f}"
            )  # 4 ops per user

            return successful_ops >= num_users * 0.9  # 90% success rate

    except Exception as e:
        print(f"✗ User operations test failed: {e}")
        return False


async def main():
    """Run simple load tests."""
    print("=" * 60)
    print("Enhanced Trivia System - Simple Load Tests")
    print("=" * 60)

    tests = [
        ("Sequential Games", test_sequential_games),
        ("Concurrent Games", test_concurrent_games_simple),
        ("User Operations", test_user_operations),
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
    print(f"Load Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 ALL LOAD TESTS PASSED!")
        print("\nThe Enhanced Trivia System handles load well!")
        return True
    elif passed >= total * 0.8:
        print("✅ MOST LOAD TESTS PASSED!")
        print("\nThe Enhanced Trivia System shows good performance!")
        return True
    else:
        print("❌ Load tests indicate performance issues.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
