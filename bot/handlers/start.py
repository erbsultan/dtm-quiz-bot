from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import HELP_TEXT, main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def command_start(message: Message) -> None:
    await message.answer(
        "Welcome to dtm-quiz-bot!\n\n"
        "This Stage 1 version gives you a short DTM-style practice quiz, explanations, and basic statistics.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(lambda message: message.text == HELP_TEXT)
async def help_message(message: Message) -> None:
    await message.answer(
        "Choose Start quiz to answer 5 sample questions.\n"
        "After each answer you will see the correct option and an explanation.\n"
        "Choose My statistics to see your saved results.",
        reply_markup=main_menu_keyboard(),
    )
