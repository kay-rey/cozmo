"""
Test suite for the Challenge System.
Tests daily and weekly challenge functionality.
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from utils.challenge_system import ChallengeSystem
from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.models import Question, UserProfile


@pytest.fixture
async def mock_question_engine():
    """Create a mock question engine."""
    engine = AsyncMock(spec=QuestionEngine)

    # Mock question
    mock_question = Question(
        id=1,
        question_text="Test question?",
        question_type="multiple_choice",
        difficulty="medium",
        category="test",
        correct_answer="A",
        options=["Option A", "Option B", "Option C", "Option D"],
        explanation="Test explanation",
        point_value=20,
    )

    engine.get_question.return_value = mock_question
    return engine


@pytest.fixture
async def mock_user_manager():
    """Create a mock user manager."""
    manager = AsyncMock(spec=UserManager)

    # Mock user profile
    mock_user = UserProfile(
        user_id=12345,
        total_points=100,
        questions_answered=10,
        questions_correct=8,
    )

    manager.get_or_create_user.return_value = mock_user
    manager.can_attempt_challenge.return_value = True
    manager.update_stats.return_value = mock_user
    manager.update_challenge_completion.return_value = True

    return manager


@pytest.fixture
async def challenge_system(mock_question_engine, mock_user_manager):
    """Create a challenge system instance."""
    system = ChallengeSystem(mock_question_engine, mock_user_manager)
    yield system
    await system.shutdown()


class TestDailyChallenge:
    """Test daily challenge functionality."""

    @pytest.mark.asyncio
    async def test_get_daily_challenge_success(
        self, challenge_system, mock_user_manager
    ):
        """Test successful daily challenge creation."""
        user_id = 12345

        # Mock that user can attempt challenge
        mock_user_manager.can_attempt_challenge.return_value = True

        # Get daily challenge
        question = await challenge_system.get_daily_challenge(user_id)

        # Verify question was returned
        assert question is not None
        assert question.question_text == "Test question?"
        assert user_id in challenge_system.active_daily_challenges

        # Verify challenge data
        challenge_data = challenge_system.active_daily_challenges[user_id]
        assert challenge_data["question"] == question
        assert challenge_data["max_attempts"] == 1

    @pytest.mark.asyncio
    async def test_get_daily_challenge_already_completed(
        self, challenge_system, mock_user_manager
    ):
        """Test daily challenge when already completed."""
        user_id = 12345

        # Mock that user cannot attempt challenge (already completed)
        mock_user_manager.can_attempt_challenge.return_value = False

        # Get daily challenge
        question = await challenge_system.get_daily_challenge(user_id)

        # Verify no question was returned
        assert question is None
        assert user_id not in challenge_system.active_daily_challenges

    @pytest.mark.asyncio
    async def test_process_daily_challenge_answer_correct(
        self, challenge_system, mock_user_manager
    ):
        """Test processing correct daily challenge answer."""
        user_id = 12345

        # Set up active challenge
        mock_question = Question(
            id=1,
            question_text="Test question?",
            difficulty="medium",
            point_value=20,
            explanation="Test explanation",
        )

        challenge_system.active_daily_challenges[user_id] = {
            "question": mock_question,
            "start_time": datetime.now(),
            "attempts": 0,
            "max_attempts": 1,
        }

        # Process correct answer
        result = await challenge_system.process_daily_challenge_answer(
            user_id, is_correct=True, time_taken=15.0
        )

        # Verify result
        assert result["success"] is True
        assert result["is_correct"] is True
        assert result["base_points"] == 20
        assert result["challenge_points"] == 40  # Double points
        assert result["challenge_type"] == "daily"

        # Verify challenge was cleaned up
        assert user_id not in challenge_system.active_daily_challenges

        # Verify user manager calls
        mock_user_manager.update_stats.assert_called_once_with(
            user_id, 40, True, "medium", mock_question.category
        )
        mock_user_manager.update_challenge_completion.assert_called_once_with(
            user_id, "daily"
        )

    @pytest.mark.asyncio
    async def test_process_daily_challenge_answer_incorrect(
        self, challenge_system, mock_user_manager
    ):
        """Test processing incorrect daily challenge answer."""
        user_id = 12345

        # Set up active challenge
        mock_question = Question(
            id=1,
            question_text="Test question?",
            difficulty="medium",
            point_value=20,
            explanation="Test explanation",
        )

        challenge_system.active_daily_challenges[user_id] = {
            "question": mock_question,
            "start_time": datetime.now(),
            "attempts": 0,
            "max_attempts": 1,
        }

        # Process incorrect answer
        result = await challenge_system.process_daily_challenge_answer(
            user_id, is_correct=False, time_taken=25.0
        )

        # Verify result
        assert result["success"] is True
        assert result["is_correct"] is False
        assert result["base_points"] == 0
        assert result["challenge_points"] == 0  # No points for incorrect

        # Verify challenge was cleaned up
        assert user_id not in challenge_system.active_daily_challenges


class TestWeeklyChallenge:
    """Test weekly challenge functionality."""

    @pytest.mark.asyncio
    async def test_get_weekly_challenge_success(
        self, challenge_system, mock_user_manager, mock_question_engine
    ):
        """Test successful weekly challenge creation."""
        user_id = 12345

        # Mock that user can attempt challenge
        mock_user_manager.can_attempt_challenge.return_value = True

        # Mock multiple questions for weekly challenge
        questions = []
        for i in range(5):
            question = Question(
                id=i + 1,
                question_text=f"Question {i + 1}?",
                difficulty=["easy", "easy", "medium", "medium", "hard"][i],
                point_value=[10, 10, 20, 20, 30][i],
            )
            questions.append(question)

        mock_question_engine.get_question.side_effect = questions

        # Get weekly challenge
        result_questions = await challenge_system.get_weekly_challenge(user_id)

        # Verify questions were returned
        assert result_questions is not None
        assert len(result_questions) == 5
        assert user_id in challenge_system.active_weekly_challenges

        # Verify challenge data
        challenge_data = challenge_system.active_weekly_challenges[user_id]
        assert len(challenge_data["questions"]) == 5
        assert challenge_data["current_question"] == 0
        assert challenge_data["correct_answers"] == 0

    @pytest.mark.asyncio
    async def test_get_current_weekly_question(self, challenge_system):
        """Test getting current weekly question."""
        user_id = 12345

        # Set up active weekly challenge
        questions = [
            Question(id=1, question_text="Question 1?"),
            Question(id=2, question_text="Question 2?"),
        ]

        challenge_system.active_weekly_challenges[user_id] = {
            "questions": questions,
            "current_question": 0,
            "correct_answers": 0,
            "total_points": 0,
            "answers": [],
        }

        # Get current question
        current = await challenge_system.get_current_weekly_question(user_id)

        # Verify correct question returned
        assert current is not None
        assert current.id == 1
        assert current.question_text == "Question 1?"

    @pytest.mark.asyncio
    async def test_process_weekly_challenge_answer(
        self, challenge_system, mock_user_manager
    ):
        """Test processing weekly challenge answer."""
        user_id = 12345

        # Set up active weekly challenge
        questions = [Question(id=1, question_text="Question 1?", point_value=20)]

        challenge_system.active_weekly_challenges[user_id] = {
            "questions": questions,
            "start_time": datetime.now(),
            "current_question": 0,
            "correct_answers": 0,
            "total_points": 0,
            "answers": [],
        }

        # Process correct answer
        result = await challenge_system.process_weekly_challenge_answer(
            user_id, is_correct=True, time_taken=15.0
        )

        # Verify result
        assert result["success"] is True
        assert result["is_correct"] is True
        assert result["points"] == 20
        assert result["question_number"] == 1
        assert result["correct_so_far"] == 1
        assert result["challenge_type"] == "weekly"

        # Verify challenge data updated
        challenge_data = challenge_system.active_weekly_challenges[user_id]
        assert challenge_data["current_question"] == 1
        assert challenge_data["correct_answers"] == 1
        assert challenge_data["total_points"] == 20
        assert len(challenge_data["answers"]) == 1

    @pytest.mark.asyncio
    async def test_weekly_challenge_completion(
        self, challenge_system, mock_user_manager
    ):
        """Test weekly challenge completion with badge award."""
        user_id = 12345

        # Set up weekly challenge at final question
        questions = [Question(id=i, point_value=20) for i in range(5)]

        challenge_system.active_weekly_challenges[user_id] = {
            "questions": questions,
            "start_time": datetime.now(),
            "current_question": 4,  # Last question
            "correct_answers": 4,  # 4 correct so far
            "total_points": 80,  # 4 * 20 points
            "answers": [{"is_correct": True} for _ in range(4)],
        }

        # Process final correct answer
        with patch.object(challenge_system, "_award_challenge_badge") as mock_award:
            result = await challenge_system.process_weekly_challenge_answer(
                user_id, is_correct=True, time_taken=15.0
            )

        # Verify completion
        assert result["is_completed"] is True
        assert result["final_score"] == "5/5"
        assert result["base_points"] == 100
        assert result["final_points"] == 300  # Triple points
        assert result["badge_awarded"] == "weekly_perfect"

        # Verify challenge cleaned up
        assert user_id not in challenge_system.active_weekly_challenges

        # Verify badge awarded
        mock_award.assert_called_once_with(user_id, "weekly_perfect")


class TestChallengeStatus:
    """Test challenge status functionality."""

    @pytest.mark.asyncio
    async def test_get_challenge_status(self, challenge_system, mock_user_manager):
        """Test getting challenge status."""
        user_id = 12345

        # Mock user manager responses
        mock_user_manager.can_attempt_challenge.side_effect = (
            lambda uid, ctype: ctype == "daily"
        )

        # Get status
        status = await challenge_system.get_challenge_status(user_id)

        # Verify status structure
        assert "daily" in status
        assert "weekly" in status
        assert status["daily"]["available"] is True
        assert status["weekly"]["available"] is False

    @pytest.mark.asyncio
    async def test_cancel_active_challenge(self, challenge_system):
        """Test cancelling active challenges."""
        user_id = 12345

        # Set up active challenges
        challenge_system.active_daily_challenges[user_id] = {"test": "data"}
        challenge_system.active_weekly_challenges[user_id] = {"test": "data"}

        # Cancel daily challenge
        result = await challenge_system.cancel_active_challenge(user_id, "daily")
        assert result is True
        assert user_id not in challenge_system.active_daily_challenges

        # Cancel weekly challenge
        result = await challenge_system.cancel_active_challenge(user_id, "weekly")
        assert result is True
        assert user_id not in challenge_system.active_weekly_challenges


if __name__ == "__main__":
    pytest.main([__file__])
