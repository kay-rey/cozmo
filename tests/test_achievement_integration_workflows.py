"""
Integration tests for achievement unlocking during gameplay workflows.
Tests achievement system integration with game mechanics and user progression.
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
from utils.models import Question, UserProfile, ACHIEVEMENTS


class TestAchievementIntegrationWorkflows:
    """Integration tests for achievement unlocking during gameplay."""

    @pytest_asyncio.fixture
    async def achievement_test_environment(self):
        """Set up test environment for achievement testing."""
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
    async def test_streak_achievement_progression(self, achievement_test_environment):
        """Test streak achievement unlocking progression."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 12345
        achievements_unlocked = []

        # Answer questions to build streak and unlock achievements
        for i in range(12):  # Enough to unlock multiple streak achievements
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                # Create mock question for testing
                question = Question(
                    id=i, difficulty="easy", category="test", point_value=10
                )

            # Get current user state
            current_user = await user_manager.get_or_create_user(user_id)
            current_streak = current_user.current_streak

            # Check achievements before answering
            achievements_before = scoring_engine.check_streak_achievements(
                current_streak, user_id
            )

            # Answer correctly to build streak
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=10.0,
                current_streak=current_streak,
            )

            # Update user stats
            updated_user = await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

            # Check achievements after answering
            new_streak = updated_user.current_streak
            achievements_after = scoring_engine.check_streak_achievements(
                new_streak, user_id
            )

            # Check for newly unlocked achievements
            new_achievements = set(achievements_after) - set(achievements_before)
            if new_achievements:
                achievements_unlocked.extend(new_achievements)
                print(
                    f"Unlocked achievements at streak {new_streak}: {new_achievements}"
                )

            # Verify streak progression
            assert new_streak == i + 1

        # Verify expected achievements were unlocked
        assert "hot_streak" in achievements_unlocked  # Should unlock at streak 5
        assert "galaxy_expert" in achievements_unlocked  # Should unlock at streak 10

        # Verify final user state
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.current_streak == 12
        assert final_user.best_streak == 12

    @pytest.mark.asyncio
    async def test_accuracy_achievement_progression(self, achievement_test_environment):
        """Test accuracy-based achievement progression."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 23456

        # Answer questions with high accuracy to work toward accuracy achievements
        total_questions = 60  # More than minimum for accuracy achievements
        correct_answers = 0

        for i in range(total_questions):
            question = await question_engine.get_question()
            if not question:
                question = Question(id=i, difficulty="medium", point_value=20)

            # Maintain 90%+ accuracy (answer 9 out of 10 correctly)
            is_correct = (i % 10) != 0  # Miss every 10th question
            if is_correct:
                correct_answers += 1

            current_user = await user_manager.get_or_create_user(user_id)

            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=8.0,
                current_streak=current_user.current_streak,
            )

            points_earned = score_result["total_points"] if is_correct else 0

            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
            )

            # Check accuracy achievement progress periodically
            if (i + 1) % 10 == 0:  # Every 10 questions
                current_user = await user_manager.get_or_create_user(user_id)
                accuracy = current_user.accuracy_percentage

                # Check if accuracy achievement requirements are met
                if current_user.questions_answered >= 50 and accuracy >= 90:
                    # Would unlock perfectionist achievement
                    print(f"After {i + 1} questions: {accuracy:.1f}% accuracy")

        # Verify final accuracy
        final_user = await user_manager.get_or_create_user(user_id)
        final_accuracy = final_user.accuracy_percentage

        # Should have 90% accuracy (54/60 = 90%)
        expected_accuracy = (correct_answers / total_questions) * 100
        assert abs(final_accuracy - expected_accuracy) < 0.1
        assert final_accuracy >= 90.0

    @pytest.mark.asyncio
    async def test_total_correct_achievement_progression(
        self, achievement_test_environment
    ):
        """Test total correct answers achievement progression."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 34567
        target_correct = 100  # Target for trivia_master achievement

        # Answer questions to reach total correct milestone
        for i in range(120):  # Answer more than target to ensure we reach it
            question = await question_engine.get_question()
            if not question:
                question = Question(id=i, difficulty="easy", point_value=10)

            # Answer correctly most of the time (85% accuracy)
            is_correct = (i % 7) != 0  # Miss every 7th question

            current_user = await user_manager.get_or_create_user(user_id)

            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=12.0,
                current_streak=current_user.current_streak,
            )

            points_earned = score_result["total_points"] if is_correct else 0

            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
            )

            # Check progress toward total correct achievement
            updated_user = await user_manager.get_or_create_user(user_id)
            if updated_user.questions_correct >= target_correct:
                print(f"Reached {updated_user.questions_correct} correct answers!")
                break

        # Verify achievement milestone was reached
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.questions_correct >= target_correct

    @pytest.mark.asyncio
    async def test_mixed_achievement_progression(self, achievement_test_environment):
        """Test progression toward multiple different achievement types simultaneously."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 45678

        # Simulate varied gameplay that could unlock multiple achievement types
        gameplay_sessions = [
            # Session 1: Build initial streak
            {"questions": 8, "accuracy": 1.0, "difficulty": "easy"},
            # Session 2: Break streak but maintain good accuracy
            {"questions": 5, "accuracy": 0.6, "difficulty": "medium"},
            # Session 3: Rebuild streak with high accuracy
            {"questions": 15, "accuracy": 0.93, "difficulty": "hard"},
            # Session 4: Consistent performance
            {"questions": 25, "accuracy": 0.88, "difficulty": "medium"},
        ]

        total_questions = 0
        total_correct = 0

        for session_num, session in enumerate(gameplay_sessions):
            print(
                f"\nSession {session_num + 1}: {session['questions']} questions, "
                f"{session['accuracy'] * 100:.0f}% accuracy, {session['difficulty']} difficulty"
            )

            session_questions = session["questions"]
            session_accuracy = session["accuracy"]
            difficulty = session["difficulty"]

            for i in range(session_questions):
                question = await question_engine.get_question(difficulty=difficulty)
                if not question:
                    question = Question(
                        id=total_questions + i,
                        difficulty=difficulty,
                        point_value={"easy": 10, "medium": 20, "hard": 30}[difficulty],
                    )

                # Determine if this answer is correct based on session accuracy
                is_correct = (i / session_questions) < session_accuracy
                if is_correct:
                    total_correct += 1

                current_user = await user_manager.get_or_create_user(user_id)

                score_result = scoring_engine.calculate_total_score(
                    difficulty=difficulty,
                    is_correct=is_correct,
                    time_taken=7.0 + (i % 5),  # Varying response times
                    current_streak=current_user.current_streak,
                )

                points_earned = score_result["total_points"] if is_correct else 0

                await user_manager.update_stats(
                    user_id=user_id,
                    points=points_earned,
                    is_correct=is_correct,
                    difficulty=difficulty,
                )

            total_questions += session_questions

            # Check achievement progress after each session
            session_user = await user_manager.get_or_create_user(user_id)
            print(
                f"After session: {session_user.questions_correct} correct, "
                f"{session_user.current_streak} current streak, "
                f"{session_user.accuracy_percentage:.1f}% accuracy"
            )

        # Verify final state and potential achievements
        final_user = await user_manager.get_or_create_user(user_id)

        # Check various achievement criteria
        print(f"\nFinal stats:")
        print(f"Total questions: {final_user.questions_answered}")
        print(f"Correct answers: {final_user.questions_correct}")
        print(f"Current streak: {final_user.current_streak}")
        print(f"Best streak: {final_user.best_streak}")
        print(f"Accuracy: {final_user.accuracy_percentage:.1f}%")

        # Verify reasonable progression
        assert final_user.questions_answered == total_questions
        assert final_user.questions_correct > 0
        assert final_user.best_streak > 0

    @pytest.mark.asyncio
    async def test_achievement_unlocking_during_challenges(
        self, achievement_test_environment
    ):
        """Test achievement unlocking during daily and weekly challenges."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 56789

        # Build up some base stats first
        for i in range(3):
            question = await question_engine.get_question(difficulty="easy")
            if not question:
                question = Question(id=i, difficulty="easy", point_value=10)

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty="easy",
                is_correct=True,
                time_taken=10.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty="easy",
            )

        # Attempt daily challenge
        can_attempt_daily = await user_manager.can_attempt_challenge(user_id, "daily")
        if can_attempt_daily:
            daily_question = await question_engine.get_daily_challenge_question()
            if daily_question:
                current_user = await user_manager.get_or_create_user(user_id)

                # Answer daily challenge correctly
                score_result = scoring_engine.calculate_total_score(
                    difficulty=daily_question.difficulty,
                    is_correct=True,
                    time_taken=12.0,
                    current_streak=current_user.current_streak,
                    is_challenge=True,  # Challenge bonus
                )

                await user_manager.update_stats(
                    user_id=user_id,
                    points=score_result["total_points"],
                    is_correct=True,
                    difficulty=daily_question.difficulty,
                )

                await user_manager.update_challenge_completion(user_id, "daily")

                # Check if this unlocked any achievements
                updated_user = await user_manager.get_or_create_user(user_id)
                achievements = scoring_engine.check_streak_achievements(
                    updated_user.current_streak, user_id
                )

                if achievements:
                    print(f"Daily challenge unlocked achievements: {achievements}")

        # Continue building streak for more achievements
        for i in range(5):
            question = await question_engine.get_question(difficulty="medium")
            if not question:
                question = Question(id=10 + i, difficulty="medium", point_value=20)

            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty="medium",
                is_correct=True,
                time_taken=8.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty="medium",
            )

        # Verify final achievement state
        final_user = await user_manager.get_or_create_user(user_id)
        final_achievements = scoring_engine.check_streak_achievements(
            final_user.current_streak, user_id
        )

        print(f"Final streak: {final_user.current_streak}")
        print(f"Final achievements: {final_achievements}")

        # Should have unlocked hot_streak at minimum
        if final_user.current_streak >= 5:
            assert "hot_streak" in final_achievements

    @pytest.mark.asyncio
    async def test_achievement_progress_tracking(self, achievement_test_environment):
        """Test detailed achievement progress tracking during gameplay."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        user_id = 67890

        # Track progress toward specific achievements
        target_achievements = {
            "hot_streak": {"type": "streak", "value": 5, "current": 0},
            "galaxy_expert": {"type": "streak", "value": 10, "current": 0},
        }

        # Answer questions and track progress
        for i in range(12):
            question = await question_engine.get_question()
            if not question:
                question = Question(id=i, difficulty="medium", point_value=20)

            current_user = await user_manager.get_or_create_user(user_id)

            # Calculate progress before answering
            for achievement_id, achievement_data in target_achievements.items():
                if achievement_data["type"] == "streak":
                    current_progress = current_user.current_streak
                    target_value = achievement_data["value"]
                    progress_percentage = min(
                        100, (current_progress / target_value) * 100
                    )

                    print(
                        f"{achievement_id} progress: {current_progress}/{target_value} "
                        f"({progress_percentage:.1f}%)"
                    )

            # Answer correctly to build streak
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=True,
                time_taken=9.0,
                current_streak=current_user.current_streak,
            )

            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=question.difficulty,
            )

            # Check if any achievements were unlocked
            updated_user = await user_manager.get_or_create_user(user_id)
            achievements = scoring_engine.check_streak_achievements(
                updated_user.current_streak, user_id
            )

            if achievements:
                print(f"Question {i + 1}: Unlocked {achievements}")

        # Verify achievement unlocking occurred at expected thresholds
        final_user = await user_manager.get_or_create_user(user_id)
        final_achievements = scoring_engine.check_streak_achievements(
            final_user.current_streak, user_id
        )

        assert final_user.current_streak == 12
        assert "hot_streak" in final_achievements
        assert "galaxy_expert" in final_achievements

    @pytest.mark.asyncio
    async def test_achievement_system_performance_under_load(
        self, achievement_test_environment
    ):
        """Test achievement system performance under concurrent load."""
        question_engine = achievement_test_environment["question_engine"]
        user_manager = achievement_test_environment["user_manager"]
        scoring_engine = achievement_test_environment["scoring_engine"]

        # Create multiple users working toward achievements simultaneously
        user_ids = range(70000, 70010)  # 10 users

        async def user_achievement_session(user_id):
            """Simulate a user session working toward achievements."""
            achievements_unlocked = []

            for i in range(8):  # Each user answers 8 questions
                question = await question_engine.get_question()
                if not question:
                    question = Question(
                        id=f"{user_id}_{i}", difficulty="easy", point_value=10
                    )

                current_user = await user_manager.get_or_create_user(user_id)

                # Check achievements before
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

                # Check achievements after
                updated_user = await user_manager.get_or_create_user(user_id)
                achievements_after = scoring_engine.check_streak_achievements(
                    updated_user.current_streak, user_id
                )

                # Track new achievements
                new_achievements = set(achievements_after) - set(achievements_before)
                achievements_unlocked.extend(new_achievements)

            return {
                "user_id": user_id,
                "achievements": achievements_unlocked,
                "final_streak": updated_user.current_streak,
            }

        # Run all user sessions concurrently
        tasks = [user_achievement_session(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) > 0

        # Verify achievement unlocking worked for multiple users
        users_with_achievements = [r for r in successful_results if r["achievements"]]
        assert len(users_with_achievements) > 0

        # Verify each user reached expected streak
        for result in successful_results:
            assert result["final_streak"] == 8
            if result["final_streak"] >= 5:
                assert "hot_streak" in result["achievements"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
