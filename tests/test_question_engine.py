"""
Unit tests for the Question Engine.
Tests question selection, validation, and formatting functionality.
"""

import pytest
import asyncio
from datetime import date
from utils.question_engine import QuestionEngine
from utils.models import Question


class TestQuestionEngine:
    """Test cases for the QuestionEngine class."""

    @pytest.fixture
    def question_engine(self):
        """Create a QuestionEngine instance for testing."""
        return QuestionEngine()

    @pytest.fixture
    def sample_multiple_choice_question(self):
        """Sample multiple choice question for testing."""
        return Question(
            id=1,
            question_text="What is 2 + 2?",
            question_type="multiple_choice",
            difficulty="easy",
            category="math",
            correct_answer="4",
            options=["2", "3", "4", "5"],
            explanation="Basic addition",
            point_value=10,
        )

    @pytest.fixture
    def sample_true_false_question(self):
        """Sample true/false question for testing."""
        return Question(
            id=2,
            question_text="The sky is blue.",
            question_type="true_false",
            difficulty="easy",
            category="general",
            correct_answer="true",
            explanation="The sky appears blue due to light scattering",
            point_value=10,
        )

    @pytest.fixture
    def sample_fill_blank_question(self):
        """Sample fill-in-the-blank question for testing."""
        return Question(
            id=3,
            question_text="The capital of France is _____.",
            question_type="fill_blank",
            difficulty="medium",
            category="geography",
            correct_answer="Paris",
            answer_variations=["paris", "PARIS"],
            explanation="Paris is the capital and largest city of France",
            point_value=20,
        )

    @pytest.mark.asyncio
    async def test_get_question_no_filters(self, question_engine):
        """Test getting a question without any filters."""
        question = await question_engine.get_question()
        assert question is not None
        assert isinstance(question, Question)
        assert question.difficulty in ["easy", "medium", "hard"]
        assert question.question_type in ["multiple_choice", "true_false", "fill_blank"]

    @pytest.mark.asyncio
    async def test_get_question_with_difficulty(self, question_engine):
        """Test getting a question with specific difficulty."""
        for difficulty in ["easy", "medium", "hard"]:
            question = await question_engine.get_question(difficulty=difficulty)
            assert question is not None
            assert question.difficulty == difficulty

    @pytest.mark.asyncio
    async def test_get_question_with_invalid_difficulty(self, question_engine):
        """Test getting a question with invalid difficulty defaults to medium."""
        question = await question_engine.get_question(difficulty="invalid")
        assert question is not None
        # Should default to medium or return any valid question

    @pytest.mark.asyncio
    async def test_get_question_with_type_filter(self, question_engine):
        """Test getting a question with specific type filter."""
        for question_type in ["multiple_choice", "true_false", "fill_blank"]:
            question = await question_engine.get_question(question_type=question_type)
            if question:  # Some types might not be available in test data
                assert question.question_type == question_type

    @pytest.mark.asyncio
    async def test_get_daily_challenge_question(self, question_engine):
        """Test getting daily challenge question."""
        question1 = await question_engine.get_daily_challenge_question()
        question2 = await question_engine.get_daily_challenge_question()

        # Should return the same question for the same day
        if question1 and question2:
            assert question1.id == question2.id
            assert question1.difficulty == "hard"
            # Points should be doubled for daily challenge
            assert (
                question1.point_value >= 60
            )  # Hard questions are 30 points, doubled = 60

    @pytest.mark.asyncio
    async def test_get_weekly_challenge_questions(self, question_engine):
        """Test getting weekly challenge questions."""
        questions1 = await question_engine.get_weekly_challenge_questions()
        questions2 = await question_engine.get_weekly_challenge_questions()

        # Should return the same questions for the same week
        assert len(questions1) == len(questions2)
        if questions1 and questions2:
            for q1, q2 in zip(questions1, questions2):
                assert q1.id == q2.id

    def test_validate_multiple_choice_answer_by_index(
        self, question_engine, sample_multiple_choice_question
    ):
        """Test validating multiple choice answer by index."""
        # Test correct answer by index
        result = asyncio.run(
            question_engine.validate_answer(sample_multiple_choice_question, "2")
        )  # Index 2 = "4"
        assert result is True

        # Test incorrect answer by index
        result = asyncio.run(
            question_engine.validate_answer(sample_multiple_choice_question, "0")
        )  # Index 0 = "2"
        assert result is False

    def test_validate_multiple_choice_answer_by_text(
        self, question_engine, sample_multiple_choice_question
    ):
        """Test validating multiple choice answer by text."""
        # Test correct answer by text
        result = asyncio.run(
            question_engine.validate_answer(sample_multiple_choice_question, "4")
        )
        assert result is True

        # Test incorrect answer by text
        result = asyncio.run(
            question_engine.validate_answer(sample_multiple_choice_question, "3")
        )
        assert result is False

    def test_validate_true_false_answer(
        self, question_engine, sample_true_false_question
    ):
        """Test validating true/false answers."""
        # Test various true representations
        for true_answer in ["true", "True", "TRUE", "t", "T", "yes", "y", "1", "✅"]:
            result = asyncio.run(
                question_engine.validate_answer(sample_true_false_question, true_answer)
            )
            assert result is True, f"Failed for true answer: {true_answer}"

        # Test various false representations
        for false_answer in ["false", "False", "FALSE", "f", "F", "no", "n", "0", "❌"]:
            result = asyncio.run(
                question_engine.validate_answer(
                    sample_true_false_question, false_answer
                )
            )
            assert result is False, f"Failed for false answer: {false_answer}"

    def test_validate_fill_blank_answer(
        self, question_engine, sample_fill_blank_question
    ):
        """Test validating fill-in-the-blank answers."""
        # Test correct answer (exact match)
        result = asyncio.run(
            question_engine.validate_answer(sample_fill_blank_question, "Paris")
        )
        assert result is True

        # Test correct answer (case insensitive)
        result = asyncio.run(
            question_engine.validate_answer(sample_fill_blank_question, "paris")
        )
        assert result is True

        # Test answer variation
        result = asyncio.run(
            question_engine.validate_answer(sample_fill_blank_question, "PARIS")
        )
        assert result is True

        # Test incorrect answer
        result = asyncio.run(
            question_engine.validate_answer(sample_fill_blank_question, "London")
        )
        assert result is False

    def test_validate_answer_with_none_inputs(self, question_engine):
        """Test validating answers with None inputs."""
        result = asyncio.run(question_engine.validate_answer(None, "answer"))
        assert result is False

        question = Question(question_text="Test", correct_answer="test")
        result = asyncio.run(question_engine.validate_answer(question, None))
        assert result is False

    def test_clean_answer(self, question_engine):
        """Test the answer cleaning functionality."""
        # Test case normalization
        assert question_engine._clean_answer("HELLO") == "hello"

        # Test whitespace removal
        assert question_engine._clean_answer("  hello world  ") == "hello world"

        # Test punctuation removal
        assert question_engine._clean_answer("hello, world!") == "hello world"

        # Test multiple spaces
        assert question_engine._clean_answer("hello    world") == "hello world"

    def test_format_question_for_discord_multiple_choice(
        self, question_engine, sample_multiple_choice_question
    ):
        """Test formatting multiple choice question for Discord."""
        formatted = question_engine.format_question_for_discord(
            sample_multiple_choice_question
        )

        assert "title" in formatted
        assert "description" in formatted
        assert "color" in formatted
        assert "Easy Question" in formatted["title"]
        assert "10 points" in formatted["title"]
        assert formatted["description"] == "What is 2 + 2?"

    def test_format_question_for_discord_true_false(
        self, question_engine, sample_true_false_question
    ):
        """Test formatting true/false question for Discord."""
        formatted = question_engine.format_question_for_discord(
            sample_true_false_question
        )

        assert "title" in formatted
        assert "description" in formatted
        assert "footer" in formatted
        assert "✅" in formatted["footer"]["text"]
        assert "❌" in formatted["footer"]["text"]

    def test_format_question_for_discord_fill_blank(
        self, question_engine, sample_fill_blank_question
    ):
        """Test formatting fill-in-the-blank question for Discord."""
        formatted = question_engine.format_question_for_discord(
            sample_fill_blank_question
        )

        assert "title" in formatted
        assert "description" in formatted
        assert "footer" in formatted
        assert "Type your answer" in formatted["footer"]["text"]

    def test_format_question_for_discord_empty(self, question_engine):
        """Test formatting empty question for Discord."""
        formatted = question_engine.format_question_for_discord(None)
        assert formatted == {}

    def test_get_difficulty_color(self, question_engine):
        """Test getting difficulty colors."""
        assert question_engine._get_difficulty_color("easy") == 0x00FF00
        assert question_engine._get_difficulty_color("medium") == 0xFFFF00
        assert question_engine._get_difficulty_color("hard") == 0xFF0000
        assert question_engine._get_difficulty_color("invalid") == 0x0099FF  # Default

    @pytest.mark.asyncio
    async def test_add_custom_question_valid(self, question_engine):
        """Test adding a valid custom question."""
        question_data = {
            "question": "What is the answer to everything?",
            "question_type": "multiple_choice",
            "difficulty": "hard",
            "category": "philosophy",
            "correct_answer": "42",
            "options": ["41", "42", "43", "44"],
            "explanation": "From The Hitchhiker's Guide to the Galaxy",
            "point_value": 30,
        }

        result = await question_engine.add_custom_question(question_data)
        assert result is True

    @pytest.mark.asyncio
    async def test_add_custom_question_invalid(self, question_engine):
        """Test adding invalid custom questions."""
        # Missing required field
        invalid_data = {
            "question": "Test question",
            "question_type": "multiple_choice",
            # Missing difficulty and correct_answer
        }

        result = await question_engine.add_custom_question(invalid_data)
        assert result is False

        # Invalid question type
        invalid_data = {
            "question": "Test question",
            "question_type": "invalid_type",
            "difficulty": "easy",
            "correct_answer": "test",
        }

        result = await question_engine.add_custom_question(invalid_data)
        assert result is False

    def test_get_question_statistics(self, question_engine):
        """Test getting question statistics."""
        stats = question_engine.get_question_statistics()

        assert "total_questions" in stats
        assert "by_difficulty" in stats
        assert "by_type" in stats
        assert "by_category" in stats

        assert isinstance(stats["total_questions"], int)
        assert stats["total_questions"] > 0

        # Check that we have questions in each difficulty
        for difficulty in ["easy", "medium", "hard"]:
            assert difficulty in stats["by_difficulty"]
            assert stats["by_difficulty"][difficulty] >= 0

    def test_clear_caches(self, question_engine):
        """Test clearing daily and weekly caches."""
        # These should not raise exceptions
        question_engine.clear_daily_cache()
        question_engine.clear_weekly_cache()

        # Verify caches are empty
        assert len(question_engine._daily_challenge_cache) == 0
        assert len(question_engine._weekly_challenge_cache) == 0


if __name__ == "__main__":
    pytest.main([__file__])
