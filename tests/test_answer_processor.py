"""
Tests for the Answer Processor system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from utils.answer_processor import AnswerProcessor
from utils.models import Question
import discord


class TestAnswerProcessor:
    """Test cases for the AnswerProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AnswerProcessor()

    def test_multiple_choice_reaction_processing(self):
        """Test processing multiple choice reactions."""
        # Test valid reactions
        assert self.processor._process_multiple_choice_reaction("🇦") == 0
        assert self.processor._process_multiple_choice_reaction("🇧") == 1
        assert self.processor._process_multiple_choice_reaction("🇨") == 2
        assert self.processor._process_multiple_choice_reaction("🇩") == 3

        # Test invalid reactions
        assert self.processor._process_multiple_choice_reaction("❌") is None
        assert self.processor._process_multiple_choice_reaction("🎉") is None

    def test_true_false_reaction_processing(self):
        """Test processing true/false reactions."""
        # Test valid reactions
        assert self.processor._process_true_false_reaction("✅") is True
        assert self.processor._process_true_false_reaction("❌") is False

        # Test invalid reactions
        assert self.processor._process_true_false_reaction("🇦") is None
        assert self.processor._process_true_false_reaction("🎉") is None

    def test_multiple_choice_text_processing(self):
        """Test processing multiple choice text answers."""
        question = Question(
            question_text="Test question?",
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",
        )

        # Test letter answers
        assert self.processor._process_multiple_choice_text("A", question) == 0
        assert self.processor._process_multiple_choice_text("b", question) == 1
        assert self.processor._process_multiple_choice_text("C", question) == 2
        assert self.processor._process_multiple_choice_text("d", question) == 3

        # Test number answers
        assert self.processor._process_multiple_choice_text("0", question) == 0
        assert self.processor._process_multiple_choice_text("1", question) == 1
        assert self.processor._process_multiple_choice_text("2", question) == 2
        assert self.processor._process_multiple_choice_text("3", question) == 3

        # Test option text matching
        assert self.processor._process_multiple_choice_text("Option A", question) == 0
        assert self.processor._process_multiple_choice_text("option b", question) == 1

        # Test invalid answers
        assert self.processor._process_multiple_choice_text("E", question) is None
        assert self.processor._process_multiple_choice_text("5", question) is None

    def test_true_false_text_processing(self):
        """Test processing true/false text answers."""
        # Test true values
        for true_val in ["true", "t", "yes", "y", "1", "correct", "right"]:
            assert self.processor._process_true_false_text(true_val) is True
            assert self.processor._process_true_false_text(true_val.upper()) is True

        # Test false values
        for false_val in ["false", "f", "no", "n", "0", "incorrect", "wrong"]:
            assert self.processor._process_true_false_text(false_val) is False
            assert self.processor._process_true_false_text(false_val.upper()) is False

        # Test invalid values
        assert self.processor._process_true_false_text("maybe") is None
        assert self.processor._process_true_false_text("") is None

    def test_fill_blank_text_processing(self):
        """Test processing fill-in-the-blank text answers."""
        # Should just return the trimmed text
        assert self.processor._process_fill_blank_text("  answer  ") == "answer"
        assert self.processor._process_fill_blank_text("LA Galaxy") == "LA Galaxy"
        assert self.processor._process_fill_blank_text("") == ""

    def test_multiple_choice_validation(self):
        """Test multiple choice answer validation."""
        question = Question(
            question_text="Test question?",
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",  # Index-based correct answer
        )

        # Test correct answer
        assert self.processor._validate_multiple_choice_answer(question, 1) is True

        # Test incorrect answers
        assert self.processor._validate_multiple_choice_answer(question, 0) is False
        assert self.processor._validate_multiple_choice_answer(question, 2) is False
        assert self.processor._validate_multiple_choice_answer(question, 3) is False

        # Test invalid indices
        assert self.processor._validate_multiple_choice_answer(question, 4) is False
        assert self.processor._validate_multiple_choice_answer(question, -1) is False

    def test_multiple_choice_validation_text_answer(self):
        """Test multiple choice validation with text-based correct answer."""
        question = Question(
            question_text="Test question?",
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="Option B",  # Text-based correct answer
        )

        # Test correct answer
        assert self.processor._validate_multiple_choice_answer(question, 1) is True

        # Test incorrect answers
        assert self.processor._validate_multiple_choice_answer(question, 0) is False
        assert self.processor._validate_multiple_choice_answer(question, 2) is False
        assert self.processor._validate_multiple_choice_answer(question, 3) is False

    def test_true_false_validation(self):
        """Test true/false answer validation."""
        # Test with true answer
        question_true = Question(
            question_text="Test question?",
            question_type="true_false",
            correct_answer="true",
        )

        assert self.processor._validate_true_false_answer(question_true, True) is True
        assert self.processor._validate_true_false_answer(question_true, False) is False

        # Test with false answer
        question_false = Question(
            question_text="Test question?",
            question_type="true_false",
            correct_answer="false",
        )

        assert self.processor._validate_true_false_answer(question_false, False) is True
        assert self.processor._validate_true_false_answer(question_false, True) is False

    def test_fill_blank_validation(self):
        """Test fill-in-the-blank answer validation."""
        question = Question(
            question_text="What team plays at Dignity Health Sports Park?",
            question_type="fill_blank",
            correct_answer="LA Galaxy",
            answer_variations=["Los Angeles Galaxy", "Galaxy", "LAG"],
        )

        # Test exact match
        assert self.processor._validate_fill_blank_answer(question, "LA Galaxy") is True

        # Test case insensitive
        assert self.processor._validate_fill_blank_answer(question, "la galaxy") is True
        assert self.processor._validate_fill_blank_answer(question, "LA GALAXY") is True

        # Test variations
        assert (
            self.processor._validate_fill_blank_answer(question, "Los Angeles Galaxy")
            is True
        )
        assert self.processor._validate_fill_blank_answer(question, "galaxy") is True
        assert self.processor._validate_fill_blank_answer(question, "LAG") is True

        # Test with punctuation and extra spaces
        assert (
            self.processor._validate_fill_blank_answer(question, "LA Galaxy!") is True
        )
        assert (
            self.processor._validate_fill_blank_answer(question, "  LA Galaxy  ")
            is True
        )

        # Test incorrect answers
        assert self.processor._validate_fill_blank_answer(question, "LAFC") is False
        assert (
            self.processor._validate_fill_blank_answer(question, "Real Salt Lake")
            is False
        )

    def test_text_cleaning(self):
        """Test text cleaning for comparison."""
        # Test basic cleaning
        assert self.processor._clean_text_for_comparison("LA Galaxy") == "la galaxy"
        assert (
            self.processor._clean_text_for_comparison("  LA Galaxy!  ") == "la galaxy"
        )

        # Test punctuation removal
        assert (
            self.processor._clean_text_for_comparison("Hello, World!") == "hello world"
        )
        assert self.processor._clean_text_for_comparison("What's up?") == "whats up"

        # Test multiple spaces
        assert self.processor._clean_text_for_comparison("LA    Galaxy") == "la galaxy"

        # Test article removal (but not for short answers)
        assert self.processor._clean_text_for_comparison("The LA Galaxy") == "la galaxy"
        assert (
            self.processor._clean_text_for_comparison("The Galaxy") == "the galaxy"
        )  # Short (2 words), keep articles
        assert (
            self.processor._clean_text_for_comparison("A team") == "a team"
        )  # Short (2 words), keep articles

    def test_expected_answer_format(self):
        """Test getting expected answer format descriptions."""
        mc_question = Question(question_type="multiple_choice")
        tf_question = Question(question_type="true_false")
        fb_question = Question(question_type="fill_blank")

        assert "🇦, 🇧, 🇨, or 🇩" in self.processor.get_expected_answer_format(mc_question)
        assert "✅" in self.processor.get_expected_answer_format(tf_question)
        assert "❌" in self.processor.get_expected_answer_format(tf_question)
        assert "Type your answer" in self.processor.get_expected_answer_format(
            fb_question
        )

    def test_answer_display(self):
        """Test getting formatted answer display."""
        # Multiple choice with index answer
        mc_question = Question(
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",
        )
        display = self.processor.get_answer_display(mc_question)
        assert "🇧" in display
        assert "Option B" in display

        # True/false
        tf_question = Question(question_type="true_false", correct_answer="true")
        display = self.processor.get_answer_display(tf_question)
        assert "✅" in display
        assert "True" in display

        # Fill in blank
        fb_question = Question(question_type="fill_blank", correct_answer="LA Galaxy")
        display = self.processor.get_answer_display(fb_question)
        assert display == "LA Galaxy"

    def test_valid_reaction_check(self):
        """Test checking if reactions are valid for question types."""
        mc_question = Question(question_type="multiple_choice")
        tf_question = Question(question_type="true_false")
        fb_question = Question(question_type="fill_blank")

        # Multiple choice reactions
        assert self.processor.is_valid_reaction_for_question(mc_question, "🇦") is True
        assert self.processor.is_valid_reaction_for_question(mc_question, "🇧") is True
        assert self.processor.is_valid_reaction_for_question(mc_question, "✅") is False

        # True/false reactions
        assert self.processor.is_valid_reaction_for_question(tf_question, "✅") is True
        assert self.processor.is_valid_reaction_for_question(tf_question, "❌") is True
        assert self.processor.is_valid_reaction_for_question(tf_question, "🇦") is False

        # Fill blank (no valid reactions)
        assert self.processor.is_valid_reaction_for_question(fb_question, "🇦") is False
        assert self.processor.is_valid_reaction_for_question(fb_question, "✅") is False

    @pytest.mark.asyncio
    async def test_validate_answer_integration(self):
        """Test the main validate_answer method."""
        # Multiple choice question
        mc_question = Question(
            question_type="multiple_choice",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_answer="1",
        )

        assert await self.processor.validate_answer(mc_question, 1) is True
        assert await self.processor.validate_answer(mc_question, 0) is False

        # True/false question
        tf_question = Question(question_type="true_false", correct_answer="true")

        assert await self.processor.validate_answer(tf_question, True) is True
        assert await self.processor.validate_answer(tf_question, False) is False

        # Fill blank question
        fb_question = Question(question_type="fill_blank", correct_answer="LA Galaxy")

        assert await self.processor.validate_answer(fb_question, "LA Galaxy") is True
        assert await self.processor.validate_answer(fb_question, "la galaxy") is True
        assert await self.processor.validate_answer(fb_question, "LAFC") is False


if __name__ == "__main__":
    pytest.main([__file__])
