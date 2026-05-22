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
    resume_session_keyboard,
    start_new_session_keyboard,
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
from bot.services.session_service import (
    cancel_session,
    complete_session,
    create_session,
    filter_questions_by_ids,
    get_active_session,
    has_missing_questions,
    pause_session,
    restore_answers_for_questions,
    resume_session,
    save_answer,
)
from bot.utils.text import safe_join_sections, split_long_message

router = Router()


class QuizState(StatesGroup):
    answering = State()


@router.message(F.text.in_(START_QUIZ_TEXTS))
async def show_quiz_sources(message: Message, state: FSMContext) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)
        user = await get_or_create_user(session, message.from_user)
        active_session = await get_active_session(session, user.id)

    if active_session:
        await state.clear()
        await message.answer(_format_resume_prompt(active_session, language_code), reply_markup=resume_session_keyboard(language_code))
        return

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
        active_session = await get_active_session(session, user.id)
        if active_session:
            await state.clear()
            await message.answer(
                _format_resume_prompt(active_session, language_code),
                reply_markup=resume_session_keyboard(language_code),
            )
            return
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

    await callback.message.edit_reply_markup(reply_markup=None)

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
        t(language_code, "materials_shown"),
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
    data = await state.get_data()
    if not data.get("session_id"):
        questions: list[dict[str, Any]] = data["questions"]
        language_code = data.get("language_code", "uz")
        mode = data.get("mode", "sample")
        async with async_session_factory() as session:
            user = await get_or_create_user(session, callback.from_user)
            profile_code = await get_user_exam_profile_code(session, callback.from_user)
            quiz_session = await create_session(
                session=session,
                user_id=user.id,
                mode=mode,
                language_code=language_code,
                exam_profile_code=profile_code,
                question_ids=[str(question["id"]) for question in questions],
            )
        await state.update_data(session_id=quiz_session.id)

    await state.set_state(QuizState.answering)
    await callback.message.edit_reply_markup(reply_markup=None)
    await _send_current_question(callback, state)


@router.callback_query(F.data == "quiz:resume")
async def continue_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    async with async_session_factory() as session:
        user = await get_or_create_user(session, callback.from_user)
        active_session = await get_active_session(session, user.id)
        if active_session is None:
            language_code = user.language_code
            await callback.message.answer(
                t(language_code, "unfinished_session_not_found"),
                reply_markup=start_new_session_keyboard(language_code),
            )
            await callback.answer()
            return
        active_session = await resume_session(session, active_session.id)

    try:
        all_questions = load_questions(settings.questions_file)
    except QuestionLoaderError as exc:
        await callback.message.answer(t(active_session.language_code, "quiz_load_error", error=exc))
        await callback.answer()
        return

    question_ids = [str(question_id) for question_id in active_session.question_ids]
    if has_missing_questions(all_questions, question_ids):
        await callback.message.answer(
            t(active_session.language_code, "session_questions_missing"),
            reply_markup=start_new_session_keyboard(active_session.language_code),
        )
        await callback.answer()
        return

    questions = filter_questions_by_ids(all_questions, question_ids)
    answers = restore_answers_for_questions(question_ids, active_session.answers or [])
    await state.clear()
    await state.update_data(
        questions=questions,
        current_index=active_session.current_question_index,
        answers=answers,
        started_at=active_session.started_at.isoformat(),
        language_code=active_session.language_code,
        mode=active_session.mode,
        session_id=active_session.id,
    )
    await state.set_state(QuizState.answering)
    if active_session.current_question_index >= len(questions):
        await _finish_quiz(callback, state)
        return
    await _send_current_question(callback, state)


@router.callback_query(F.data == "quiz:start_new")
async def start_new_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    async with async_session_factory() as session:
        language_code = await get_user_language(session, callback.from_user)
        user = await get_or_create_user(session, callback.from_user)
        active_session = await get_active_session(session, user.id)
        if active_session:
            await cancel_session(session, active_session.id)

    await state.clear()
    await callback.message.answer(t(language_code, "discarded_session"))
    await _start_preparation(callback.message, state, language_code, mode="sample")
    await callback.answer()


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
    session_id = data.get("session_id")
    if session_id:
        async with async_session_factory() as session:
            await save_answer(
                session,
                session_id,
                {
                    "question_id": str(question["id"]),
                    "selected_index": selected_index,
                    "correct_index": question["correct_index"],
                    "is_correct": is_correct,
                },
            )

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        format_answer_feedback(question, selected_index, data.get("language_code")),
        reply_markup=next_question_keyboard(data.get("language_code")),
    )
    await callback.answer()


@router.callback_query(QuizState.answering, F.data == "quiz:pause")
async def pause_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = data.get("session_id")
    language_code = data.get("language_code", "uz")
    if session_id:
        async with async_session_factory() as session:
            await pause_session(session, session_id)

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t(language_code, "quiz_paused"), reply_markup=main_menu_keyboard(language_code))
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
        reply_markup=options_keyboard(question["options"][language_code], language_code),
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
        session_id = data.get("session_id")
        if session_id:
            await complete_session(session, session_id)

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


async def _start_preparation(message: Message, state: FSMContext, language_code: str, mode: str) -> None:
    try:
        questions = load_questions(settings.questions_file)[:5]
    except QuestionLoaderError as exc:
        await message.answer(t(language_code, "quiz_load_error", error=exc))
        return

    await _prepare_quiz_state(state, questions, language_code, mode=mode)
    await _send_split_message(
        message,
        build_sources_message(questions, language_code),
        reply_markup=preparation_keyboard(language_code),
    )


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


def _format_resume_prompt(quiz_session: Any, language_code: str) -> str:
    return t(
        language_code,
        "resume_prompt",
        answered=len(quiz_session.answers or []),
        total=len(quiz_session.question_ids or []),
        mode=t(language_code, _mode_key(quiz_session.mode)),
    )


def _mode_key(mode: str) -> str:
    if mode == "mistake_review":
        return "mode_mistake_review"
    return "mode_sample"


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
