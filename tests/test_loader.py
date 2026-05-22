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
                    "subject": "matematika",
                    "subject_group": "mandatory",
                    "topic": "Algebra",
                    "subtopic": "Linear equations",
                    "question": {"uz": "2 + 2 = ?", "ru": "2 + 2 = ?"},
                    "options": {"uz": ["3", "4"], "ru": ["3", "4"]},
                    "correct_index": 1,
                    "explanation_correct": {"uz": "2 + 2 = 4.", "ru": "2 + 2 = 4."},
                    "wrong_explanations": {
                        "uz": {"0": "3 is one less than 4."},
                        "ru": {"0": "3 меньше 4."},
                    },
                    "difficulty": "easy",
                    "source_refs": [
                        {
                            "book": {"uz": "Algebra", "ru": "Алгебра"},
                            "page_start": 1,
                            "page_end": 2,
                            "section": {"uz": "Sonlar", "ru": "Числа"},
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    questions = load_questions(questions_file)

    assert questions[0]["id"] == "q1"
    assert questions[0]["question"]["uz"] == "2 + 2 = ?"


def test_load_questions_rejects_empty_file(tmp_path):
    questions_file = tmp_path / "questions.json"
    questions_file.write_text("[]", encoding="utf-8")

    with pytest.raises(QuestionLoaderError, match="non-empty list"):
        load_questions(questions_file)


def test_load_questions_rejects_old_flat_question_format(tmp_path):
    questions_file = tmp_path / "questions.json"
    questions_file.write_text(
        json.dumps(
            [
                {
                    "id": "q1",
                    "subject": "Math",
                    "subject_group": "mandatory",
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

    with pytest.raises(QuestionLoaderError, match="Stage 2"):
        load_questions(questions_file)
