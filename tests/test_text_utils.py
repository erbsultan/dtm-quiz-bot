from bot.utils.text import safe_join_sections, split_long_message


def test_split_long_message_respects_limit():
    text = "alpha\n\n" + ("x" * 20) + "\n\nomega"

    chunks = split_long_message(text, limit=15)

    assert all(len(chunk) <= 15 for chunk in chunks)
    assert chunks[0] == "alpha"


def test_safe_join_sections_keeps_sections_under_limit():
    sections = ["first", "second", "x" * 20]

    messages = safe_join_sections(sections, limit=15)

    assert all(len(message) <= 15 for message in messages)
    assert messages[0] == "first\n\nsecond"
