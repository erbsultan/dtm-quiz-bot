from bot.services.quiz_service import format_repeat_sources, get_wrong_explanation


def _question():
    return {
        "id": 101,
        "question": {"uz": "Savol?", "ru": "Вопрос?"},
        "options": {"uz": ["A", "B"], "ru": ["А", "Б"]},
        "correct_index": 1,
        "explanation_correct": {"uz": "To'g'ri izoh.", "ru": "Правильное объяснение."},
        "wrong_explanations": {
            "uz": {"0": "Bu javob noto'g'ri."},
            "ru": {"0": "Этот ответ неверный."},
        },
        "source_refs": [
            {
                "book": {"uz": "Jahon tarixi", "ru": "Всемирная история"},
                "page_start": 142,
                "page_end": 145,
                "section": {"uz": "Konferensiyalar", "ru": "Конференции"},
            }
        ],
    }


def test_get_wrong_explanation_uses_selected_wrong_index():
    assert get_wrong_explanation(_question(), 0, "ru") == "Этот ответ неверный."


def test_get_wrong_explanation_falls_back_to_correct_explanation():
    assert get_wrong_explanation(_question(), 1, "ru") == "Правильное объяснение."


def test_format_repeat_sources_deduplicates_sources():
    question = _question()
    text = format_repeat_sources(
        [question, question],
        [
            {"question_index": 0, "is_correct": False},
            {"question_index": 1, "is_correct": False},
        ],
        "ru",
    )

    assert text.count("Всемирная история") == 1
    assert "стр. 142-145" in text
