"""
Integration tests for complete trivia game workflows.
Tests end-to-end functionality across multiple components.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add the parent directory to the path so we can import our modules
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.question_engine import QuestionEngine
from utils.user_manager import UserManager
from utils.scoring_engine import ScoringEngine
from utils.database import DatabaseManager
from utils.models import Question, UserProfile, GameSession


class TestCompleteWorkflowIntegration:
    """Integration tests for complete trivia game workflows."""

    @pytest_asyncio.fixture
    async def test_environment(self):
        """Set up complete test environment with all components."""
        # Create temporary database
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_file.close()

        db_manager = DatabaseManager(temp_file.name)
        await db_manager.initialize_database()

        # Create component instances
        question_engine = QuestionEngine()
        user_manager = UserManager()
        user_manager.db_manager = db_manager
        scoring_engine = ScoringEngine()

        yield {
            "db_manager": db_manager,
            "question_engine": question_engine,
            "user_manager": user_manager,
            "scoring_engine": scoring_engine,
        }

        # Cleanup
        await db_manager.close_all_connections()
        os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_complete_trivia_game_session(self, test_environment):
        """Test a complete trivia game session from start to finish."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 12345

        # Step 1: Create/get user
        user = await user_manager.get_or_create_user(user_id)
        assert user.user_id == user_id
        assert user.total_points == 0

        # Step 2: Get a question
        question = await question_engine.get_question(difficulty="medium")
        if not question:
            pytest.skip("No questions available for testing")

        # Step 3: Simulate user answering correctly
        start_time = datetime.now()
        time_taken = 8.0  # 8 seconds
        is_correct = True

        # Validate the answer
        user_answer = question.correct_answer
        answer_valid = await question_engine.validate_answer(question, user_answer)
        assert answer_valid is True

        # Step 4: Calculate score
        score_result = scoring_engine.calculate_total_score(
            difficulty=question.difficulty,
            is_correct=is_correct,
            time_taken=time_taken,
            current_streak=user.current_streak,
            user_accuracy=user.accuracy_percentage,
        )

        points_earned = score_result["total_points"]
        assert points_earned > 0

        # Step 5: Update user stats
        updated_user = await user_manager.update_stats(
            user_id=user_id,
            points=points_earned,
            is_correct=is_correct,
            difficulty=question.difficulty,
            category=question.category,
        )

        # Step 6: Verify final state
        assert updated_user.total_points == points_earned
        assert updated_user.questions_answered == 1
        assert updated_user.questions_correct == 1
        assert updated_user.current_streak == 1
        assert updated_user.accuracy_percentage == 100.0

    @pytest.mark.asyncio
    async def test_multiple_question_session_with_streak(self, test_environment):
        """Test multiple questions in a session building up a streak."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 54321
        user = await user_manager.get_or_create_user(user_id)

        total_points = 0
        questions_answered = 0
        questions_correct = 0

        # Answer 5 questions correctly to build streak
        for i in range(5):
            # Get question
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                continue

            questions_answered += 1

            # Answer correctly
            is_correct = True
            questions_correct += 1
            time_taken = 5.0 + i  # Varying response times

            # Get current user state for scoring
            current_user = await user_manager.get_or_create_user(user_id)

            # Calculate score with current streak
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=time_taken,
                current_streak=current_user.current_streak,
                user_accuracy=current_user.accuracy_percentage,
            )

            points_earned = score_result["total_points"]
            total_points += points_earned

            # Update user stats
            updated_user = await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
                category=question.category,
            )

            # Verify streak is building
            assert updated_user.current_streak == i + 1

        # Verify final state
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.questions_answered == questions_answered
        assert final_user.questions_correct == questions_correct
        assert final_user.current_streak == 5
        assert final_user.best_streak == 5
        assert final_user.accuracy_percentage == 100.0

    @pytest.mark.asyncio
    async def test_streak_breaking_and_recovery(self, test_environment):
        """Test streak breaking and recovery workflow."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 98765
        user = await user_manager.get_or_create_user(user_id)

        # Build up a streak of 3
        for i in range(3):
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                continue

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=10.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

        # Verify streak is built
        user_with_streak = await user_manager.get_or_create_user(user_id)
        assert user_with_streak.current_streak == 3
        assert user_with_streak.best_streak == 3

        # Break the streak with wrong answer
        question = await question_engine.get_question(difficulty="hard")
        if question:
            await user_manager.update_stats(
                user_id=user_id,
                points=0,
                is_correct=False,
                difficulty=question.difficulty,
            )

        # Verify streak is broken but best streak preserved
        user_broken_streak = await user_manager.get_or_create_user(user_id)
        assert user_broken_streak.current_streak == 0
        assert user_broken_streak.best_streak == 3  # Preserved

        # Start new streak
        for i in range(2):
            question = await question_engine.get_question(difficulty="medium")
            if not question:
                continue

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=10.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

        # Verify new streak
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.current_streak == 2
        assert final_user.best_streak == 3  # Still preserved

    @pytest.mark.asyncio
    async def test_daily_challenge_workflow(self, test_environment):
        """Test complete daily challenge workflow."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 11111

        # Check if user can attempt daily challenge
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is True

        # Get daily challenge question
        daily_question = await question_engine.get_daily_challenge_question()
        if not daily_question:
            pytest.skip("No daily challenge question available")

        # Verify it's a hard question with doubled points
        assert daily_question.difficulty == "hard"
        assert daily_question.point_value >= 60  # Hard (30) * 2

        # Answer the daily challenge
        is_correct = True
        time_taken = 15.0

        current_user = await user_manager.get_or_create_user(user_id)
        score_result = scoring_engine.calculate_total_score(
            difficulty=daily_question.difficulty,
            is_correct=is_correct,
            time_taken=time_taken,
            current_streak=current_user.current_streak,
            is_challenge=True,  # Daily challenge bonus
        )

        # Update stats
        await user_manager.update_stats(
            user_id=user_id,
            points=score_result["total_points"],
            is_correct=is_correct,
            difficulty=daily_question.difficulty,
        )

        # Mark daily challenge as completed
        completion_success = await user_manager.update_challenge_completion(
            user_id, "daily"
        )
        assert completion_success is True

        # Verify can't attempt again today
        can_attempt_again = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_again is False

        # Verify points were awarded with challenge bonus
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.total_points > 0
        # Should have challenge multiplier applied
        assert score_result["challenge_multiplier"] == 2.0

    @pytest.mark.asyncio
    async def test_weekly_challenge_workflow(self, test_environment):
        """Test complete weekly challenge workflow."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 22222

        # Check if user can attempt weekly challenge
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is True

        # Get weekly challenge questions
        weekly_questions = await question_engine.get_weekly_challenge_questions()
        if not weekly_questions:
            pytest.skip("No weekly challenge questions available")

        # Should have 5 questions (2 medium, 3 hard)
        assert len(weekly_questions) <= 5

        total_points = 0
        questions_correct = 0

        # Answer all weekly challenge questions
        for i, question in enumerate(weekly_questions):
            # Simulate varying performance (some correct, some incorrect)
            is_correct = i < 3  # First 3 correct, last 2 incorrect
            time_taken = 10.0 + i * 2

            if is_correct:
                questions_correct += 1

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=time_taken,
                current_streak=current_user.current_streak,
                is_challenge=True,  # Weekly challenge bonus
            )

            points_earned = score_result["total_points"] if is_correct else 0
            total_points += points_earned

            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
            )

        # Mark weekly challenge as completed
        completion_success = await user_manager.update_challenge_completion(
            user_id, "weekly"
        )
        assert completion_success is True

        # Verify can't attempt again this week
        can_attempt_again = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_again is False

        # Verify final state
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.total_points == total_points
        assert final_user.questions_correct == questions_correct

    @pytest.mark.asyncio
    async def test_concurrent_game_sessions(self, test_environment):
        """Test concurrent game sessions across multiple users."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_ids = [33333, 44444, 55555]

        async def simulate_user_session(user_id):
            """Simulate a complete user session."""
            session_points = 0

            # Each user answers 3 questions
            for i in range(3):
                question = await question_engine.get_question(difficulty="medium")
                if not question:
                    continue

                # Simulate different performance per user
                is_correct = (user_id + i) % 2 == 0  # Alternating pattern
                time_taken = 5.0 + (user_id % 10)  # Different response times

                current_user = await user_manager.get_or_create_user(user_id)
                score_result = scoring_engine.calculate_total_score(
                    difficulty=question.difficulty,
                    is_correct=is_correct,
                    time_taken=time_taken,
                    current_streak=current_user.current_streak,
                )

                points_earned = score_result["total_points"] if is_correct else 0
                session_points += points_earned

                await user_manager.update_stats(
                    user_id=user_id,
                    points=points_earned,
                    is_correct=is_correct,
                    difficulty=question.difficulty,
                )

            return session_points

        # Run concurrent sessions
        tasks = [simulate_user_session(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all sessions completed successfully
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == len(user_ids)

        # Verify each user has their own independent state
        for user_id in user_ids:
            user = await user_manager.get_or_create_user(user_id)
            assert user.user_id == user_id
            assert user.questions_answered > 0

    @pytest.mark.asyncio
    async def test_achievement_unlocking_workflow(self, test_environment):
        """Test achievement unlocking during gameplay."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 66666

        # Answer questions to build up to streak achievement
        for i in range(5):  # Build 5-question streak for "hot_streak"
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                continue

            current_user = await user_manager.get_or_create_user(user_id)

            # Check for achievements before update
            achievements_before = scoring_engine.check_streak_achievements(
                current_user.current_streak, user_id
            )

            # Answer correctly
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=10.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

            # Check for achievements after update
            updated_user = await user_manager.get_or_create_user(user_id)
            achievements_after = scoring_engine.check_streak_achievements(
                updated_user.current_streak, user_id
            )

            # If we reached streak 5, should unlock hot_streak
            if updated_user.current_streak == 5:
                assert "hot_streak" in achievements_after
                assert "hot_streak" not in achievements_before

    @pytest.mark.asyncio
    async def test_user_statistics_workflow(self, test_environment):
        """Test complete user statistics tracking workflow."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 77777

        # Create varied gameplay history
        categories = ["science", "history", "math", "general"]
        difficulties = ["easy", "medium", "hard"]

        for i in range(12):  # 12 questions for good sample size
            category = categories[i % len(categories)]
            difficulty = difficulties[i % len(difficulties)]

            question = await question_engine.get_question(
                difficulty=difficulty, category=category
            )
            if not question:
                # Create a mock question for testing
                question = Question(
                    id=i,
                    difficulty=difficulty,
                    category=category,
                    point_value={"easy": 10, "medium": 20, "hard": 30}[difficulty],
                )

            # Simulate 75% accuracy
            is_correct = i % 4 != 0  # 3 out of 4 correct

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty=difficulty,
                is_correct=is_correct,
                time_taken=8.0 + i,
                current_streak=current_user.current_streak,
            )

            points_earned = score_result["total_points"] if is_correct else 0

            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=difficulty,
                category=category,
            )

        # Get comprehensive user statistics
        user_stats = await user_manager.get_user_stats(user_id)

        # Verify statistics are comprehensive
        assert user_stats.user_profile.questions_answered == 12
        assert user_stats.user_profile.questions_correct == 9  # 75% of 12
        assert user_stats.accuracy_percentage == 75.0
        assert isinstance(user_stats.points_per_category, dict)
        assert isinstance(user_stats.difficulty_breakdown, dict)

        # Get user preferences
        preferences = await user_manager.get_user_preferences(user_id)
        assert isinstance(preferences, dict)
        assert "preferred_difficulty" in preferences
        assert "favorite_categories" in preferences

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_environment):
        """Test system recovery from various error conditions."""
        question_engine = test_environment["question_engine"]
        user_manager = test_environment["user_manager"]
        scoring_engine = test_environment["scoring_engine"]

        user_id = 88888

        # Start normal session
        user = await user_manager.get_or_create_user(user_id)
        question = await question_engine.get_question()

        if question:
            # Simulate partial session completion
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=10.0,
                current_streak=0,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

        # Verify system state is consistent after operations
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.user_id == user_id

        # System should be able to continue normal operations
        another_question = await question_engine.get_question()
        # Should not raise exceptions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
