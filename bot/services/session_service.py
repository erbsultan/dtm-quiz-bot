from datetime import UTC, datetime
from typing import Any

ACTIVE_SESSION_STATUSES = ("in_progress", "paused")


async def get_active_session(session: Any, user_id: int) -> Any | None:
    from sqlalchemy import desc, select

    from bot.db.models import QuizSession

    result = await session.execute(
        select(QuizSession)
        .where(QuizSession.user_id == user_id, QuizSession.status.in_(ACTIVE_SESSION_STATUSES))
        .order_by(desc(QuizSession.updated_at), desc(QuizSession.id))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_session(
    session: Any,
    user_id: int,
    mode: str,
    language_code: str,
    exam_profile_code: str | None,
    question_ids: list[str],
) -> Any:
    from bot.db.models import QuizSession

    quiz_session = QuizSession(
        user_id=user_id,
        mode=mode,
        status="in_progress",
        language_code=language_code,
        exam_profile_code=exam_profile_code,
        current_question_index=0,
        question_ids=question_ids,
        answers=[],
    )
    session.add(quiz_session)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


async def save_answer(session: Any, session_id: int, answer_data: dict[str, Any]) -> Any | None:
    from bot.db.models import QuizSession

    quiz_session = await session.get(QuizSession, session_id)
    if quiz_session is None:
        return None

    answers = upsert_answer(quiz_session.answers or [], answer_data)
    quiz_session.answers = answers
    quiz_session.current_question_index = min(len(answers), len(quiz_session.question_ids or []))
    quiz_session.status = "in_progress"
    quiz_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


async def pause_session(session: Any, session_id: int) -> Any | None:
    from bot.db.models import QuizSession

    quiz_session = await session.get(QuizSession, session_id)
    if quiz_session is None:
        return None
    quiz_session.status = "paused"
    quiz_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


async def resume_session(session: Any, session_id: int) -> Any | None:
    from bot.db.models import QuizSession

    quiz_session = await session.get(QuizSession, session_id)
    if quiz_session is None:
        return None
    quiz_session.status = "in_progress"
    quiz_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


async def cancel_session(session: Any, session_id: int) -> Any | None:
    from bot.db.models import QuizSession

    quiz_session = await session.get(QuizSession, session_id)
    if quiz_session is None:
        return None
    quiz_session.status = "cancelled"
    quiz_session.finished_at = datetime.now(UTC)
    quiz_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


async def complete_session(session: Any, session_id: int) -> Any | None:
    from bot.db.models import QuizSession

    quiz_session = await session.get(QuizSession, session_id)
    if quiz_session is None:
        return None
    quiz_session.status = "completed"
    quiz_session.finished_at = datetime.now(UTC)
    quiz_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(quiz_session)
    return quiz_session


def upsert_answer(existing_answers: list[dict[str, Any]], answer_data: dict[str, Any]) -> list[dict[str, Any]]:
    question_id = str(answer_data["question_id"])
    answers = [answer for answer in existing_answers if str(answer.get("question_id")) != question_id]
    answers.append(
        {
            "question_id": question_id,
            "selected_index": answer_data["selected_index"],
            "correct_index": answer_data["correct_index"],
            "is_correct": answer_data["is_correct"],
        }
    )
    return answers


def restore_answers_for_questions(
    question_ids: list[str],
    stored_answers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index_by_question_id = {str(question_id): index for index, question_id in enumerate(question_ids)}
    restored = []
    for answer in stored_answers:
        question_id = str(answer.get("question_id"))
        if question_id not in index_by_question_id:
            continue
        restored.append(
            {
                "question_index": index_by_question_id[question_id],
                "selected_index": answer["selected_index"],
                "is_correct": answer["is_correct"],
            }
        )
    return sorted(restored, key=lambda answer: answer["question_index"])


def filter_questions_by_ids(
    all_questions: list[dict[str, Any]],
    question_ids: list[str],
) -> list[dict[str, Any]]:
    question_by_id = {str(question["id"]): question for question in all_questions}
    return [question_by_id[question_id] for question_id in question_ids if question_id in question_by_id]


def has_missing_questions(all_questions: list[dict[str, Any]], question_ids: list[str]) -> bool:
    existing_ids = {str(question["id"]) for question in all_questions}
    return any(str(question_id) not in existing_ids for question_id in question_ids)
