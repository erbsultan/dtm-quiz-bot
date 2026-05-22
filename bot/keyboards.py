from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


START_QUIZ_TEXT = "Start quiz"
STATS_TEXT = "My statistics"
HELP_TEXT = "Help"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=START_QUIZ_TEXT)],
            [KeyboardButton(text=STATS_TEXT), KeyboardButton(text=HELP_TEXT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an action",
    )


def options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{chr(65 + index)}. {option}", callback_data=f"answer:{index}")]
        for index, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def next_question_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Next question", callback_data="quiz:next")]]
    )


def start_quiz_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Start now", callback_data="quiz:begin")]]
    )
