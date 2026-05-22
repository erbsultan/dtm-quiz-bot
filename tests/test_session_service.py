from bot.services.session_service import (
    filter_questions_by_ids,
    has_missing_questions,
    restore_answers_for_questions,
    upsert_answer,
)


def test_upsert_answer_replaces_existing_question_answer():
    answers = upsert_answer(
        [{"question_id": "101", "selected_index": 0, "correct_index": 1, "is_correct": False}],
        {"question_id": "101", "selected_index": 1, "correct_index": 1, "is_correct": True},
    )

    assert len(answers) == 1
    assert answers[0]["selected_index"] == 1
    assert answers[0]["is_correct"] is True


def test_restore_answers_for_questions_adds_question_indexes():
    answers = restore_answers_for_questions(
        ["101", "102"],
        [
            {"question_id": "102", "selected_index": 0, "correct_index": 0, "is_correct": True},
            {"question_id": "101", "selected_index": 2, "correct_index": 1, "is_correct": False},
        ],
    )

    assert answers == [
        {"question_index": 0, "selected_index": 2, "is_correct": False},
        {"question_index": 1, "selected_index": 0, "is_correct": True},
    ]


def test_filter_questions_by_ids_preserves_session_order():
    questions = [{"id": 102}, {"id": 101}, {"id": 103}]

    assert filter_questions_by_ids(questions, ["101", "102"]) == [{"id": 101}, {"id": 102}]


def test_has_missing_questions_detects_removed_question():
    questions = [{"id": 101}]

    assert has_missing_questions(questions, ["101", "999"]) is True
    assert has_missing_questions(questions, ["101"]) is False
