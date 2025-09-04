#!/usr/bin/env python3
"""
Simple integration test to verify the challenge system components work together.
"""

import asyncio
import logging
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_imports():
    """Test that all components can be imported successfully."""
    logger.info("=== Testing Imports ===")

    try:
        # Test challenge system import
        from utils.challenge_system import ChallengeSystem, CHALLENGE_BADGES

        logger.info("✅ Challenge system imported successfully")

        # Test enhanced trivia cog import
        from cogs.enhanced_trivia import EnhancedTriviaCog

        logger.info("✅ Enhanced trivia cog imported successfully")

        # Test models import
        from utils.models import Question, UserProfile

        logger.info("✅ Models imported successfully")

        # Verify challenge badges are defined
        assert len(CHALLENGE_BADGES) > 0, "Should have challenge badges defined"
        assert "weekly_perfect" in CHALLENGE_BADGES, "Should have weekly_perfect badge"
        logger.info(f"✅ Found {len(CHALLENGE_BADGES)} challenge badges")

        logger.info("🎉 All imports successful!")
        return True

    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        return False


async def test_basic_functionality():
    """Test basic functionality without Discord dependencies."""
    logger.info("=== Testing Basic Functionality ===")

    try:
        from utils.challenge_system import ChallengeSystem
        from utils.models import Question
        from unittest.mock import AsyncMock

        # Create mock components
        mock_question_engine = AsyncMock()
        mock_question_engine.get_question.return_value = Question(
            id=1, question_text="Test question?", difficulty="medium", point_value=20
        )

        mock_user_manager = AsyncMock()
        mock_user_manager.can_attempt_challenge.return_value = True
        mock_user_manager.update_stats.return_value = None
        mock_user_manager.update_challenge_completion.return_value = True

        # Create challenge system
        challenge_system = ChallengeSystem(mock_question_engine, mock_user_manager)

        # Test basic operations
        user_id = 12345

        # Test getting challenge status
        status = await challenge_system.get_challenge_status(user_id)
        assert "daily" in status, "Should have daily status"
        assert "weekly" in status, "Should have weekly status"
        logger.info("✅ Challenge status retrieval works")

        # Test cancelling non-existent challenge
        result = await challenge_system.cancel_active_challenge(user_id, "daily")
        assert result is False, "Should return False for non-existent challenge"
        logger.info("✅ Challenge cancellation works")

        # Clean up
        await challenge_system.shutdown()
        logger.info("✅ Challenge system shutdown works")

        logger.info("🎉 Basic functionality tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Basic functionality test failed: {e}")
        return False


async def test_command_structure():
    """Test that the command structure is correct."""
    logger.info("=== Testing Command Structure ===")

    try:
        from cogs.enhanced_trivia import EnhancedTriviaCog
        from unittest.mock import MagicMock

        # Create mock bot
        bot = MagicMock()

        # Create cog
        cog = EnhancedTriviaCog(bot)

        # Check that commands exist
        assert hasattr(cog, "daily_challenge"), "Should have daily_challenge command"
        assert hasattr(cog, "weekly_challenge"), "Should have weekly_challenge command"
        assert hasattr(cog, "challenge_progress"), (
            "Should have challenge_progress command"
        )
        logger.info("✅ All expected commands exist")

        # Check that helper methods exist
        assert hasattr(cog, "_create_challenge_embed"), (
            "Should have _create_challenge_embed method"
        )
        assert hasattr(cog, "_handle_challenge_result"), (
            "Should have _handle_challenge_result method"
        )
        logger.info("✅ All expected helper methods exist")

        logger.info("🎉 Command structure tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Command structure test failed: {e}")
        return False


async def main():
    """Run all simple integration tests."""
    logger.info("🚀 Starting Simple Integration Tests")

    tests_passed = 0
    total_tests = 3

    # Run tests
    if await test_imports():
        tests_passed += 1

    if await test_basic_functionality():
        tests_passed += 1

    if await test_command_structure():
        tests_passed += 1

    # Report results
    logger.info(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        logger.info(
            "🎉 All simple integration tests passed! The challenge system is ready to use."
        )
        return True
    else:
        logger.error(f"❌ {total_tests - tests_passed} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
