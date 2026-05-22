from datetime import UTC, datetime
from typing import Any

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AnswerResult, TestAttempt, User


async def get_or_create_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )
        session.add(user)
        await session.flush()
        return user

    user.username = telegram_user.username
    user.first_name = telegram_user.first_name
    user.last_name = telegram_user.last_name
    return user


async def save_quiz_attempt(
    session: AsyncSession,
    telegram_user: TelegramUser,
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    started_at_iso: str,
) -> TestAttempt:
    user = await get_or_create_user(session, telegram_user)
    started_at = datetime.fromisoformat(started_at_iso)
    finished_at = datetime.now(UTC)
    total_questions = len(questions)
    correct_count = sum(1 for answer in answers if answer["is_correct"])
    wrong_count = total_questions - correct_count
    accuracy_percent = round((correct_count / total_questions) * 100, 2) if total_questions else 0.0
    subjects = sorted({question["subject"] for question in questions})
    topics = sorted({question["topic"] for question in questions})

    attempt = TestAttempt(
        user_id=user.id,
        mode="sample",
        subject=", ".join(subjects),
        topic=", ".join(topics),
        total_questions=total_questions,
        correct_count=correct_count,
        wrong_count=wrong_count,
        accuracy_percent=accuracy_percent,
        started_at=started_at,
        finished_at=finished_at,
    )
    session.add(attempt)
    await session.flush()

    for answer in answers:
        question = questions[answer["question_index"]]
        session.add(
            AnswerResult(
                attempt_id=attempt.id,
                question_id=str(question["id"]),
                selected_index=answer["selected_index"],
                correct_index=question["correct_index"],
                is_correct=answer["is_correct"],
                subject=question["subject"],
                topic=question["topic"],
                subtopic=question.get("subtopic"),
                difficulty=question.get("difficulty"),
            )
        )

    await session.commit()
    await session.refresh(attempt)
    return attempt


def build_sources_message(questions: list[dict[str, Any]]) -> str:
    source_lines: list[str] = []
    seen: set[str] = set()

    for question in questions:
        for source in question.get("source_refs", []):
            pages = _format_pages(source.get("page_start"), source.get("page_end"))
            line = f"- {source.get('book', 'Unknown source')}, {pages}, {source.get('section', 'section not specified')}"
            if line not in seen:
                source_lines.append(line)
                seen.add(line)

    sources = "\n".join(source_lines) if source_lines else "- No source references provided."
    return f"Before this test, read these books/pages:\n\n{sources}"


def format_question(question: dict[str, Any], number: int, total: int) -> str:
    return (
        f"Question {number}/{total}\n"
        f"Subject: {question['subject']}\n"
        f"Topic: {question['topic']}\n\n"
        f"{question['question']}"
    )


def format_answer_feedback(question: dict[str, Any], selected_index: int) -> str:
    correct_index = question["correct_index"]
    is_correct = selected_index == correct_index
    selected_label = chr(65 + selected_index)
    correct_label = chr(65 + correct_index)
    correct_answer = question["options"][correct_index]
    explanation = question["explanation_correct"]

    if not is_correct:
        explanation = question.get("wrong_explanations", {}).get(str(selected_index), explanation)

    status = "Correct!" if is_correct else f"Incorrect. You selected {selected_label}."
    return (
        f"{status}\n\n"
        f"Correct answer: {correct_label}. {correct_answer}\n\n"
        f"Explanation: {explanation}"
    )


def format_result(correct_count: int, total_questions: int) -> str:
    accuracy = round((correct_count / total_questions) * 100, 2) if total_questions else 0.0
    if accuracy >= 80:
        message = "Great work. Keep reviewing explanations to make it stick."
    elif accuracy >= 50:
        message = "Good start. Review the missed topics and try again."
    else:
        message = "This is a baseline. Read the sources and repeat the test."

    return f"Result: {correct_count}/{total_questions}\nAccuracy: {accuracy}%\n\n{message}"


def _format_pages(page_start: int | None, page_end: int | None) -> str:
    if page_start and page_end and page_start != page_end:
        return f"pages {page_start}-{page_end}"
    if page_start:
        return f"page {page_start}"
    return "pages not specified"
