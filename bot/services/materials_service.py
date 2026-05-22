from pathlib import Path
from typing import Any

from bot.locales import DEFAULT_LANGUAGE, normalize_language, t

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_ROOT = PROJECT_ROOT / "materials"


def collect_unique_sources(questions: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    normalize_language(language)
    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()

    for question in questions:
        for source in question.get("source_refs", []):
            key = (
                _localized(source.get("book", {}), language),
                str(source.get("page_start") or ""),
                str(source.get("page_end") or ""),
                _localized(source.get("section", {}), language),
                source.get("public_url") or "",
                source.get("local_excerpt_path") or "",
            )
            if key in seen:
                continue
            sources.append(source)
            seen.add(key)

    return sources


def format_source_text(source: dict[str, Any], language: str) -> str:
    language_code = normalize_language(language)
    book = _localized(source.get("book", {}), language_code)
    pages = _format_pages(source.get("page_start"), source.get("page_end"))
    section = _localized(source.get("section", {}), language_code)
    distribution = source.get("distribution", "text_only")
    public_url = source.get("public_url")

    if distribution == "link_only" and public_url:
        return t(language_code, "materials_link", book=book, pages=pages, section=section, url=public_url)

    return t(language_code, "materials_text_only", book=book, pages=pages, section=section)


def format_missing_file_text(source: dict[str, Any], language: str) -> str:
    language_code = normalize_language(language)
    book = _localized(source.get("book", {}), language_code)
    pages = _format_pages(source.get("page_start"), source.get("page_end"))
    section = _localized(source.get("section", {}), language_code)
    return t(language_code, "materials_missing_file", book=book, pages=pages, section=section)


def get_local_material_path(source: dict[str, Any]) -> Path | None:
    raw_path = source.get("local_excerpt_path")
    if not raw_path or ".." in Path(raw_path).parts:
        return None

    path = Path(raw_path)
    candidate = path if path.is_absolute() else PROJECT_ROOT / path
    resolved = candidate.resolve()

    if not _is_relative_to(resolved, PROJECT_ROOT):
        return None
    if not _is_relative_to(resolved, MATERIALS_ROOT):
        return None
    return resolved


def source_file_exists(source: dict[str, Any]) -> bool:
    path = get_local_material_path(source)
    return bool(path and path.is_file())


def get_materials_to_send(questions: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    materials = []
    for source in collect_unique_sources(questions, language):
        distribution = source.get("distribution", "text_only")
        path = get_local_material_path(source) if distribution == "send_excerpt" else None
        materials.append(
            {
                "source": source,
                "distribution": distribution,
                "path": path if path and path.is_file() else None,
                "text": format_source_text(source, language),
                "fallback_text": format_missing_file_text(source, language),
            }
        )
    return materials


def _localized(value: dict[str, Any], language: str) -> str:
    language_code = normalize_language(language)
    if not isinstance(value, dict):
        return str(value or "")
    return value.get(language_code) or value.get(DEFAULT_LANGUAGE) or ""


def _format_pages(page_start: int | None, page_end: int | None) -> str:
    if page_start and page_end and page_start != page_end:
        return f"{page_start}-{page_end}"
    if page_start:
        return str(page_start)
    return "-"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
