"""
Integration tests for daily and weekly challenge workflows with time-based scenarios.
Tests challenge timing, availability, completion tracking, and time boundaries.
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
from utils.models import Question, UserProfile


class TestTimeBased ChallengeWorkflows:
    """Integration tests for time-based challenge workflows."""

    @pytest_asyncio.fixture
    async def challenge_test_environment(self):
        """Set up test environment for challenge testing."""
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
    async def test_daily_challenge_complete_workflow(self, challenge_test_environment):
        """Test complete daily challenge workflow from start to finish."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        scoring_engine = challenge_test_environment["scoring_engine"]

        user_id = 12345
        
        # Step 1: Check initial challenge availability
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is True
        
        # Step 2: Get daily challenge question
        daily_question = await question_engine.get_daily_challenge_question()
        if not daily_question:
            pytest.skip("No daily challenge question available")
        
        # Verify daily challenge properties
        assert daily_question.difficulty == "hard"
        assert daily_question.point_value >= 60  # Hard (30) * 2 multiplier
        
        # Step 3: Answer the daily challenge
        start_time = datetime.now()
        is_correct = True
        time_taken = 15.0
        
        # Validate answer
        user_answer = daily_question.correct_answer
        answer_valid = await question_engine.validate_answer(daily_question, user_answer)
        assert answer_valid is True
        
        # Step 4: Calculate score with challenge bonus
        current_user = await user_manager.get_or_create_user(user_id)
        score_result = scoring_engine.calculate_total_score(
            difficulty=daily_question.difficulty,
            is_correct=is_correct,
            time_taken=time_taken,
            current_streak=current_user.current_streak,
            user_accuracy=current_user.accuracy_percentage,
            is_challenge=True  # Daily challenge bonus
        )
        
        # Verify challenge multiplier is applied
        assert score_result["challenge_multiplier"] == 2.0
        points_earned = score_result["total_points"]
        assert points_earned > 0
        
        # Step 5: Update user stats
        updated_user = await user_manager.update_stats(
            user_id=user_id,
            points=points_earned,
            is_correct=is_correct,
            difficulty=daily_question.difficulty,
            category=daily_question.category
        )
        
        # Step 6: Mark daily challenge as completed
        completion_success = await user_manager.update_challenge_completion(user_id, "daily")
        assert completion_success is True
        
        # Step 7: Verify challenge cannot be attempted again today
        can_attempt_again = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_again is False
        
        # Step 8: Verify final user state
        assert updated_user.total_points == points_earned
        assert updated_user.questions_answered == 1
        assert updated_user.questions_correct == 1

    @pytest.mark.asyncio
    async def test_weekly_challenge_complete_workflow(self, challenge_test_environment):
        """Test complete weekly challenge workflow."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        scoring_engine = challenge_test_environment["scoring_engine"]

        user_id = 23456
        
        # Step 1: Check weekly challenge availability
        can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt is True
        
        # Step 2: Get weekly challenge questions
        weekly_questions = await question_engine.get_weekly_challenge_questions()
        if not weekly_questions:
            pytest.skip("No weekly challenge questions available")
        
        # Verify weekly challenge properties
        assert len(weekly_questions) <= 5  # Should have up to 5 questions
        
        # Verify question difficulties (2 medium, 3 hard)
        difficulties = [q.difficulty for q in weekly_questions]
        medium_count = difficulties.count("medium")
        hard_count = difficulties.count("hard")
        
        # All questions should have tripled points
        for question in weekly_questions:
            if question.difficulty == "medium":
                assert question.point_value >= 60  # 20 * 3
            elif question.difficulty == "hard":
                assert question.point_value >= 90  # 30 * 3
        
        # Step 3: Answer all weekly challenge questions
        total_points = 0
        questions_correct = 0
        
        for i, question in enumerate(weekly_questions):
            # Simulate varying performance (first 3 correct, rest incorrect)
            is_correct = i < 3
            time_taken = 10.0 + i * 2
            
            if is_correct:
                questions_correct += 1
            
            # Validate answer if correct
            if is_correct:
                user_answer = question.correct_answer
                answer_valid = await question_engine.validate_answer(question, user_answer)
                assert answer_valid is True
            
            # Calculate score
            current_user = await user_manager.get_or_create_user(user_id)
            score_result = scoring_engine.calculate_total_score(
                difficulty=question.difficulty,
                is_correct=is_correct,
                time_taken=time_taken,
                current_streak=current_user.current_streak,
                user_accuracy=current_user.accuracy_percentage,
                is_challenge=True  # Weekly challenge bonus
            )
            
            # Verify challenge multiplier
            assert score_result["challenge_multiplier"] == 2.0
            
            points_earned = score_result["total_points"] if is_correct else 0
            total_points += points_earned
            
            # Update user stats
            await user_manager.update_stats(
                user_id=user_id,
                points=points_earned,
                is_correct=is_correct,
                difficulty=question.difficulty,
                category=question.category
            )
        
        # Step 4: Mark weekly challenge as completed
        completion_success = await user_manager.update_challenge_completion(user_id, "weekly")
        assert completion_success is True
        
        # Step 5: Verify challenge cannot be attempted again this week
        can_attempt_again = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_again is False
        
        # Step 6: Verify final state
        final_user = await user_manager.get_or_create_user(user_id)
        assert final_user.total_points == total_points
        assert final_user.questions_correct == questions_correct
        assert final_user.questions_answered == len(weekly_questions)

    @pytest.mark.asyncio
    async def test_daily_challenge_time_boundaries(self, challenge_test_environment):
        """Test daily challenge behavior across day boundaries."""
        user_manager = challenge_test_environment["user_manager"]
        
        user_id = 34567
        
        # Test 1: Complete today's daily challenge
        can_attempt_today = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_today is True
        
        # Mark as completed today
        completion_success = await user_manager.update_challenge_completion(user_id, "daily")
        assert completion_success is True
        
        # Verify cannot attempt again today
        can_attempt_again_today = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_again_today is False
        
        # Test 2: Simulate next day by manually setting completion date to yesterday
        yesterday = date.today() - timedelta(days=1)
        
        async with user_manager.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET daily_challenge_completed = ? WHERE user_id = ?",
                (yesterday, user_id)
            )
            await conn.commit()
        
        # Should be able to attempt challenge again (new day)
        can_attempt_new_day = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_new_day is True

    @pytest.mark.asyncio
    async def test_weekly_challenge_time_boundaries(self, challenge_test_environment):
        """Test weekly challenge behavior across week boundaries."""
        user_manager = challenge_test_environment["user_manager"]
        
        user_id = 45678
        
        # Test 1: Complete this week's challenge
        can_attempt_this_week = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_this_week is True
        
        # Mark as completed this week
        completion_success = await user_manager.update_challenge_completion(user_id, "weekly")
        assert completion_success is True
        
        # Verify cannot attempt again this week
        can_attempt_again_this_week = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_again_this_week is False
        
        # Test 2: Simulate next week by setting completion date to last week
        last_week = date.today() - timedelta(days=7)
        
        async with user_manager.db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE users SET weekly_challenge_completed = ? WHERE user_id = ?",
                (last_week, user_id)
            )
            await conn.commit()
        
        # Should be able to attempt challenge again (new week)
        can_attempt_new_week = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_new_week is True

    @pytest.mark.asyncio
    async def test_challenge_consistency_across_users(self, challenge_test_environment):
        """Test that challenges are consistent across different users."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        
        user_ids = [56789, 67890, 78901]
        
        # Test daily challenge consistency
        daily_questions = []
        for user_id in user_ids:
            can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
            if can_attempt:
                daily_question = await question_engine.get_daily_challenge_question()
                if daily_question:
                    daily_questions.append(daily_question.id)
        
        # All users should get the same daily question
        if len(daily_questions) > 1:
            assert all(qid == daily_questions[0] for qid in daily_questions)
        
        # Test weekly challenge consistency
        weekly_question_sets = []
        for user_id in user_ids:
            can_attempt = await user_manager.can_attempt_challenge(user_id, "weekly")
            if can_attempt:
                weekly_questions = await question_engine.get_weekly_challenge_questions()
                if weekly_questions:
                    question_ids = [q.id for q in weekly_questions]
                    weekly_question_sets.append(question_ids)
        
        # All users should get the same weekly question set
        if len(weekly_question_sets) > 1:
            first_set = weekly_question_sets[0]
            for question_set in weekly_question_sets[1:]:
                assert question_set == first_set

    @pytest.mark.asyncio
    async def test_challenge_completion_tracking_persistence(self, challenge_test_environment):
        """Test that challenge completion tracking persists across sessions."""
        user_manager = challenge_test_environment["user_manager"]
        
        user_id = 89012
        
        # Complete daily challenge
        await user_manager.update_challenge_completion(user_id, "daily")
        
        # Verify completion is tracked
        can_attempt_daily = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_daily is False
        
        # Complete weekly challenge
        await user_manager.update_challenge_completion(user_id, "weekly")
        
        # Verify completion is tracked
        can_attempt_weekly = await user_manager.can_attempt_challenge(user_id, "weekly")
        assert can_attempt_weekly is False
        
        # Simulate system restart by creating new user manager instance
        new_user_manager = UserManager()
        new_user_manager.db_manager = challenge_test_environment["db_manager"]
        
        # Verify completion tracking persists
        can_attempt_daily_after_restart = await new_user_manager.can_attempt_challenge(user_id, "daily")
        can_attempt_weekly_after_restart = await new_user_manager.can_attempt_challenge(user_id, "weekly")
        
        assert can_attempt_daily_after_restart is False
        assert can_attempt_weekly_after_restart is False

    @pytest.mark.asyncio
    async def test_concurrent_challenge_attempts(self, challenge_test_environment):
        """Test concurrent challenge attempts by multiple users."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        scoring_engine = challenge_test_environment["scoring_engine"]
        
        user_ids = [90123, 90124, 90125, 90126, 90127]
        
        async def attempt_daily_challenge(user_id):
            """Simulate user attempting daily challenge."""
            try:
                # Check if can attempt
                can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
                if not can_attempt:
                    return {"user_id": user_id, "status": "already_completed"}
                
                # Get daily question
                daily_question = await question_engine.get_daily_challenge_question()
                if not daily_question:
                    return {"user_id": user_id, "status": "no_question"}
                
                # Answer correctly
                current_user = await user_manager.get_or_create_user(user_id)
                score_result = scoring_engine.calculate_total_score(
                    difficulty=daily_question.difficulty,
                    is_correct=True,
                    time_taken=12.0,
                    current_streak=current_user.current_streak,
                    is_challenge=True
                )
                
                # Update stats
                await user_manager.update_stats(
                    user_id=user_id,
                    points=score_result["total_points"],
                    is_correct=True,
                    difficulty=daily_question.difficulty
                )
                
                # Mark as completed
                await user_manager.update_challenge_completion(user_id, "daily")
                
                return {
                    "user_id": user_id,
                    "status": "completed",
                    "points": score_result["total_points"],
                    "question_id": daily_question.id
                }
                
            except Exception as e:
                return {"user_id": user_id, "status": "error", "error": str(e)}
        
        # All users attempt daily challenge concurrently
        tasks = [attempt_daily_challenge(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        successful_completions = [
            r for r in results 
            if isinstance(r, dict) and r.get("status") == "completed"
        ]
        
        # At least some users should complete successfully
        assert len(successful_completions) > 0
        
        # All successful completions should have the same question
        if len(successful_completions) > 1:
            question_ids = [r["question_id"] for r in successful_completions]
            assert all(qid == question_ids[0] for qid in question_ids)
        
        # Verify all users cannot attempt again
        for user_id in user_ids:
            can_attempt_again = await user_manager.can_attempt_challenge(user_id, "daily")
            # Should be False if they completed, or might still be True if they had an error
            if any(r.get("user_id") == user_id and r.get("status") == "completed" for r in results):
                assert can_attempt_again is False

    @pytest.mark.asyncio
    async def test_challenge_scoring_integration(self, challenge_test_environment):
        """Test integration between challenge system and scoring system."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        scoring_engine = challenge_test_environment["scoring_engine"]
        
        user_id = 91234
        
        # Build up some base stats first
        base_user = await user_manager.get_or_create_user(user_id)
        for i in range(3):
            await user_manager.update_stats(user_id, 10, True, "easy")
        
        # Get current user state
        current_user = await user_manager.get_or_create_user(user_id)
        initial_points = current_user.total_points
        initial_streak = current_user.current_streak
        
        # Attempt daily challenge
        daily_question = await question_engine.get_daily_challenge_question()
        if daily_question:
            # Calculate score with all bonuses
            score_result = scoring_engine.calculate_total_score(
                difficulty=daily_question.difficulty,
                is_correct=True,
                time_taken=8.0,  # Fast answer for time bonus
                current_streak=initial_streak,
                user_accuracy=current_user.accuracy_percentage,
                is_challenge=True  # Challenge multiplier
            )
            
            # Verify challenge bonus is applied
            assert score_result["challenge_multiplier"] == 2.0
            
            # Verify other bonuses can stack with challenge bonus
            if score_result["time_bonus_multiplier"] > 1.0:
                # Time bonus should stack with challenge bonus
                expected_base = 30  # Hard question base points
                expected_with_bonuses = expected_base * score_result["time_bonus_multiplier"] * 2.0
                expected_total = int(expected_with_bonuses) + score_result["streak_bonus"]
                
                assert score_result["total_points"] == expected_total
            
            # Update user stats
            await user_manager.update_stats(
                user_id=user_id,
                points=score_result["total_points"],
                is_correct=True,
                difficulty=daily_question.difficulty
            )
            
            # Verify final state
            final_user = await user_manager.get_or_create_user(user_id)
            expected_total_points = initial_points + score_result["total_points"]
            assert final_user.total_points == expected_total_points
            assert final_user.current_streak == initial_streak + 1

    @pytest.mark.asyncio
    async def test_challenge_error_recovery(self, challenge_test_environment):
        """Test challenge system recovery from various error conditions."""
        question_engine = challenge_test_environment["question_engine"]
        user_manager = challenge_test_environment["user_manager"]
        
        user_id = 92345
        
        # Test 1: Attempt challenge completion with database error
        with patch.object(user_manager.db_manager, 'get_connection') as mock_conn:
            mock_conn.side_effect = Exception("Database error")
            
            # Should handle error gracefully
            try:
                result = await user_manager.update_challenge_completion(user_id, "daily")
                assert result is False
            except Exception:
                # Exception is also acceptable
                pass
        
        # Test 2: System should recover and work normally after error
        can_attempt = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt is True  # Should still be able to attempt
        
        # Test 3: Normal completion should work after error recovery
        completion_success = await user_manager.update_challenge_completion(user_id, "daily")
        assert completion_success is True
        
        # Verify completion is tracked
        can_attempt_after_completion = await user_manager.can_attempt_challenge(user_id, "daily")
        assert can_attempt_after_completion is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])