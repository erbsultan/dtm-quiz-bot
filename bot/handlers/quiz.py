from datetime import UTC, datetime
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.db.database import async_session_factory
from bot.keyboards import START_QUIZ_TEXT, next_question_keyboard, options_keyboard, start_quiz_keyboard
from bot.loader import QuestionLoaderError, load_questions
from bot.services.quiz_service import (
    build_sources_message,
    format_answer_feedback,
    format_question,
    format_result,
    save_quiz_attempt,
)

router = Router()


class QuizState(StatesGroup):
    answering = State()


@router.message(F.text == START_QUIZ_TEXT)
async def show_quiz_sources(message: Message, state: FSMContext) -> None:
    try:
        questions = load_questions(settings.questions_file)[:5]
    except QuestionLoaderError as exc:
        await message.answer(f"Could not start quiz: {exc}")
        return

    await state.clear()
    await state.update_data(
        questions=questions,
        current_index=0,
        answers=[],
        started_at=datetime.now(UTC).isoformat(),
    )
    await message.answer(build_sources_message(questions), reply_markup=start_quiz_keyboard())


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
        await callback.answer("This question has already been answered.")
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
    await callback.message.answer(format_answer_feedback(question, selected_index), reply_markup=next_question_keyboard())
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

    await callback.message.answer(
        format_question(question, current_index + 1, len(questions)),
        reply_markup=options_keyboard(question["options"]),
    )
    await callback.answer()


async def _finish_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions: list[dict[str, Any]] = data["questions"]
    answers: list[dict[str, Any]] = data["answers"]
    correct_count = sum(1 for answer in answers if answer["is_correct"])

    async with async_session_factory() as session:
        await save_quiz_attempt(
            session=session,
            telegram_user=callback.from_user,
            questions=questions,
            answers=answers,
            started_at_iso=data["started_at"],
        )

    await callback.message.answer(format_result(correct_count, len(questions)))
    await state.clear()
    await callback.answer()
