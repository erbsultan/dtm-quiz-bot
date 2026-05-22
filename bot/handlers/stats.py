from aiogram import F, Router
from aiogram.types import Message

from bot.config import settings
from bot.db.database import async_session_factory
from bot.keyboards import STATS_TEXTS, main_menu_keyboard
from bot.services.quiz_service import get_user_language
from bot.services.scoring_service import get_exam_profile
from bot.services.stats_service import format_statistics, get_user_statistics

router = Router()


@router.message(F.text.in_(STATS_TEXTS))
async def my_statistics(message: Message) -> None:
    profile = get_exam_profile(settings.exam_profiles_file)
    async with async_session_factory() as session:
        language_code = await get_user_language(session, message.from_user)
        stats = await get_user_statistics(session, message.from_user.id, profile)

    await message.answer(format_statistics(stats, language_code), reply_markup=main_menu_keyboard(language_code))
