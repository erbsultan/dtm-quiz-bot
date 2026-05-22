from datetime import UTC, datetime
from typing import Any

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AnswerResult, TestAttempt, User
from bot.locales import DEFAULT_LANGUAGE, normalize_language, subject_name, t


async def get_or_create_user(
    session: AsyncSession,
    telegram_user: TelegramUser,
    language_code: str | None = None,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            language_code=normalize_language(language_code),
            exam_profile_code="60310200",
        )
        session.add(user)
        await session.flush()
        return user

    user.username = telegram_user.username
    user.first_name = telegram_user.first_name
    user.last_name = telegram_user.last_name
    if language_code:
        user.language_code = normalize_language(language_code)
    if not user.exam_profile_code:
        user.exam_profile_code = "60310200"
    return user


async def get_user_language(session: AsyncSession, telegram_user: TelegramUser) -> str:
    user = await get_or_create_user(session, telegram_user)
    await session.commit()
    return normalize_language(user.language_code)


async def get_user_exam_profile_code(session: AsyncSession, telegram_user: TelegramUser) -> str:
    user = await get_or_create_user(session, telegram_user)
    await session.commit()
    return user.exam_profile_code or "60310200"


async def set_user_language(session: AsyncSession, telegram_user: TelegramUser, language_code: str) -> User:
    user = await get_or_create_user(session, telegram_user, language_code)
    await session.commit()
    await session.refresh(user)
    return user


async def save_quiz_attempt(
    session: AsyncSession,
    telegram_user: TelegramUser,
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    started_at_iso: str,
    scoring_result: dict[str, Any],
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
        score=scoring_result["total_score"],
        max_score=scoring_result["max_score"],
        score_percent=scoring_result["percentage"],
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


def build_sources_message(questions: list[dict[str, Any]], language_code: str) -> str:
    language = normalize_language(language_code)
    source_lines: list[str] = [t(language, "sources_title"), ""]
    seen: set[str] = set()
    item_number = 1

    for question in questions:
        for source in question.get("source_refs", []):
            pages = _format_pages(source.get("page_start"), source.get("page_end"))
            book = _localized(source["book"], language)
            section = _localized(source["section"], language)
            key = f"{book}|{pages}|{section}"
            if key in seen:
                continue
            source_lines.extend(
                [
                    f"{item_number}. {book}",
                    f"   {t(language, 'pages')}: {pages}",
                    f"   {t(language, 'section')}: {section}",
                ]
            )
            seen.add(key)
            item_number += 1

    if item_number == 1:
        source_lines.append(t(language, "no_sources"))
    return "\n".join(source_lines)


def format_question(question: dict[str, Any], number: int, total: int, language_code: str) -> str:
    language = normalize_language(language_code)
    return (
        f"{t(language, 'question_header', number=number, total=total)}\n"
        f"{t(language, 'subject')}: {subject_name(language, question['subject'])}\n"
        f"{t(language, 'topic')}: {question['topic']}\n\n"
        f"{_localized(question['question'], language)}"
    )


def format_answer_feedback(question: dict[str, Any], selected_index: int, language_code: str) -> str:
    language = normalize_language(language_code)
    correct_index = question["correct_index"]
    is_correct = selected_index == correct_index
    selected_label = chr(65 + selected_index)
    correct_label = chr(65 + correct_index)
    correct_answer = _localized(question["options"], language)[correct_index]
    explanation = _localized(question["explanation_correct"], language)

    if not is_correct:
        explanation = question.get("wrong_explanations", {}).get(language, {}).get(str(selected_index), explanation)

    status = t(language, "correct") if is_correct else t(language, "incorrect", selected=selected_label)
    return (
        f"{status}\n\n"
        f"{t(language, 'correct_answer')}: {correct_label}. {correct_answer}\n\n"
        f"{t(language, 'explanation')}: {explanation}"
    )


def format_result(
    correct_count: int,
    total_questions: int,
    scoring_result: dict[str, Any],
    language_code: str,
) -> str:
    language = normalize_language(language_code)
    accuracy = round((correct_count / total_questions) * 100, 2) if total_questions else 0.0
    if accuracy >= 80:
        message = t(language, "interpret_high")
    elif accuracy >= 50:
        message = t(language, "interpret_mid")
    else:
        message = t(language, "interpret_low")

    breakdown_lines = []
    for item in scoring_result["breakdown"]:
        breakdown_lines.append(
            f"{subject_name(language, item['subject'])}: "
            f"{item['correct']}/{item['total']} -> {item['score']} {t(language, 'points')}"
        )

    return (
        f"{t(language, 'result_title')}\n"
        f"{t(language, 'correct_answers')}: {correct_count}/{total_questions}\n"
        f"{t(language, 'percentage')}: {accuracy}%\n"
        f"{t(language, 'dtm_score')}: {scoring_result['total_score']} / {scoring_result['max_score']}\n\n"
        f"{t(language, 'by_subject')}\n"
        f"{chr(10).join(breakdown_lines)}\n\n"
        f"{message}"
    )


def _format_pages(page_start: int | None, page_end: int | None) -> str:
    if page_start and page_end and page_start != page_end:
        return f"{page_start}-{page_end}"
    if page_start:
        return str(page_start)
    return "-"


def _localized(value: dict[str, Any], language_code: str) -> Any:
    language = normalize_language(language_code)
    return value.get(language) or value.get(DEFAULT_LANGUAGE)
