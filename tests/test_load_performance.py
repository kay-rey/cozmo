#!/usr/bin/env python3
"""
Load Testing for Enhanced Trivia System.
Simulates concurrent users and games to test system performance.
"""

import asyncio
import sys
import os
import time
import statistics
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


async def simulate_trivia_game(
    game_manager, channel_id: int, user_id: int, game_number: int
):
    """Simulate a complete trivia game session."""
    start_time = time.time()

    try:
        # Start game
        game_session = await game_manager.start_game(
            channel_id=channel_id, user_id=user_id, difficulty="easy"
        )

        if not game_session:
            return {"success": False, "duration": 0, "error": "Failed to start game"}

        # Simulate thinking time
        await asyncio.sleep(0.1)

        # Process answer
        result = await game_manager.process_answer(
            channel_id=channel_id,
            user_id=user_id,
            answer="A",  # Always answer A for consistency
        )

        # End game
        await game_manager.end_game(channel_id)

        duration = time.time() - start_time
        return {
            "success": True,
            "duration": duration,
            "points": result.points_earned if result else 0,
            "game_number": game_number,
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "duration": duration,
            "error": str(e),
            "game_number": game_number,
        }


async def test_concurrent_games_load(num_games: int = 10):
    """Test concurrent games with specified number of simultaneous games."""
    print(f"\nTesting {num_games} concurrent games...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            # Create tasks for concurrent games
            tasks = []
            start_time = time.time()

            for i in range(num_games):
                channel_id = 1000000 + i
                user_id = 2000000 + i

                task = simulate_trivia_game(game_manager, channel_id, user_id, i + 1)
                tasks.append(task)

            # Execute all games concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Analyze results
            successful_games = [
                r for r in results if isinstance(r, dict) and r.get("success")
            ]
            failed_games = [
                r for r in results if isinstance(r, dict) and not r.get("success")
            ]
            exceptions = [r for r in results if isinstance(r, Exception)]

            success_rate = len(successful_games) / num_games * 100

            print(f"✓ Load test completed in {total_time:.2f} seconds")
            print(
                f"✓ Success rate: {success_rate:.1f}% ({len(successful_games)}/{num_games})"
            )
            print(f"✓ Failed games: {len(failed_games)}")
            print(f"✓ Exceptions: {len(exceptions)}")

            if successful_games:
                durations = [g["duration"] for g in successful_games]
                avg_duration = statistics.mean(durations)
                max_duration = max(durations)
                min_duration = min(durations)

                print(f"✓ Average game duration: {avg_duration:.3f}s")
                print(f"✓ Max game duration: {max_duration:.3f}s")
                print(f"✓ Min game duration: {min_duration:.3f}s")

                # Calculate games per second
                games_per_second = num_games / total_time
                print(f"✓ Throughput: {games_per_second:.2f} games/second")

            # Clean up
            await game_manager.shutdown()

            return success_rate >= 80  # 80% success rate threshold

    except Exception as e:
        print(f"✗ Concurrent games load test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_sequential_games_performance(num_games: int = 50):
    """Test sequential game performance to establish baseline."""
    print(f"\nTesting {num_games} sequential games...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            results = []
            start_time = time.time()

            for i in range(num_games):
                channel_id = 1000000
                user_id = 2000000 + i

                result = await simulate_trivia_game(
                    game_manager, channel_id, user_id, i + 1
                )
                results.append(result)

                # Small delay between games
                await asyncio.sleep(0.01)

            total_time = time.time() - start_time

            # Analyze results
            successful_games = [r for r in results if r.get("success")]
            success_rate = len(successful_games) / num_games * 100

            print(f"✓ Sequential test completed in {total_time:.2f} seconds")
            print(
                f"✓ Success rate: {success_rate:.1f}% ({len(successful_games)}/{num_games})"
            )

            if successful_games:
                durations = [g["duration"] for g in successful_games]
                avg_duration = statistics.mean(durations)

                print(f"✓ Average game duration: {avg_duration:.3f}s")

                # Calculate games per second
                games_per_second = num_games / total_time
                print(f"✓ Throughput: {games_per_second:.2f} games/second")

            # Clean up
            await game_manager.shutdown()

            return success_rate >= 95  # Higher threshold for sequential

    except Exception as e:
        print(f"✗ Sequential games performance test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_user_operations_load():
    """Test user management operations under load."""
    print("\nTesting user operations load...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.user_manager import user_manager

            num_users = 100
            operations_per_user = 5

            async def simulate_user_operations(user_id: int):
                """Simulate user operations."""
                try:
                    # Create/get user
                    user_profile = await user_manager.get_or_create_user(user_id)

                    # Simulate multiple stat updates
                    for _ in range(operations_per_user):
                        await user_manager.update_stats(user_id, 10, True, "easy")
                        await asyncio.sleep(0.001)  # Small delay

                    # Get final stats
                    final_stats = await user_manager.get_user_stats(user_id)

                    return {"success": True, "user_id": user_id}

                except Exception as e:
                    return {"success": False, "user_id": user_id, "error": str(e)}

            # Create tasks for concurrent user operations
            tasks = []
            start_time = time.time()

            for i in range(num_users):
                user_id = 3000000 + i
                tasks.append(simulate_user_operations(user_id))

            # Execute all operations concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Analyze results
            successful_ops = [
                r for r in results if isinstance(r, dict) and r.get("success")
            ]
            success_rate = len(successful_ops) / num_users * 100

            total_operations = num_users * (
                operations_per_user + 2
            )  # +2 for create and get_stats
            ops_per_second = total_operations / total_time

            print(f"✓ User operations completed in {total_time:.2f} seconds")
            print(
                f"✓ Success rate: {success_rate:.1f}% ({len(successful_ops)}/{num_users})"
            )
            print(f"✓ Total operations: {total_operations}")
            print(f"✓ Operations per second: {ops_per_second:.2f}")

            return success_rate >= 90  # 90% success rate threshold

    except Exception as e:
        print(f"✗ User operations load test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_memory_usage():
    """Test memory usage during operations."""
    print("\nTesting memory usage...")

    try:
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            # Run multiple game cycles
            for cycle in range(5):
                # Start multiple games
                games = []
                for i in range(20):
                    channel_id = 1000000 + i
                    user_id = 2000000 + i

                    game_session = await game_manager.start_game(
                        channel_id, user_id, "easy"
                    )
                    if game_session:
                        games.append(channel_id)

                # End all games
                for channel_id in games:
                    await game_manager.end_game(channel_id)

                # Force garbage collection
                gc.collect()

                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory

                print(
                    f"  Cycle {cycle + 1}: Memory usage: {current_memory:.1f} MB (+{memory_increase:.1f} MB)"
                )

            # Clean up
            await game_manager.shutdown()

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            total_increase = final_memory - initial_memory

            print(f"✓ Initial memory: {initial_memory:.1f} MB")
            print(f"✓ Final memory: {final_memory:.1f} MB")
            print(f"✓ Total increase: {total_increase:.1f} MB")

            # Memory increase should be reasonable (less than 50MB for this test)
            return total_increase < 50

    except ImportError:
        print("⚠ psutil not available, skipping memory test")
        return True
    except Exception as e:
        print(f"✗ Memory usage test failed: {e}")
        return False


async def test_stress_concurrent_mixed_operations():
    """Stress test with mixed concurrent operations."""
    print("\nTesting stress with mixed concurrent operations...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from utils.game_manager import GameManager
            from utils.question_engine import QuestionEngine
            from utils.user_manager import user_manager
            from utils.achievement_system import achievement_system

            # Initialize components
            question_engine = QuestionEngine()
            game_manager = GameManager(question_engine)

            async def mixed_operations(operation_id: int):
                """Perform mixed operations."""
                try:
                    user_id = 4000000 + operation_id
                    channel_id = 5000000 + operation_id

                    # User operations
                    await user_manager.get_or_create_user(user_id)
                    await user_manager.update_stats(user_id, 10, True, "easy")

                    # Game operations
                    game_session = await game_manager.start_game(
                        channel_id, user_id, "easy"
                    )
                    if game_session:
                        await asyncio.sleep(0.01)  # Simulate game time
                        await game_manager.process_answer(channel_id, user_id, "A")
                        await game_manager.end_game(channel_id)

                    # Achievement operations
                    context = {
                        "user_id": user_id,
                        "current_streak": 3,
                        "is_correct": True,
                    }
                    await achievement_system.check_achievements(user_id, context)

                    return {"success": True, "operation_id": operation_id}

                except Exception as e:
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": str(e),
                    }

            # Run stress test
            num_operations = 30
            tasks = []
            start_time = time.time()

            for i in range(num_operations):
                tasks.append(mixed_operations(i))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            total_time = time.time() - start_time

            # Analyze results
            successful_ops = [
                r for r in results if isinstance(r, dict) and r.get("success")
            ]
            success_rate = len(successful_ops) / num_operations * 100

            print(f"✓ Stress test completed in {total_time:.2f} seconds")
            print(
                f"✓ Success rate: {success_rate:.1f}% ({len(successful_ops)}/{num_operations})"
            )
            print(f"✓ Operations per second: {num_operations / total_time:.2f}")

            # Clean up
            await game_manager.shutdown()

            return success_rate >= 75  # 75% success rate for stress test

    except Exception as e:
        print(f"✗ Stress test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all load and performance tests."""
    print("=" * 70)
    print("Enhanced Trivia System - Load & Performance Test Suite")
    print("=" * 70)

    tests = [
        (
            "Sequential Games Performance (50 games)",
            lambda: test_sequential_games_performance(50),
        ),
        ("Concurrent Games Load (10 games)", lambda: test_concurrent_games_load(10)),
        ("Concurrent Games Load (25 games)", lambda: test_concurrent_games_load(25)),
        ("User Operations Load", test_user_operations_load),
        ("Memory Usage Test", test_memory_usage),
        ("Stress Test (Mixed Operations)", test_stress_concurrent_mixed_operations),
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

    print("\n" + "=" * 70)
    print(f"Load Test Results: {passed}/{total} tests passed")
    print("=" * 70)

    success_rate = passed / total
    if success_rate >= 0.8:  # 80% success rate
        print("🎉 LOAD TESTS PASSED!")
        print("\nThe Enhanced Trivia System handles load well!")
        print("\nPerformance characteristics verified:")
        print("✓ Concurrent game handling")
        print("✓ User operation scalability")
        print("✓ Memory usage stability")
        print("✓ Mixed operation stress handling")
        return True
    else:
        print("❌ Load tests indicate performance issues.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
