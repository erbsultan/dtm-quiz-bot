from aiogram import F, Router
from aiogram.types import Message

from bot.db.database import async_session_factory
from bot.keyboards import STATS_TEXT, main_menu_keyboard
from bot.services.stats_service import format_statistics, get_user_statistics

router = Router()


@router.message(F.text == STATS_TEXT)
async def my_statistics(message: Message) -> None:
    async with async_session_factory() as session:
        stats = await get_user_statistics(session, message.from_user.id)

    await message.answer(format_statistics(stats), reply_markup=main_menu_keyboard())
