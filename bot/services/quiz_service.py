from datetime import UTC, datetime
from typing import Any

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AnswerResult, TestAttempt, User
from bot.locales import DEFAULT_LANGUAGE, normalize_language, subject_name, t
from bot.services.progress_service import (
    TREND_DECLINE,
    TREND_IMPROVEMENT,
    TREND_NOT_ENOUGH_DATA,
    TREND_STABLE,
)


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
    mode: str = "sample",
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
        mode=mode,
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
    correct_label = chr(65 + correct_index)
    correct_answer = _localized(question["options"], language)[correct_index]
    explanation = _localized(question["explanation_correct"], language)

    if is_correct:
        return f"{t(language, 'correct')}\n{t(language, 'explanation')}: {explanation}"

    return (
        f"{t(language, 'incorrect')}\n"
        f"{t(language, 'correct_answer')}: {correct_label}. {correct_answer}\n"
        f"{t(language, 'explanation')}: {explanation}"
    )


def format_result(
    correct_count: int,
    total_questions: int,
    scoring_result: dict[str, Any],
    language_code: str,
) -> str:
    language = normalize_language(language_code)
    accuracy = round((correct_count / total_questions) * 100, 1) if total_questions else 0.0
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
            f"{item['correct']}/{item['total']} -> "
            f"{_format_number(item['score'])} / {_format_number(item['max_score'])} {t(language, 'points')}"
        )

    return (
        f"{t(language, 'result_title')}\n"
        f"{t(language, 'correct_answers')}: {correct_count}/{total_questions}\n"
        f"{t(language, 'percentage')}: {accuracy}%\n"
        "\n"
        f"{t(language, 'mini_test_score')}: "
        f"{_format_number(scoring_result['total_score'])} / {_format_number(scoring_result['max_score'])}\n"
        f"{t(language, 'projected_full_score')}: "
        f"{_format_number(scoring_result['projected_full_score'])} / "
        f"{_format_number(scoring_result['full_max_score'])}\n\n"
        f"{t(language, 'by_subject')}\n"
        f"{chr(10).join(breakdown_lines)}\n\n"
        f"{message}"
    )


def format_attempt_comparison(comparison: dict[str, Any] | None, language_code: str) -> str:
    language = normalize_language(language_code)
    if comparison is None:
        return t(language, "first_attempt_comparison")

    return (
        f"{t(language, 'comparison_title')}\n"
        f"{t(language, 'previous_accuracy')}: {_format_number(comparison['previous_accuracy'])}%\n"
        f"{t(language, 'current_accuracy')}: {_format_number(comparison['current_accuracy'])}%\n"
        f"{t(language, 'change')}: {_format_signed(comparison['accuracy_diff'])} {t(language, 'percentage_points')}\n\n"
        f"{t(language, 'previous_score')}: {_format_number(comparison['previous_score'])}\n"
        f"{t(language, 'current_score')}: {_format_number(comparison['current_score'])}\n"
        f"{t(language, 'change')}: {_format_signed(comparison['score_diff'])}\n\n"
        f"{t(language, 'trend')}: {t(language, _trend_key(comparison['trend']))}"
    )


def format_mistakes_review(
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    language_code: str,
    limit: int = 5,
) -> str | None:
    language = normalize_language(language_code)
    wrong_answers = [answer for answer in answers if not answer["is_correct"]]
    if not wrong_answers:
        return None

    lines = [t(language, "mistakes_review_title"), ""]
    for number, answer in enumerate(wrong_answers[:limit], start=1):
        question = questions[answer["question_index"]]
        selected_index = answer["selected_index"]
        correct_index = question["correct_index"]
        options = _localized(question["options"], language)
        why_wrong = get_wrong_explanation(question, selected_index, language)
        source = _format_first_source(question, language)
        lines.extend(
            [
                f"{number}. {t(language, 'mistake_question')}:",
                _localized(question["question"], language),
                "",
                f"{t(language, 'selected_answer')}:",
                f"{chr(65 + selected_index)}. {options[selected_index]}",
                "",
                f"{t(language, 'correct_answer')}:",
                f"{chr(65 + correct_index)}. {options[correct_index]}",
                "",
                f"{t(language, 'why_wrong')}:",
                why_wrong,
                "",
                f"{t(language, 'correct_explanation')}:",
                _localized(question["explanation_correct"], language),
                "",
                f"{t(language, 'repeat_for')}:",
                source or "-",
                "",
            ]
        )

    remaining = len(wrong_answers) - limit
    if remaining > 0:
        lines.append(t(language, "more_mistakes", count=remaining))

    return "\n".join(lines).strip()


def format_repeat_sources(
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    language_code: str,
) -> str:
    language = normalize_language(language_code)
    wrong_questions = [questions[answer["question_index"]] for answer in answers if not answer["is_correct"]]
    if not wrong_questions:
        return t(language, "no_wrong_answers")

    lines = [t(language, "what_to_repeat")]
    seen: set[str] = set()
    item_number = 1
    for question in wrong_questions:
        for source in question.get("source_refs", []):
            book = _localized(source["book"], language)
            pages = _format_pages(source.get("page_start"), source.get("page_end"))
            section = _localized(source["section"], language)
            key = f"{book}|{pages}|{section}"
            if key in seen:
                continue
            lines.extend(
                [
                    f"{item_number}. {book} - {_format_source_pages(pages, language)}",
                    f"   {t(language, 'source_topic')}: {section}",
                ]
            )
            seen.add(key)
            item_number += 1

    if item_number == 1:
        lines.append(t(language, "no_sources"))

    return "\n".join(lines)


def _format_pages(page_start: int | None, page_end: int | None) -> str:
    if page_start and page_end and page_start != page_end:
        return f"{page_start}-{page_end}"
    if page_start:
        return str(page_start)
    return "-"


def _localized(value: dict[str, Any], language_code: str) -> Any:
    language = normalize_language(language_code)
    return value.get(language) or value.get(DEFAULT_LANGUAGE)


def get_wrong_explanation(question: dict[str, Any], selected_index: int, language_code: str) -> str:
    language = normalize_language(language_code)
    return question.get("wrong_explanations", {}).get(language, {}).get(
        str(selected_index),
        _localized(question["explanation_correct"], language),
    )


def _format_first_source(question: dict[str, Any], language_code: str) -> str | None:
    source_refs = question.get("source_refs", [])
    if not source_refs:
        return None
    source = source_refs[0]
    book = _localized(source["book"], language_code)
    pages = _format_pages(source.get("page_start"), source.get("page_end"))
    return f"{book}, {_format_source_pages(pages, language_code)}."


def _format_source_pages(pages: str, language_code: str) -> str:
    language = normalize_language(language_code)
    return t(language, "source_pages", pages=pages)


def _format_number(value: float | int) -> str:
    return f"{float(value):.1f}"


def _format_signed(value: float | int) -> str:
    return f"{float(value):+.1f}"


def _trend_key(trend: str) -> str:
    return {
        TREND_IMPROVEMENT: "trend_improvement",
        TREND_DECLINE: "trend_decline",
        TREND_STABLE: "trend_stable",
        TREND_NOT_ENOUGH_DATA: "trend_not_enough_data",
    }.get(trend, "trend_stable")
