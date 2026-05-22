from pathlib import Path

from bot.services.materials_service import (
    collect_unique_sources,
    format_source_text,
    get_local_material_path,
    get_materials_to_send,
    source_file_exists,
)


def _source(**overrides):
    source = {
        "book": {"uz": "Jahon tarixi", "ru": "Всемирная история"},
        "page_start": 142,
        "page_end": 145,
        "section": {"uz": "Konferensiyalar", "ru": "Конференции"},
        "local_excerpt_path": "materials/ru/history/world_history_10_142_145.pdf",
        "distribution": "send_excerpt",
    }
    source.update(overrides)
    return source


def test_collect_unique_sources_removes_duplicates():
    questions = [{"source_refs": [_source(), _source()]}]

    assert len(collect_unique_sources(questions, "ru")) == 1


def test_missing_local_file_falls_back_safely():
    materials = get_materials_to_send([{"source_refs": [_source()]}], "ru")

    assert materials[0]["path"] is None
    assert "Файл пока не найден локально" in materials[0]["fallback_text"]
    assert source_file_exists(_source()) is False


def test_local_path_traversal_is_rejected():
    source = _source(local_excerpt_path="../secret.pdf")

    assert get_local_material_path(source) is None


def test_format_source_text_works_in_ru_and_uz():
    assert "стр. 142-145" in format_source_text(_source(distribution="text_only"), "ru")
    assert "142-145-betlar" in format_source_text(_source(distribution="text_only"), "uz")


def test_valid_material_path_stays_inside_materials():
    path = get_local_material_path(_source())

    assert isinstance(path, Path)
    assert "materials" in path.parts
