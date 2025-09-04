"""
Integration tests for GameManager and AnswerProcessor working together.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from utils.game_manager import GameManager
from utils.question_engine import QuestionEngine
from utils.models import Question


class TestIntegration:
    """Integration test cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.question_engine = Mock(spec=QuestionEngine)
        self.game_manager = GameManager(self.question_engine)

    @pytest.mark.asyncio
    async def test_full_game_flow_multiple_choice(self):
        """Test complete game flow with multiple choice question."""
        # Mock question
        test_question = Question(
            id=1,
            question_text="What is the capital of France?",
            question_type="multiple_choice",
            difficulty="medium",
            options=["London", "Paris", "Berlin", "Madrid"],
            correct_answer="1",  # Paris
            point_value=20,
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        game_session = await self.game_manager.start_game(
            channel_id=12345, user_id=67890, timeout_duration=30
        )

        assert game_session is not None
        assert game_session.question.question_text == "What is the capital of France?"

        # Check answer format
        format_str = self.game_manager.get_expected_answer_format(12345)
        assert "🇦, 🇧, 🇨, or 🇩" in format_str

        # Check valid reactions
        assert self.game_manager.is_valid_reaction(12345, "🇦") is True
        assert self.game_manager.is_valid_reaction(12345, "🇧") is True
        assert self.game_manager.is_valid_reaction(12345, "✅") is False

        # Get correct answer display
        correct_display = self.game_manager.get_correct_answer_display(12345)
        assert "🇧" in correct_display
        assert "Paris" in correct_display

    @pytest.mark.asyncio
    async def test_full_game_flow_true_false(self):
        """Test complete game flow with true/false question."""
        # Mock question
        test_question = Question(
            id=2,
            question_text="LA Galaxy plays in MLS.",
            question_type="true_false",
            difficulty="easy",
            correct_answer="true",
            point_value=10,
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        game_session = await self.game_manager.start_game(
            channel_id=54321, user_id=11111, timeout_duration=30
        )

        assert game_session is not None
        assert game_session.question.question_text == "LA Galaxy plays in MLS."

        # Check answer format
        format_str = self.game_manager.get_expected_answer_format(54321)
        assert "✅" in format_str
        assert "❌" in format_str

        # Check valid reactions
        assert self.game_manager.is_valid_reaction(54321, "✅") is True
        assert self.game_manager.is_valid_reaction(54321, "❌") is True
        assert self.game_manager.is_valid_reaction(54321, "🇦") is False

        # Get correct answer display
        correct_display = self.game_manager.get_correct_answer_display(54321)
        assert "✅" in correct_display
        assert "True" in correct_display

    @pytest.mark.asyncio
    async def test_full_game_flow_fill_blank(self):
        """Test complete game flow with fill-in-the-blank question."""
        # Mock question
        test_question = Question(
            id=3,
            question_text="What team plays at Dignity Health Sports Park?",
            question_type="fill_blank",
            difficulty="medium",
            correct_answer="LA Galaxy",
            answer_variations=["Los Angeles Galaxy", "Galaxy", "LAG"],
            point_value=20,
        )

        self.question_engine.get_question = AsyncMock(return_value=test_question)

        # Start game
        game_session = await self.game_manager.start_game(
            channel_id=99999, user_id=22222, timeout_duration=30
        )

        assert game_session is not None
        assert "Dignity Health Sports Park" in game_session.question.question_text

        # Check answer format
        format_str = self.game_manager.get_expected_answer_format(99999)
        assert "Type your answer" in format_str

        # Check no valid reactions for fill-blank
        assert self.game_manager.is_valid_reaction(99999, "🇦") is False
        assert self.game_manager.is_valid_reaction(99999, "✅") is False

        # Get correct answer display
        correct_display = self.game_manager.get_correct_answer_display(99999)
        assert correct_display == "LA Galaxy"

    @pytest.mark.asyncio
    async def test_concurrent_games_different_channels(self):
        """Test multiple games running concurrently in different channels."""
        # Mock questions
        mc_question = Question(
            id=1,
            question_text="Multiple choice question?",
            question_type="multiple_choice",
            options=["A", "B", "C", "D"],
            correct_answer="0",
        )

        tf_question = Question(
            id=2,
            question_text="True/false question?",
            question_type="true_false",
            correct_answer="true",
        )

        self.question_engine.get_question = AsyncMock(
            side_effect=[mc_question, tf_question]
        )

        # Start games in different channels
        game1 = await self.game_manager.start_game(channel_id=111, user_id=1001)
        game2 = await self.game_manager.start_game(channel_id=222, user_id=1002)

        assert game1 is not None
        assert game2 is not None
        assert game1.question.question_type == "multiple_choice"
        assert game2.question.question_type == "true_false"

        # Check both games are active
        assert await self.game_manager.get_active_games_count() == 2
        active_channels = await self.game_manager.get_active_channels()
        assert 111 in active_channels
        assert 222 in active_channels

        # Check different answer formats
        format1 = self.game_manager.get_expected_answer_format(111)
        format2 = self.game_manager.get_expected_answer_format(222)
        assert "🇦, 🇧, 🇨, or 🇩" in format1
        assert "✅" in format2 and "❌" in format2

        # End one game
        await self.game_manager.end_game(111)
        assert await self.game_manager.get_active_games_count() == 1
        assert await self.game_manager.get_active_game(111) is None
        assert await self.game_manager.get_active_game(222) is not None

    @pytest.mark.asyncio
    async def test_answer_processor_integration(self):
        """Test that answer processor correctly validates answers."""
        # Test multiple choice validation
        mc_question = Question(
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",
        )

        processor = self.game_manager.answer_processor

        # Test correct answer
        assert await processor.validate_answer(mc_question, 1) is True
        # Test incorrect answers
        assert await processor.validate_answer(mc_question, 0) is False
        assert await processor.validate_answer(mc_question, 2) is False

        # Test true/false validation
        tf_question = Question(question_type="true_false", correct_answer="true")

        assert await processor.validate_answer(tf_question, True) is True
        assert await processor.validate_answer(tf_question, False) is False

        # Test fill-blank validation
        fb_question = Question(
            question_type="fill_blank",
            correct_answer="LA Galaxy",
            answer_variations=["Los Angeles Galaxy", "Galaxy"],
        )

        assert await processor.validate_answer(fb_question, "LA Galaxy") is True
        assert await processor.validate_answer(fb_question, "la galaxy") is True
        assert await processor.validate_answer(fb_question, "Galaxy") is True
        assert (
            await processor.validate_answer(fb_question, "Los Angeles Galaxy") is True
        )
        assert await processor.validate_answer(fb_question, "LAFC") is False


if __name__ == "__main__":
    pytest.main([__file__])
