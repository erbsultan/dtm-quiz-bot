from bot.services.progress_service import (
    TREND_DECLINE,
    TREND_IMPROVEMENT,
    TREND_NOT_ENOUGH_DATA,
    TREND_STABLE,
    calculate_progress_trend,
    calculate_subject_performance,
    calculate_topic_performance,
    determine_pair_trend,
    select_mistake_question_ids,
)


def test_determine_pair_trend():
    assert determine_pair_trend(20.0, 2.1) == TREND_IMPROVEMENT
    assert determine_pair_trend(-10.0, -1.0) == TREND_DECLINE
    assert determine_pair_trend(0.0, 0.0) == TREND_STABLE


def test_calculate_progress_trend():
    assert calculate_progress_trend([]) == TREND_NOT_ENOUGH_DATA
    assert calculate_progress_trend([{"accuracy_percent": 60.0}]) == TREND_NOT_ENOUGH_DATA
    assert calculate_progress_trend([{"accuracy_percent": 60.0}, {"accuracy_percent": 80.0}]) == TREND_IMPROVEMENT
    assert calculate_progress_trend([{"accuracy_percent": 80.0}, {"accuracy_percent": 60.0}]) == TREND_DECLINE
    assert calculate_progress_trend([{"accuracy_percent": 70.0}, {"accuracy_percent": 70.0}]) == TREND_STABLE


def test_calculate_subject_performance():
    profile = {
        "subjects": [
            {"subject": "tarix", "points_per_correct": 3.1},
            {"subject": "matematika", "points_per_correct": 1.1},
        ]
    }
    rows = [
        {"subject": "tarix", "total": 5, "correct": 4},
        {"subject": "matematika", "total": 4, "correct": 1},
        {"subject": "ona_tili", "total": 1, "correct": 1},
    ]

    result = calculate_subject_performance(rows, profile, min_answers=2)

    assert [item["subject"] for item in result] == ["tarix", "matematika"]
    assert result[0]["accuracy"] == 80.0
    assert result[0]["earned_score"] == 12.4
    assert result[0]["possible_score"] == 15.5
    assert result[1]["accuracy"] == 25.0


def test_calculate_topic_performance():
    rows = [
        {"subject": "tarix", "topic": "WWII", "subtopic": "Conferences", "total": 3, "correct": 1},
        {"subject": "matematika", "topic": "Algebra", "subtopic": "Quadratic", "total": 2, "correct": 0},
        {"subject": "ona_tili", "topic": "Morfologiya", "subtopic": "Sifat", "total": 1, "correct": 0},
    ]

    result = calculate_topic_performance(rows, min_answers=2)

    assert [item["topic"] for item in result] == ["Algebra", "WWII"]
    assert result[0]["accuracy"] == 0.0
    assert result[1]["accuracy"] == 33.3


def test_select_mistake_question_ids():
    rows = [("105", "latest"), ("101", "older"), ("104", "oldest")]

    assert select_mistake_question_ids(rows, limit=2) == ["105", "101"]
