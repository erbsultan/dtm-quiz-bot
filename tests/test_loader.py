import json

import pytest

from bot.loader import QuestionLoaderError, load_questions


def test_load_questions_returns_valid_questions(tmp_path):
    questions_file = tmp_path / "questions.json"
    questions_file.write_text(
        json.dumps(
            [
                {
                    "id": "q1",
                    "subject": "Math",
                    "topic": "Algebra",
                    "subtopic": "Linear equations",
                    "question": "2 + 2 = ?",
                    "options": ["3", "4"],
                    "correct_index": 1,
                    "explanation_correct": "2 + 2 equals 4.",
                    "wrong_explanations": {"0": "3 is one less than 4."},
                    "difficulty": "easy",
                    "source_refs": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    questions = load_questions(questions_file)

    assert questions[0]["id"] == "q1"


def test_load_questions_rejects_empty_file(tmp_path):
    questions_file = tmp_path / "questions.json"
    questions_file.write_text("[]", encoding="utf-8")

    with pytest.raises(QuestionLoaderError, match="non-empty list"):
        load_questions(questions_file)
