SUPPORTED_LANGUAGES = {"uz", "ru"}
DEFAULT_LANGUAGE = "uz"


MESSAGES = {
    "uz": {
        "choose_language": "Tilni tanlang:",
        "language_saved": "Til saqlandi.",
        "welcome": (
            "dtm-quiz-bot ga xush kelibsiz!\n\n"
            "Bu bot DTM uslubidagi testlar orqali tayyorgarlik ko'rishga yordam beradi."
        ),
        "start_quiz": "Testni boshlash",
        "my_statistics": "Statistikam",
        "help": "Yordam",
        "settings": "Sozlamalar",
        "menu_placeholder": "Amalni tanlang",
        "help_text": (
            "Testni boshlash tugmasi orqali 5 ta namunaviy savolga javob bering.\n"
            "Har bir javobdan keyin izoh ko'rsatiladi.\n"
            "Statistikam bo'limida natijalaringizni ko'rishingiz mumkin."
        ),
        "start_now": "Boshlash",
        "next_question": "Keyingi savol",
        "question_header": "Savol {number}/{total}",
        "subject": "Fan",
        "topic": "Mavzu",
        "correct": "To'g'ri!",
        "incorrect": "Noto'g'ri. Siz {selected} javobini tanladingiz.",
        "already_answered": "Bu savolga javob berilgan.",
        "correct_answer": "To'g'ri javob",
        "explanation": "Izoh",
        "sources_title": "📚 Testdan oldin o'qish tavsiya qilinadi:",
        "pages": "Betlar",
        "section": "Mavzu",
        "no_sources": "Manbalar ko'rsatilmagan.",
        "result_title": "📊 Natijangiz:",
        "correct_answers": "To'g'ri javoblar",
        "percentage": "Aniqlik",
        "mini_test_score": "Bu testdagi DTM ball",
        "projected_full_score": "To'liq DTM uchun taxminiy natija",
        "by_subject": "Fanlar bo'yicha:",
        "points": "ball",
        "interpret_high": "Ajoyib natija. Endi xatolar izohlarini qayta ko'rib chiqing.",
        "interpret_mid": "Yaxshi boshlanish. Zaif mavzularni qayta o'qing va yana urinib ko'ring.",
        "interpret_low": "Bu boshlang'ich natija. Manbalarni o'qib, testni qayta ishlang.",
        "stats_empty": "Hali test natijalaringiz yo'q. Avval testni boshlang.",
        "stats_title": "Statistikam",
        "total_attempts": "Urinishlar soni",
        "average_accuracy": "O'rtacha aniqlik",
        "average_score": "O'rtacha mini-test ball",
        "best_score": "Eng yaxshi mini-test ball",
        "latest_score": "Oxirgi mini-test ball",
        "projected_average_full_score": "To'liq DTM uchun o'rtacha taxmin",
        "quiz_load_error": "Testni boshlashda xatolik: {error}",
    },
    "ru": {
        "choose_language": "Выберите язык:",
        "language_saved": "Язык сохранён.",
        "welcome": (
            "Добро пожаловать в dtm-quiz-bot!\n\n"
            "Бот помогает готовиться к тестам в формате ДТМ."
        ),
        "start_quiz": "Начать тест",
        "my_statistics": "Моя статистика",
        "help": "Помощь",
        "settings": "Настройки",
        "menu_placeholder": "Выберите действие",
        "help_text": (
            "Нажмите Начать тест, чтобы ответить на 5 пробных вопросов.\n"
            "После каждого ответа бот покажет объяснение.\n"
            "В разделе Моя статистика доступны ваши результаты."
        ),
        "start_now": "Начать",
        "next_question": "Следующий вопрос",
        "question_header": "Вопрос {number}/{total}",
        "subject": "Предмет",
        "topic": "Тема",
        "correct": "Верно!",
        "incorrect": "Неверно. Вы выбрали {selected}.",
        "already_answered": "На этот вопрос уже дан ответ.",
        "correct_answer": "Правильный ответ",
        "explanation": "Объяснение",
        "sources_title": "📚 Перед тестом желательно прочитать:",
        "pages": "Страницы",
        "section": "Тема",
        "no_sources": "Источники не указаны.",
        "result_title": "📊 Ваш результат:",
        "correct_answers": "Правильные ответы",
        "percentage": "Точность",
        "mini_test_score": "DTM-балл в этом тесте",
        "projected_full_score": "Прогноз на полный DTM",
        "by_subject": "По предметам:",
        "points": "балла",
        "interpret_high": "Отличный результат. Теперь разберите объяснения к ошибкам.",
        "interpret_mid": "Хорошее начало. Повторите слабые темы и попробуйте снова.",
        "interpret_low": "Это стартовый результат. Прочитайте источники и повторите тест.",
        "stats_empty": "У вас пока нет попыток. Сначала начните тест.",
        "stats_title": "Моя статистика",
        "total_attempts": "Всего попыток",
        "average_accuracy": "Средняя точность",
        "average_score": "Средний балл мини-теста",
        "best_score": "Лучший балл мини-теста",
        "latest_score": "Последний балл мини-теста",
        "projected_average_full_score": "Средний прогноз на полный DTM",
        "quiz_load_error": "Не удалось начать тест: {error}",
    },
}

SUBJECT_NAMES = {
    "uz": {
        "ona_tili": "Ona tili",
        "matematika": "Matematika",
        "ozbekiston_tarixi": "O'zbekiston tarixi",
        "tarix": "Tarix",
        "chet_tili": "Chet tili",
    },
    "ru": {
        "ona_tili": "Родной язык",
        "matematika": "Математика",
        "ozbekiston_tarixi": "История Узбекистана",
        "tarix": "История",
        "chet_tili": "Иностранный язык",
    },
}


def normalize_language(language_code: str | None) -> str:
    if language_code in SUPPORTED_LANGUAGES:
        return language_code
    return DEFAULT_LANGUAGE


def t(language_code: str | None, key: str, **kwargs: object) -> str:
    language = normalize_language(language_code)
    template = MESSAGES[language].get(key, MESSAGES[DEFAULT_LANGUAGE][key])
    return template.format(**kwargs)


def subject_name(language_code: str | None, subject: str) -> str:
    language = normalize_language(language_code)
    return SUBJECT_NAMES.get(language, {}).get(subject, subject)
