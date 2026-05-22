from datetime import UTC, datetime
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.db.database import async_session_factory
from bot.keyboards import (
    materials_after_open_keyboard,
    main_menu_keyboard,
    preparation_keyboard,
    REPEAT_MISTAKES_TEXTS,
    START_QUIZ_TEXTS,
    next_question_keyboard,
    options_keyboard,
)
from bot.loader import QuestionLoaderError, load_questions
from bot.locales import t
from bot.services.quiz_service import (
    build_sources_message,
    format_attempt_comparison,
    format_answer_feedback,
    format_mistakes_review,
    format_question,
    format_repeat_sources,
    format_result,
    get_or_create_user,
    get_user_exam_profile_code,
    get_user_language,
    save_quiz_attempt,
)
from bot.services.materials_service import get_materials_to_send
from bot.services.progress_service import get_attempt_comparison, get_mistake_question_ids
from bot.services.scoring_service import calculate_score, get_exam_profile
from bot.utils.text import safe_join_sections, split_long_message

router = Router()


class QuizState(StatesGroup):
    answering = State()


@router.message(F.text.in_(START_QUIZ_TEXTS))
async def show_quiz_sources(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)

    try:
        questions = load_questions(settings.questions_file)[:5]
    except QuestionLoaderError as exc:
        await message.answer(t(language_code, "quiz_load_error", error=exc))
        return

    await _prepare_quiz_state(state, questions, language_code, mode="sample")
    await _send_split_message(
        message,
        build_sources_message(questions, language_code),
        reply_markup=preparation_keyboard(language_code),
    )


@router.message(F.text.in_(REPEAT_MISTAKES_TEXTS))
async def repeat_mistakes(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)
        user = await get_or_create_user(session, message.from_user)
        mistake_ids = await get_mistake_question_ids(session, user.id, limit=10)

    if not mistake_ids:
        await message.answer(t(language_code, "no_mistakes"))
        return

    try:
        all_questions = load_questions(settings.questions_file)
    except QuestionLoaderError as exc:
        await message.answer(t(language_code, "quiz_load_error", error=exc))
        return

    question_by_id = {str(question["id"]): question for question in all_questions}
    questions = [question_by_id[question_id] for question_id in mistake_ids if question_id in question_by_id]
    if not questions:
        await message.answer(t(language_code, "no_mistakes"))
        return

    await _prepare_quiz_state(state, questions, language_code, mode="mistake_review")
    await message.answer(t(language_code, "mistake_review_sources"))
    await _send_split_message(
        message,
        build_sources_message(questions, language_code),
        reply_markup=preparation_keyboard(language_code),
    )


@router.callback_query(F.data == "quiz:materials")
async def open_materials(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list[dict[str, Any]] = data.get("questions", [])
    language_code = data.get("language_code", "uz")

    for material in get_materials_to_send(questions, language_code):
        if material["distribution"] == "send_excerpt" and material["path"]:
            await callback.message.answer_document(
                FSInputFile(material["path"]),
                caption=material["text"],
            )
            continue

        text = material["fallback_text"] if material["distribution"] == "send_excerpt" else material["text"]
        await _send_split_callback_message(callback, text)

    await callback.message.answer(
        t(language_code, "start_test"),
        reply_markup=materials_after_open_keyboard(language_code),
    )
    await callback.answer()


@router.callback_query(F.data == "quiz:menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    language_code = data.get("language_code", "uz")
    await state.clear()
    await callback.message.answer(t(language_code, "welcome"), reply_markup=main_menu_keyboard(language_code))
    await callback.answer()


@router.callback_query(F.data == "quiz:begin")
async def begin_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(QuizState.answering)
    await _send_current_question(callback, state)


@router.callback_query(QuizState.answering, F.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list[dict[str, Any]] = data["questions"]
    current_index: int = data["current_index"]
    question = questions[current_index]
    selected_index = int(callback.data.split(":", maxsplit=1)[1])
    is_correct = selected_index == question["correct_index"]

    answers = data.get("answers", [])
    if any(answer["question_index"] == current_index for answer in answers):
        await callback.answer(t(data.get("language_code"), "already_answered"))
        return

    answers.append(
        {
            "question_index": current_index,
            "selected_index": selected_index,
            "is_correct": is_correct,
        }
    )
    await state.update_data(answers=answers)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        format_answer_feedback(question, selected_index, data.get("language_code")),
        reply_markup=next_question_keyboard(data.get("language_code")),
    )
    await callback.answer()


@router.callback_query(QuizState.answering, F.data == "quiz:next")
async def next_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    next_index = data["current_index"] + 1
    await state.update_data(current_index=next_index)

    if next_index >= len(data["questions"]):
        await _finish_quiz(callback, state)
        return

    await _send_current_question(callback, state)


async def _send_current_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list[dict[str, Any]] = data["questions"]
    current_index: int = data["current_index"]
    question = questions[current_index]
    language_code = data.get("language_code", "uz")

    await callback.message.answer(
        format_question(question, current_index + 1, len(questions), language_code),
        reply_markup=options_keyboard(question["options"][language_code]),
    )
    await callback.answer()


async def _finish_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list[dict[str, Any]] = data["questions"]
    answers: list[dict[str, Any]] = data["answers"]
    language_code = data.get("language_code", "uz")
    mode = data.get("mode", "sample")
    correct_count = sum(1 for answer in answers if answer["is_correct"])

    async with async_session_factory() as session:
        profile_code = await get_user_exam_profile_code(session, callback.from_user)

    profile = get_exam_profile(settings.exam_profiles_file, profile_code)
    scoring_result = calculate_score(questions, answers, profile)

    async with async_session_factory() as session:
        attempt = await save_quiz_attempt(
            session=session,
            telegram_user=callback.from_user,
            questions=questions,
            answers=answers,
            started_at_iso=data["started_at"],
            scoring_result=scoring_result,
            mode=mode,
        )
        comparison = await get_attempt_comparison(session, attempt.user_id, attempt.id)

    sections = [
        format_result(correct_count, len(questions), scoring_result, language_code),
        format_attempt_comparison(comparison, language_code),
    ]
    mistakes_review = format_mistakes_review(questions, answers, language_code)
    if mistakes_review:
        sections.append(mistakes_review)
    sections.append(format_repeat_sources(questions, answers, language_code))

    for text in safe_join_sections(sections):
        await callback.message.answer(text)
    await state.clear()
    await callback.answer()


async def _prepare_quiz_state(
    state: FSMContext,
    questions: list[dict[str, Any]],
    language_code: str,
    mode: str,
) -> None:
    await state.clear()
    await state.update_data(
        questions=questions,
        current_index=0,
        answers=[],
        started_at=datetime.now(UTC).isoformat(),
        language_code=language_code,
        mode=mode,
    )


async def _send_split_message(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chunks = split_long_message(text)
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)


async def _send_split_callback_message(callback: CallbackQuery, text: str) -> None:
    for chunk in split_long_message(text):
        await callback.message.answer(chunk)
