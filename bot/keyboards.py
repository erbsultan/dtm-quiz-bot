from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.locales import t

START_QUIZ_TEXTS = {t("uz", "start_quiz"), t("ru", "start_quiz"), "Start quiz"}
STATS_TEXTS = {t("uz", "my_statistics"), t("ru", "my_statistics"), "My statistics"}
HELP_TEXTS = {t("uz", "help"), t("ru", "help"), "Help"}
SETTINGS_TEXTS = {t("uz", "settings"), t("ru", "settings")}
REPEAT_MISTAKES_TEXTS = {t("uz", "repeat_mistakes"), t("ru", "repeat_mistakes")}


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            ]
        ]
    )


def main_menu_keyboard(language_code: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(language_code, "start_quiz"))],
            [KeyboardButton(text=t(language_code, "repeat_mistakes"))],
            [KeyboardButton(text=t(language_code, "my_statistics")), KeyboardButton(text=t(language_code, "help"))],
            [KeyboardButton(text=t(language_code, "settings"))],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(language_code, "menu_placeholder"),
    )


def options_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{chr(65 + index)}. {option}", callback_data=f"answer:{index}")]
        for index, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def next_question_keyboard(language_code: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(language_code, "next_question"), callback_data="quiz:next")]]
    )


def start_quiz_keyboard(language_code: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(language_code, "start_now"), callback_data="quiz:begin")]]
    )


def preparation_keyboard(language_code: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language_code, "open_materials"), callback_data="quiz:materials")],
            [InlineKeyboardButton(text=t(language_code, "start_test"), callback_data="quiz:begin")],
        ]
    )


def materials_after_open_keyboard(language_code: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language_code, "start_test"), callback_data="quiz:begin")],
            [InlineKeyboardButton(text=t(language_code, "back_to_menu"), callback_data="quiz:menu")],
        ]
    )
