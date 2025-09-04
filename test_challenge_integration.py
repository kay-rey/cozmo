#!/usr/bin/env python3
"""
Integration test script for the Challenge System.
Tests the complete challenge workflow without Discord dependencies.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.challenge_system import ChallengeSystem
from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.models import Question, UserProfile
from utils.database import db_manager

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockQuestionEngine:
    """Mock question engine for testing."""

    def __init__(self):
        self.questions = [
            Question(
                id=1,
                question_text="What is the capital of California?",
                question_type="multiple_choice",
                difficulty="easy",
                category="geography",
                correct_answer="Sacramento",
                options=["Los Angeles", "San Francisco", "Sacramento", "San Diego"],
                explanation="Sacramento is the capital city of California.",
                point_value=10,
            ),
            Question(
                id=2,
                question_text="What year was the LA Galaxy founded?",
                question_type="multiple_choice",
                difficulty="medium",
                category="sports",
                correct_answer="1996",
                options=["1994", "1995", "1996", "1997"],
                explanation="LA Galaxy was founded in 1996 as one of the original MLS teams.",
                point_value=20,
            ),
            Question(
                id=3,
                question_text="Who scored the most goals in World Cup history?",
                question_type="multiple_choice",
                difficulty="hard",
                category="sports",
                correct_answer="Miroslav Klose",
                options=["Pelé", "Ronaldo", "Miroslav Klose", "Gerd Müller"],
                explanation="Miroslav Klose scored 16 goals across 4 World Cups.",
                point_value=30,
            ),
        ]
        self.question_index = 0

    async def get_question(self, difficulty=None):
        """Get a mock question."""
        if difficulty:
            # Find question with matching difficulty
            for q in self.questions:
                if q.difficulty == difficulty:
                    return q

        # Return next question in sequence
        if self.question_index < len(self.questions):
            question = self.questions[self.question_index]
            self.question_index += 1
            return question

        # Reset and return first question
        self.question_index = 0
        return self.questions[0]


class MockUserManager:
    """Mock user manager for testing."""

    def __init__(self):
        self.users = {}
        self.challenge_completions = {}

    async def get_or_create_user(self, user_id):
        """Get or create a mock user."""
        if user_id not in self.users:
            self.users[user_id] = UserProfile(
                user_id=user_id,
                total_points=0,
                questions_answered=0,
                questions_correct=0,
                created_at=datetime.now(),
            )
        return self.users[user_id]

    async def can_attempt_challenge(self, user_id, challenge_type):
        """Check if user can attempt challenge."""
        today = date.today()
        key = f"{user_id}_{challenge_type}_{today}"
        return key not in self.challenge_completions

    async def update_stats(self, user_id, points, is_correct, difficulty, category):
        """Update user stats."""
        user = await self.get_or_create_user(user_id)
        user.total_points += points
        user.questions_answered += 1
        if is_correct:
            user.questions_correct += 1
        return user

    async def update_challenge_completion(self, user_id, challenge_type):
        """Mark challenge as completed."""
        today = date.today()
        key = f"{user_id}_{challenge_type}_{today}"
        self.challenge_completions[key] = True
        return True


async def test_daily_challenge():
    """Test daily challenge functionality."""
    logger.info("=== Testing Daily Challenge ===")

    # Create mock components
    question_engine = MockQuestionEngine()
    user_manager = MockUserManager()
    challenge_system = ChallengeSystem(question_engine, user_manager)

    user_id = 12345

    try:
        # Test 1: Get daily challenge
        logger.info("Test 1: Getting daily challenge...")
        question = await challenge_system.get_daily_challenge(user_id)
        assert question is not None, "Should return a question"
        assert user_id in challenge_system.active_daily_challenges, (
            "Should track active challenge"
        )
        logger.info(f"✅ Got daily challenge: {question.question_text}")

        # Test 2: Process correct answer
        logger.info("Test 2: Processing correct answer...")
        result = await challenge_system.process_daily_challenge_answer(
            user_id, is_correct=True, time_taken=15.0
        )
        assert result["success"] is True, "Should succeed"
        assert result["is_correct"] is True, "Should be correct"
        assert result["challenge_points"] == result["base_points"] * 2, (
            "Should have double points"
        )
        assert user_id not in challenge_system.active_daily_challenges, (
            "Should clean up challenge"
        )
        logger.info(f"✅ Processed correct answer: {result['challenge_points']} points")

        # Test 3: Try to get another daily challenge (should fail)
        logger.info("Test 3: Trying to get another daily challenge...")
        question2 = await challenge_system.get_daily_challenge(user_id)
        assert question2 is None, "Should not allow second daily challenge"
        logger.info("✅ Correctly prevented second daily challenge")

        logger.info("🎉 Daily challenge tests passed!")

    except Exception as e:
        logger.error(f"❌ Daily challenge test failed: {e}")
        raise
    finally:
        await challenge_system.shutdown()


async def test_weekly_challenge():
    """Test weekly challenge functionality."""
    logger.info("=== Testing Weekly Challenge ===")

    # Create mock components
    question_engine = MockQuestionEngine()
    user_manager = MockUserManager()
    challenge_system = ChallengeSystem(question_engine, user_manager)

    user_id = 54321

    try:
        # Test 1: Get weekly challenge
        logger.info("Test 1: Getting weekly challenge...")
        questions = await challenge_system.get_weekly_challenge(user_id)
        assert questions is not None, "Should return questions"
        assert len(questions) == 5, "Should return 5 questions"
        assert user_id in challenge_system.active_weekly_challenges, (
            "Should track active challenge"
        )
        logger.info(f"✅ Got weekly challenge with {len(questions)} questions")

        # Test 2: Get current question
        logger.info("Test 2: Getting current question...")
        current_q = await challenge_system.get_current_weekly_question(user_id)
        assert current_q is not None, "Should return current question"
        assert current_q == questions[0], "Should be first question"
        logger.info(f"✅ Got current question: {current_q.question_text}")

        # Test 3: Process answers for all 5 questions
        logger.info("Test 3: Processing all 5 answers...")
        correct_answers = [True, True, False, True, True]  # 4 out of 5 correct

        for i, is_correct in enumerate(correct_answers):
            result = await challenge_system.process_weekly_challenge_answer(
                user_id, is_correct=is_correct, time_taken=20.0
            )
            assert result["success"] is True, f"Question {i + 1} should succeed"
            assert result["question_number"] == i + 1, f"Should be question {i + 1}"
            logger.info(
                f"  Question {i + 1}: {'✅' if is_correct else '❌'} - {result['points']} points"
            )

        # Check final result
        assert result["is_completed"] is True, "Should be completed"
        assert result["final_score"] == "4/5", "Should have 4/5 score"
        assert result["badge_awarded"] == "weekly_excellent", (
            "Should award excellent badge"
        )
        assert user_id not in challenge_system.active_weekly_challenges, (
            "Should clean up challenge"
        )
        logger.info(
            f"✅ Completed weekly challenge: {result['final_score']} - {result['final_points']} points"
        )

        logger.info("🎉 Weekly challenge tests passed!")

    except Exception as e:
        logger.error(f"❌ Weekly challenge test failed: {e}")
        raise
    finally:
        await challenge_system.shutdown()


async def test_challenge_status():
    """Test challenge status functionality."""
    logger.info("=== Testing Challenge Status ===")

    # Create mock components
    question_engine = MockQuestionEngine()
    user_manager = MockUserManager()
    challenge_system = ChallengeSystem(question_engine, user_manager)

    user_id = 99999

    try:
        # Test 1: Get initial status
        logger.info("Test 1: Getting initial challenge status...")
        status = await challenge_system.get_challenge_status(user_id)
        assert "daily" in status, "Should have daily status"
        assert "weekly" in status, "Should have weekly status"
        assert status["daily"]["available"] is True, "Daily should be available"
        assert status["weekly"]["available"] is True, "Weekly should be available"
        logger.info("✅ Got initial status - both challenges available")

        # Test 2: Start daily challenge and check status
        logger.info("Test 2: Starting daily challenge and checking status...")
        await challenge_system.get_daily_challenge(user_id)
        status = await challenge_system.get_challenge_status(user_id)
        assert status["daily"]["active"] is True, "Daily should be active"
        logger.info("✅ Daily challenge shows as active")

        # Test 3: Cancel challenge
        logger.info("Test 3: Cancelling daily challenge...")
        cancelled = await challenge_system.cancel_active_challenge(user_id, "daily")
        assert cancelled is True, "Should successfully cancel"
        assert user_id not in challenge_system.active_daily_challenges, (
            "Should remove from active"
        )
        logger.info("✅ Successfully cancelled daily challenge")

        logger.info("🎉 Challenge status tests passed!")

    except Exception as e:
        logger.error(f"❌ Challenge status test failed: {e}")
        raise
    finally:
        await challenge_system.shutdown()


async def test_weekly_progress_tracking():
    """Test weekly challenge progress tracking."""
    logger.info("=== Testing Weekly Progress Tracking ===")

    # Create mock components
    question_engine = MockQuestionEngine()
    user_manager = MockUserManager()
    challenge_system = ChallengeSystem(question_engine, user_manager)

    user_id = 77777

    try:
        # Start weekly challenge
        logger.info("Starting weekly challenge...")
        await challenge_system.get_weekly_challenge(user_id)

        # Answer first 2 questions correctly
        await challenge_system.process_weekly_challenge_answer(user_id, True, 15.0)
        await challenge_system.process_weekly_challenge_answer(user_id, True, 18.0)

        # Test progress tracking
        logger.info("Testing progress tracking...")
        progress = await challenge_system.get_weekly_challenge_progress(user_id)
        assert progress is not None, "Should return progress"
        assert progress["current_question"] == 3, "Should be on question 3"
        assert progress["correct_answers"] == 2, "Should have 2 correct"
        assert progress["accuracy"] == 100.0, "Should have 100% accuracy so far"
        assert progress["potential_badge"] == "on_track_for_perfect", (
            "Should be on track for perfect"
        )
        logger.info(
            f"✅ Progress tracking working: {progress['current_question']}/5, {progress['correct_answers']} correct"
        )

        logger.info("🎉 Progress tracking tests passed!")

    except Exception as e:
        logger.error(f"❌ Progress tracking test failed: {e}")
        raise
    finally:
        await challenge_system.shutdown()


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Challenge System Integration Tests")

    try:
        await test_daily_challenge()
        await test_weekly_challenge()
        await test_challenge_status()
        await test_weekly_progress_tracking()

        logger.info("🎉 All tests passed! Challenge system is working correctly.")

    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
