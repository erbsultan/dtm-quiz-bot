from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user.id not in settings.admin_ids:
        await message.answer("This command is only available to admins.")
        return

    await message.answer("Admin panel placeholder for future stages.")
