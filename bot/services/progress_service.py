from typing import Any

TREND_IMPROVEMENT = "improvement"
TREND_DECLINE = "decline"
TREND_STABLE = "stable"
TREND_NOT_ENOUGH_DATA = "not_enough_data"


async def get_attempt_comparison(
    session: Any,
    user_id: int,
    current_attempt_id: int,
) -> dict[str, Any] | None:
    from sqlalchemy import desc, select

    from bot.db.models import TestAttempt

    current = await session.get(TestAttempt, current_attempt_id)
    if current is None:
        return None

    previous_result = await session.execute(
        select(TestAttempt)
        .where(TestAttempt.user_id == user_id, TestAttempt.id != current_attempt_id)
        .order_by(desc(TestAttempt.finished_at), desc(TestAttempt.id))
        .limit(1)
    )
    previous = previous_result.scalar_one_or_none()
    if previous is None:
        return None

    accuracy_diff = round(current.accuracy_percent - previous.accuracy_percent, 2)
    score_diff = round(current.score - previous.score, 2)

    return {
        "previous_accuracy": round(previous.accuracy_percent, 1),
        "current_accuracy": round(current.accuracy_percent, 1),
        "accuracy_diff": accuracy_diff,
        "previous_score": round(previous.score, 1),
        "current_score": round(current.score, 1),
        "score_diff": score_diff,
        "trend": determine_pair_trend(accuracy_diff, score_diff),
    }


async def get_recent_attempts(session: Any, user_id: int, limit: int = 3) -> list[dict[str, Any]]:
    from sqlalchemy import desc, select

    from bot.db.models import TestAttempt

    result = await session.execute(
        select(TestAttempt)
        .where(TestAttempt.user_id == user_id)
        .order_by(desc(TestAttempt.finished_at), desc(TestAttempt.id))
        .limit(limit)
    )
    attempts = list(reversed(result.scalars().all()))
    return [
        {
            "id": attempt.id,
            "accuracy_percent": round(attempt.accuracy_percent, 1),
            "score": round(attempt.score, 1),
            "max_score": round(attempt.max_score, 1),
        }
        for attempt in attempts
    ]


async def get_progress_trend(session: Any, user_id: int) -> str:
    attempts = await get_recent_attempts(session, user_id, limit=3)
    return calculate_progress_trend(attempts)


async def get_subject_performance(
    session: Any,
    user_id: int,
    profile: dict[str, Any],
    min_answers: int = 2,
) -> list[dict[str, Any]]:
    from sqlalchemy import case, func, select

    from bot.db.models import AnswerResult, TestAttempt

    result = await session.execute(
        select(
            AnswerResult.subject,
            func.count(AnswerResult.id),
            func.sum(case((AnswerResult.is_correct.is_(True), 1), else_=0)),
        )
        .join(TestAttempt, TestAttempt.id == AnswerResult.attempt_id)
        .where(TestAttempt.user_id == user_id)
        .group_by(AnswerResult.subject)
    )
    rows = [
        {"subject": subject, "total": int(total), "correct": int(correct or 0)}
        for subject, total, correct in result.all()
    ]
    return calculate_subject_performance(rows, profile, min_answers=min_answers)


async def get_topic_performance(
    session: Any,
    user_id: int,
    min_answers: int = 2,
) -> list[dict[str, Any]]:
    from sqlalchemy import case, func, select

    from bot.db.models import AnswerResult, TestAttempt

    result = await session.execute(
        select(
            AnswerResult.subject,
            AnswerResult.topic,
            AnswerResult.subtopic,
            func.count(AnswerResult.id),
            func.sum(case((AnswerResult.is_correct.is_(True), 1), else_=0)),
        )
        .join(TestAttempt, TestAttempt.id == AnswerResult.attempt_id)
        .where(TestAttempt.user_id == user_id)
        .group_by(AnswerResult.subject, AnswerResult.topic, AnswerResult.subtopic)
    )
    rows = [
        {
            "subject": subject,
            "topic": topic,
            "subtopic": subtopic,
            "total": int(total),
            "correct": int(correct or 0),
        }
        for subject, topic, subtopic, total, correct in result.all()
    ]
    return calculate_topic_performance(rows, min_answers=min_answers)


async def get_mistake_question_ids(session: Any, user_id: int, limit: int = 10) -> list[str]:
    from sqlalchemy import desc, func, select

    from bot.db.models import AnswerResult, TestAttempt

    last_mistake_at = func.max(AnswerResult.created_at).label("last_mistake_at")
    wrong_count = func.count(AnswerResult.id).label("wrong_count")
    result = await session.execute(
        select(AnswerResult.question_id, wrong_count, last_mistake_at)
        .join(TestAttempt, TestAttempt.id == AnswerResult.attempt_id)
        .where(TestAttempt.user_id == user_id, AnswerResult.is_correct.is_(False))
        .group_by(AnswerResult.question_id)
        .order_by(desc(wrong_count), desc(last_mistake_at))
        .limit(limit)
    )
    return select_mistake_question_ids(result.all(), limit=limit)


def determine_pair_trend(accuracy_diff: float, score_diff: float, threshold: float = 0.01) -> str:
    if accuracy_diff > threshold or score_diff > threshold:
        return TREND_IMPROVEMENT
    if accuracy_diff < -threshold or score_diff < -threshold:
        return TREND_DECLINE
    return TREND_STABLE


def calculate_progress_trend(attempts: list[dict[str, Any]], threshold: float = 0.01) -> str:
    if len(attempts) < 2:
        return TREND_NOT_ENOUGH_DATA

    first = attempts[0]["accuracy_percent"]
    last = attempts[-1]["accuracy_percent"]
    diff = last - first
    if diff > threshold:
        return TREND_IMPROVEMENT
    if diff < -threshold:
        return TREND_DECLINE
    return TREND_STABLE


def calculate_subject_performance(
    rows: list[dict[str, Any]],
    profile: dict[str, Any],
    min_answers: int = 2,
) -> list[dict[str, Any]]:
    points_by_subject = {item["subject"]: float(item["points_per_correct"]) for item in profile["subjects"]}
    performance = []

    for row in rows:
        total = int(row["total"])
        if total < min_answers:
            continue
        correct = int(row["correct"])
        points_per_correct = points_by_subject.get(row["subject"], 0.0)
        performance.append(
            {
                "subject": row["subject"],
                "total": total,
                "correct": correct,
                "accuracy": round((correct / total) * 100, 1) if total else 0.0,
                "earned_score": round(correct * points_per_correct, 1),
                "possible_score": round(total * points_per_correct, 1),
            }
        )

    return sorted(performance, key=lambda item: (-item["accuracy"], -item["total"], item["subject"]))


def calculate_topic_performance(rows: list[dict[str, Any]], min_answers: int = 2) -> list[dict[str, Any]]:
    performance = []
    for row in rows:
        total = int(row["total"])
        if total < min_answers:
            continue
        correct = int(row["correct"])
        performance.append(
            {
                "subject": row["subject"],
                "topic": row["topic"],
                "subtopic": row.get("subtopic"),
                "total": total,
                "correct": correct,
                "accuracy": round((correct / total) * 100, 1) if total else 0.0,
            }
        )

    return sorted(performance, key=lambda item: (item["accuracy"], -item["total"], item["topic"]))


def select_mistake_question_ids(rows: list[Any], limit: int = 10) -> list[str]:
    return [str(row[0]) for row in rows[:limit]]


def prioritize_mistake_rows(rows: list[dict[str, Any]], limit: int = 10) -> list[str]:
    sorted_rows = sorted(
        rows,
        key=lambda row: (int(row["wrong_count"]), row.get("last_wrong_at") or ""),
        reverse=True,
    )
    return [str(row["question_id"]) for row in sorted_rows[:limit]]
