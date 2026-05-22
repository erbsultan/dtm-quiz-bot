from bot.locales import t


def test_t_falls_back_to_default_language():
    assert t("unknown", "source_pages", pages="142-145") == "142-145-betlar"


def test_t_falls_back_to_key_name_when_missing():
    assert t("ru", "missing_key") == "missing_key"


def test_source_pages_localization():
    assert t("ru", "source_pages", pages="142-145") == "стр. 142-145"
    assert t("uz", "source_pages", pages="142-145") == "142-145-betlar"
