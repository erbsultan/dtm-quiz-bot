from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.db.database import async_session_factory
from bot.keyboards import HELP_TEXTS, SETTINGS_TEXTS, language_keyboard, main_menu_keyboard
from bot.locales import t
from bot.services.quiz_service import get_user_language, set_user_language

router = Router()


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)

    await message.answer(
        t(language_code, "welcome"),
        reply_markup=main_menu_keyboard(language_code),
    )
    await message.answer(t(language_code, "choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def choose_language(callback: CallbackQuery) -> None:
    language_code = callback.data.split(":", maxsplit=1)[1]
    async with async_session_factory() as session:
        user = await set_user_language(session, callback.from_user, language_code)

    await callback.message.answer(t(user.language_code, "language_saved"), reply_markup=main_menu_keyboard(user.language_code))
    await callback.answer()


@router.message(F.text.in_(SETTINGS_TEXTS))
async def settings_message(message: Message) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)

    await message.answer(t(language_code, "choose_language"), reply_markup=language_keyboard())


@router.message(F.text.in_(HELP_TEXTS))
async def help_message(message: Message) -> None:
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)

    await message.answer(t(language_code, "help_text"), reply_markup=main_menu_keyboard(language_code))
