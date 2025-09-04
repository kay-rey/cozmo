"""
Answer Processing and Validation System for the Enhanced Trivia System.
Handles different answer types: reactions, text input, and various question formats.
"""

import re
import logging
from typing import Any, Optional, Union, List, Dict
from utils.models import Question, AnswerResult
import discord

logger = logging.getLogger(__name__)


class AnswerProcessor:
    """
    Processes and validates user answers for different question types.
    Supports reaction-based answers (multiple choice, true/false) and text-based answers (fill-in-blank).
    """

    def __init__(self):
        """Initialize the Answer Processor."""
        # Emoji mappings for different question types
        self.multiple_choice_emojis = {
            "🇦": 0,
            "🇧": 1,
            "🇨": 2,
            "🇩": 3,
        }

        self.true_false_emojis = {
            "✅": True,
            "❌": False,
        }

        # Alternative text representations for true/false
        self.true_values = ["true", "t", "yes", "y", "1", "correct", "right"]
        self.false_values = ["false", "f", "no", "n", "0", "incorrect", "wrong"]

    async def process_reaction_answer(
        self,
        question: Question,
        reaction: discord.Reaction,
        user: discord.User,
    ) -> Optional[Any]:
        """
        Process a reaction-based answer.

        Args:
            question: The Question object being answered.
            reaction: Discord reaction object.
            user: Discord user who reacted.

        Returns:
            Processed answer value or None if invalid reaction.
        """
        try:
            emoji_str = str(reaction.emoji)

            if question.question_type == "multiple_choice":
                return self._process_multiple_choice_reaction(emoji_str)
            elif question.question_type == "true_false":
                return self._process_true_false_reaction(emoji_str)
            else:
                # Fill-in-blank questions don't use reactions
                return None

        except Exception as e:
            logger.error(f"Error processing reaction answer: {e}")
            return None

    async def process_text_answer(
        self,
        question: Question,
        message: discord.Message,
    ) -> Optional[Any]:
        """
        Process a text-based answer.

        Args:
            question: The Question object being answered.
            message: Discord message containing the answer.

        Returns:
            Processed answer value or None if invalid.
        """
        try:
            text_content = message.content.strip()

            if not text_content:
                return None

            if question.question_type == "fill_blank":
                return self._process_fill_blank_text(text_content)
            elif question.question_type == "true_false":
                return self._process_true_false_text(text_content)
            elif question.question_type == "multiple_choice":
                return self._process_multiple_choice_text(text_content, question)
            else:
                return None

        except Exception as e:
            logger.error(f"Error processing text answer: {e}")
            return None

    async def validate_answer(self, question: Question, user_answer: Any) -> bool:
        """
        Validate a user's answer against the correct answer.

        Args:
            question: The Question object being answered.
            user_answer: The user's processed answer.

        Returns:
            True if the answer is correct, False otherwise.
        """
        try:
            if not question or user_answer is None:
                return False

            if question.question_type == "multiple_choice":
                return self._validate_multiple_choice_answer(question, user_answer)
            elif question.question_type == "true_false":
                return self._validate_true_false_answer(question, user_answer)
            elif question.question_type == "fill_blank":
                return self._validate_fill_blank_answer(question, user_answer)
            else:
                return False

        except Exception as e:
            logger.error(f"Error validating answer: {e}")
            return False

    def _process_multiple_choice_reaction(self, emoji_str: str) -> Optional[int]:
        """Process multiple choice reaction emoji."""
        return self.multiple_choice_emojis.get(emoji_str)

    def _process_true_false_reaction(self, emoji_str: str) -> Optional[bool]:
        """Process true/false reaction emoji."""
        return self.true_false_emojis.get(emoji_str)

    def _process_multiple_choice_text(
        self, text: str, question: Question
    ) -> Optional[int]:
        """
        Process multiple choice text answer.
        Accepts: A, B, C, D, 0, 1, 2, 3, or the actual option text.
        """
        text_lower = text.lower().strip()

        # Check for letter answers (A, B, C, D)
        if text_lower in ["a", "b", "c", "d"]:
            return ord(text_lower) - ord("a")

        # Check for number answers (0, 1, 2, 3)
        try:
            index = int(text_lower)
            if 0 <= index <= 3:
                return index
        except ValueError:
            pass

        # Check if text matches any of the options
        if question.options:
            for i, option in enumerate(question.options):
                if self._clean_text_for_comparison(
                    option
                ) == self._clean_text_for_comparison(text):
                    return i

        return None

    def _process_true_false_text(self, text: str) -> Optional[bool]:
        """Process true/false text answer."""
        text_lower = text.lower().strip()

        if text_lower in self.true_values:
            return True
        elif text_lower in self.false_values:
            return False

        return None

    def _process_fill_blank_text(self, text: str) -> str:
        """Process fill-in-the-blank text answer."""
        return text.strip()

    def _validate_multiple_choice_answer(
        self, question: Question, user_answer: int
    ) -> bool:
        """Validate multiple choice answer."""
        if not question.options or not isinstance(user_answer, int):
            return False

        if not (0 <= user_answer < len(question.options)):
            return False

        # Get the correct answer
        correct_answer = question.correct_answer

        # If correct_answer is an index, compare indices
        try:
            correct_index = int(correct_answer)
            return user_answer == correct_index
        except ValueError:
            # If correct_answer is text, compare with the option text
            if user_answer < len(question.options):
                user_option = question.options[user_answer]
                return self._clean_text_for_comparison(
                    user_option
                ) == self._clean_text_for_comparison(correct_answer)

        return False

    def _validate_true_false_answer(
        self, question: Question, user_answer: bool
    ) -> bool:
        """Validate true/false answer."""
        if not isinstance(user_answer, bool):
            return False

        correct_answer = question.correct_answer.lower().strip()

        # Determine if correct answer is true
        correct_is_true = correct_answer in ["true", "t", "yes", "y", "1"]

        return user_answer == correct_is_true

    def _validate_fill_blank_answer(self, question: Question, user_answer: str) -> bool:
        """Validate fill-in-the-blank answer with case-insensitive matching."""
        if not isinstance(user_answer, str):
            return False

        user_cleaned = self._clean_text_for_comparison(user_answer)

        # Check against main correct answer
        correct_cleaned = self._clean_text_for_comparison(question.correct_answer)
        if user_cleaned == correct_cleaned:
            return True

        # Check against answer variations
        if question.answer_variations:
            for variation in question.answer_variations:
                variation_cleaned = self._clean_text_for_comparison(variation)
                if user_cleaned == variation_cleaned:
                    return True

        return False

    def _clean_text_for_comparison(self, text: str) -> str:
        """
        Clean text for case-insensitive comparison.
        Removes extra whitespace, punctuation, and converts to lowercase.
        """
        if not text:
            return ""

        # Convert to lowercase
        cleaned = text.lower().strip()

        # Remove common punctuation that shouldn't affect correctness
        cleaned = re.sub(r"[.,!?;:\"'()]", "", cleaned)

        # Replace multiple spaces with single space
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Remove articles and common words that might not be essential
        # (be careful with this - only remove very common articles for longer phrases)
        articles = ["the", "a", "an"]
        words = cleaned.split()

        # Only remove articles if we have more than 2 words
        if len(words) > 2:
            filtered_words = [word for word in words if word not in articles]
        else:
            filtered_words = words

        return " ".join(filtered_words).strip()

    def get_expected_answer_format(self, question: Question) -> str:
        """
        Get a description of the expected answer format for a question.

        Args:
            question: The Question object.

        Returns:
            String describing the expected answer format.
        """
        if question.question_type == "multiple_choice":
            return "React with 🇦, 🇧, 🇨, or 🇩, or type A, B, C, D"
        elif question.question_type == "true_false":
            return "React with ✅ for True or ❌ for False, or type true/false"
        elif question.question_type == "fill_blank":
            return "Type your answer in the chat"
        else:
            return "Answer the question"

    def get_answer_display(self, question: Question) -> str:
        """
        Get a formatted display of the correct answer.

        Args:
            question: The Question object.

        Returns:
            Formatted string showing the correct answer.
        """
        if question.question_type == "multiple_choice" and question.options:
            try:
                # If correct_answer is an index
                correct_index = int(question.correct_answer)
                if 0 <= correct_index < len(question.options):
                    emoji = ["🇦", "🇧", "🇨", "🇩"][correct_index]
                    return f"{emoji} {question.options[correct_index]}"
            except ValueError:
                # If correct_answer is text, find matching option
                for i, option in enumerate(question.options):
                    if self._clean_text_for_comparison(
                        option
                    ) == self._clean_text_for_comparison(question.correct_answer):
                        emoji = ["🇦", "🇧", "🇨", "🇩"][i]
                        return f"{emoji} {option}"

            return question.correct_answer

        elif question.question_type == "true_false":
            correct_answer = question.correct_answer.lower().strip()
            is_true = correct_answer in ["true", "t", "yes", "y", "1"]
            emoji = "✅" if is_true else "❌"
            text = "True" if is_true else "False"
            return f"{emoji} {text}"

        elif question.question_type == "fill_blank":
            return question.correct_answer

        else:
            return question.correct_answer

    def is_valid_reaction_for_question(
        self, question: Question, emoji_str: str
    ) -> bool:
        """
        Check if a reaction emoji is valid for the given question type.

        Args:
            question: The Question object.
            emoji_str: String representation of the emoji.

        Returns:
            True if the emoji is valid for this question type.
        """
        if question.question_type == "multiple_choice":
            return emoji_str in self.multiple_choice_emojis
        elif question.question_type == "true_false":
            return emoji_str in self.true_false_emojis
        else:
            return False

    async def get_answer_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about answer processing (for debugging/monitoring).

        Returns:
            Dictionary containing processing statistics.
        """
        return {
            "supported_question_types": ["multiple_choice", "true_false", "fill_blank"],
            "multiple_choice_emojis": list(self.multiple_choice_emojis.keys()),
            "true_false_emojis": list(self.true_false_emojis.keys()),
            "true_text_values": self.true_values,
            "false_text_values": self.false_values,
        }
