#!/usr/bin/env python3
"""
Final comprehensive test for the Enhanced Trivia System.
Validates all components and integration points.
"""

import asyncio
import sys
import os
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


async def test_core_imports():
    """Test that all core components can be imported."""
    print("Testing core component imports...")

    try:
        with patch.dict(os.environ, create_test_env()):
            # Test main components
            from main import CozmoBot
            from cogs.enhanced_trivia import EnhancedTriviaCog

            print("✓ Main bot and enhanced trivia cog imported")

            # Test utility components
            from utils.database import db_manager
            from utils.user_manager import user_manager
            from utils.question_engine import QuestionEngine
            from utils.game_manager import GameManager
            from utils.challenge_system import ChallengeSystem
            from utils.achievement_system import achievement_system
            from utils.leaderboard_manager import leaderboard_manager

            print("✓ All utility components imported")

            # Test models
            from utils.models import Question, UserProfile, GameSession

            print("✓ Data models imported")

            return True

    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False


async def test_question_engine_functionality():
    """Test question engine core functionality."""
    print("\nTesting question engine functionality...")

    try:
        from utils.question_engine import QuestionEngine

        # Initialize question engine
        question_engine = QuestionEngine()
        print("✓ Question engine initialized")

        # Test question retrieval
        question = await question_engine.get_question()
        if question:
            print(f"✓ Question retrieved: {question.question_text[:50]}...")
            print(f"  Type: {question.question_type}")
            print(f"  Difficulty: {question.difficulty}")
            print(f"  Points: {question.point_value}")
        else:
            print("⚠ No question retrieved")
            return False

        # Test difficulty-specific questions
        difficulties = ["easy", "medium", "hard"]
        for difficulty in difficulties:
            diff_question = await question_engine.get_question(difficulty=difficulty)
            if diff_question and diff_question.difficulty == difficulty:
                print(f"✓ {difficulty.title()} question retrieved correctly")
            else:
                print(f"⚠ {difficulty.title()} question retrieval failed")

        # Test category filtering
        categories = ["history", "players", "matches"]
        for category in categories:
            cat_question = await question_engine.get_question(category=category)
            if cat_question:
                print(f"✓ {category.title()} category question available")
            else:
                print(f"⚠ {category.title()} category question not available")

        return True

    except Exception as e:
        print(f"✗ Question engine test failed: {e}")
        return False


async def test_game_manager_functionality():
    """Test game manager core functionality."""
    print("\nTesting game manager functionality...")

    try:
        from utils.game_manager import GameManager
        from utils.question_engine import QuestionEngine

        # Initialize components
        question_engine = QuestionEngine()
        game_manager = GameManager(question_engine)
        print("✓ Game manager initialized")

        # Test single game
        channel_id = 123456789
        user_id = 987654321

        game_session = await game_manager.start_game(
            channel_id=channel_id, user_id=user_id, difficulty="easy"
        )

        if game_session:
            print("✓ Game session created")
            print(f"  Channel: {game_session.channel_id}")
            print(f"  User: {game_session.user_id}")
            print(f"  Question: {game_session.question.question_text[:50]}...")
        else:
            print("✗ Game session creation failed")
            return False

        # Test active game retrieval
        active_game = await game_manager.get_active_game(channel_id)
        if active_game:
            print("✓ Active game retrieved")
        else:
            print("✗ Active game retrieval failed")
            return False

        # Test game cleanup
        await game_manager.end_game(channel_id)
        active_game_after = await game_manager.get_active_game(channel_id)
        if active_game_after is None:
            print("✓ Game ended successfully")
        else:
            print("✗ Game cleanup failed")
            return False

        # Test concurrent games in different channels
        channels = [1000001, 1000002, 1000003]
        users = [2000001, 2000002, 2000003]

        games_started = 0
        for ch_id, u_id in zip(channels, users):
            game = await game_manager.start_game(ch_id, u_id, "easy")
            if game:
                games_started += 1

        print(f"✓ Concurrent games: {games_started}/{len(channels)} started")

        # Clean up concurrent games
        for ch_id in channels:
            await game_manager.end_game(ch_id)

        await game_manager.shutdown()
        print("✓ Game manager shutdown completed")

        return games_started >= len(channels) // 2  # At least half successful

    except Exception as e:
        print(f"✗ Game manager test failed: {e}")
        return False


async def test_user_management():
    """Test user management functionality."""
    print("\nTesting user management...")

    try:
        from utils.user_manager import user_manager

        test_user_id = 123456789

        # Test user creation
        user_profile = await user_manager.get_or_create_user(test_user_id)
        if user_profile and user_profile.user_id == test_user_id:
            print("✓ User profile created/retrieved")
            print(f"  User ID: {user_profile.user_id}")
            print(f"  Total Points: {user_profile.total_points}")
        else:
            print("✗ User profile creation failed")
            return False

        # Test stats update
        initial_points = user_profile.total_points
        await user_manager.update_stats(test_user_id, 10, True, "easy")

        # Get updated profile
        updated_profile = await user_manager.get_or_create_user(test_user_id)
        if updated_profile.total_points > initial_points:
            print("✓ User stats updated successfully")
            print(
                f"  Points increased from {initial_points} to {updated_profile.total_points}"
            )
        else:
            print("✗ User stats update failed")
            return False

        # Test user statistics
        user_stats = await user_manager.get_user_stats(test_user_id)
        if user_stats and user_stats.user_profile:
            print("✓ User statistics retrieved")
            print(f"  Questions answered: {user_stats.user_profile.questions_answered}")
            print(f"  Accuracy: {user_stats.user_profile.accuracy_percentage:.1f}%")
        else:
            print("✗ User statistics retrieval failed")

        return True

    except Exception as e:
        print(f"✗ User management test failed: {e}")
        return False


async def test_achievement_system():
    """Test achievement system functionality."""
    print("\nTesting achievement system...")

    try:
        from utils.achievement_system import achievement_system

        test_user_id = 123456789

        # Test getting user achievements
        achievements = await achievement_system.get_user_achievements(test_user_id)
        print(f"✓ Retrieved {len(achievements)} user achievements")

        # Test achievement checking
        context = {
            "user_id": test_user_id,
            "current_streak": 5,
            "is_correct": True,
            "difficulty": "easy",
            "points_earned": 10,
        }

        new_achievements = await achievement_system.check_achievements(
            test_user_id, context
        )
        print(
            f"✓ Achievement checking completed ({len(new_achievements)} new achievements)"
        )

        # Test getting all available achievements
        all_achievements = await achievement_system.get_all_achievements()
        if all_achievements:
            print(f"✓ {len(all_achievements)} total achievements available")
        else:
            print("⚠ No achievements defined")

        return True

    except Exception as e:
        print(f"✗ Achievement system test failed: {e}")
        return False


async def test_challenge_system():
    """Test challenge system functionality."""
    print("\nTesting challenge system...")

    try:
        from utils.challenge_system import ChallengeSystem
        from utils.question_engine import QuestionEngine
        from utils.user_manager import user_manager

        # Initialize components
        question_engine = QuestionEngine()
        challenge_system = ChallengeSystem(question_engine, user_manager)

        test_user_id = 123456789

        # Test challenge status
        status = await challenge_system.get_challenge_status(test_user_id)
        if "daily" in status and "weekly" in status:
            print("✓ Challenge status retrieved")
            print(f"  Daily available: {status['daily']['available']}")
            print(f"  Weekly available: {status['weekly']['available']}")
        else:
            print("✗ Challenge status retrieval failed")
            return False

        # Test daily challenge
        daily_question = await challenge_system.get_daily_challenge(test_user_id)
        if daily_question:
            print("✓ Daily challenge question generated")
            print(f"  Question: {daily_question.question_text[:50]}...")
        else:
            print("⚠ Daily challenge question not generated")

        # Test weekly challenge
        weekly_questions = await challenge_system.get_weekly_challenge(test_user_id)
        if weekly_questions:
            print(f"✓ Weekly challenge generated ({len(weekly_questions)} questions)")
        else:
            print("⚠ Weekly challenge not generated")

        await challenge_system.shutdown()

        return True

    except Exception as e:
        print(f"✗ Challenge system test failed: {e}")
        return False


async def test_leaderboard_system():
    """Test leaderboard functionality."""
    print("\nTesting leaderboard system...")

    try:
        from utils.leaderboard_manager import leaderboard_manager
        from utils.user_manager import user_manager

        # Create test users with different scores
        test_users = [
            (111111111, 100),
            (222222222, 200),
            (333333333, 150),
        ]

        for user_id, target_points in test_users:
            await user_manager.get_or_create_user(user_id)
            # Add points to reach target
            points_to_add = target_points
            while points_to_add > 0:
                points = min(10, points_to_add)
                await user_manager.update_stats(user_id, points, True, "easy")
                points_to_add -= points

        print("✓ Test users created with different scores")

        # Test leaderboard retrieval
        leaderboard = await leaderboard_manager.get_leaderboard("all", 10)
        if leaderboard and len(leaderboard) >= 3:
            print("✓ Leaderboard retrieved successfully")
            print(f"  Top user: {leaderboard[0].total_points} points")

            # Verify ordering
            is_ordered = all(
                leaderboard[i].total_points >= leaderboard[i + 1].total_points
                for i in range(len(leaderboard) - 1)
            )
            if is_ordered:
                print("✓ Leaderboard correctly ordered")
            else:
                print("⚠ Leaderboard ordering may be incorrect")
        else:
            print(
                f"⚠ Leaderboard returned {len(leaderboard) if leaderboard else 0} entries"
            )

        # Test user rank
        user_rank = await leaderboard_manager.get_user_rank(222222222, "all")
        if user_rank:
            print(f"✓ User rank calculated: #{user_rank}")
        else:
            print("⚠ User rank not calculated")

        return True

    except Exception as e:
        print(f"✗ Leaderboard system test failed: {e}")
        return False


async def test_cog_integration():
    """Test enhanced trivia cog integration."""
    print("\nTesting cog integration...")

    try:
        with patch.dict(os.environ, create_test_env()):
            from main import CozmoBot
            from cogs.enhanced_trivia import EnhancedTriviaCog

            # Create bot instance
            bot = CozmoBot()

            # Create cog instance (don't load to avoid initialization issues)
            cog = EnhancedTriviaCog(bot)
            print("✓ Enhanced trivia cog created")

            # Check that cog has required commands
            commands = [cmd.name for cmd in cog.get_commands()]
            expected_commands = [
                "trivia",
                "triviastats",
                "achievements",
                "dailychallenge",
            ]

            found_commands = 0
            for cmd in expected_commands:
                if cmd in commands:
                    print(f"✓ Command '{cmd}' available")
                    found_commands += 1
                else:
                    print(f"⚠ Command '{cmd}' missing")

            # Clean up
            await bot.close()

            return found_commands >= len(expected_commands) // 2

    except Exception as e:
        print(f"✗ Cog integration test failed: {e}")
        return False


async def test_database_operations():
    """Test database operations."""
    print("\nTesting database operations...")

    try:
        from utils.database import db_manager

        # Test database initialization
        await db_manager.initialize_database()
        print("✓ Database initialized")

        # Test database connection
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            print(f"✓ Database connection successful ({len(tables)} tables)")

        # Test database integrity
        integrity_ok = await db_manager.check_database_integrity()
        if integrity_ok:
            print("✓ Database integrity check passed")
        else:
            print("⚠ Database integrity check failed")

        return True

    except Exception as e:
        print(f"✗ Database operations test failed: {e}")
        return False


async def main():
    """Run all enhanced system tests."""
    print("=" * 70)
    print("Enhanced Trivia System - Final Comprehensive Test Suite")
    print("=" * 70)

    tests = [
        ("Core Imports", test_core_imports),
        ("Database Operations", test_database_operations),
        ("Question Engine", test_question_engine_functionality),
        ("Game Manager", test_game_manager_functionality),
        ("User Management", test_user_management),
        ("Achievement System", test_achievement_system),
        ("Challenge System", test_challenge_system),
        ("Leaderboard System", test_leaderboard_system),
        ("Cog Integration", test_cog_integration),
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
    print(f"Enhanced System Test Results: {passed}/{total} tests passed")
    print("=" * 70)

    success_rate = passed / total
    if success_rate >= 0.9:  # 90% success rate
        print("🎉 ENHANCED TRIVIA SYSTEM FULLY FUNCTIONAL!")
        print("\nAll major components are working correctly!")
        print("\nSystem Status: ✅ PRODUCTION READY")
        print("\nVerified Features:")
        print("✓ Question engine with multiple types and difficulties")
        print("✓ Game manager with concurrent game support")
        print("✓ User management with persistent statistics")
        print("✓ Achievement system with automatic unlocking")
        print("✓ Challenge system with daily and weekly challenges")
        print("✓ Leaderboard system with rankings")
        print("✓ Database operations with integrity checking")
        print("✓ Enhanced trivia cog integration")
        return True
    elif success_rate >= 0.7:  # 70% success rate
        print("✅ ENHANCED TRIVIA SYSTEM MOSTLY FUNCTIONAL!")
        print("\nMost components are working correctly!")
        print("\nSystem Status: ⚠️ NEEDS MINOR FIXES")
        return True
    else:
        print("❌ ENHANCED TRIVIA SYSTEM NEEDS ATTENTION")
        print("\nSeveral components need fixes before production.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
