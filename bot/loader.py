import json
from pathlib import Path
from typing import Any


REQUIRED_QUESTION_FIELDS = {
    "id",
    "subject",
    "subject_group",
    "topic",
    "subtopic",
    "question",
    "options",
    "correct_index",
    "explanation_correct",
    "wrong_explanations",
    "difficulty",
    "source_refs",
}
SUPPORTED_LANGUAGE_FIELDS = {"uz", "ru"}


class QuestionLoaderError(ValueError):
    pass


def load_questions(file_path: str | Path) -> list[dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        raise QuestionLoaderError(f"Questions file not found: {path}")

    try:
        raw_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QuestionLoaderError(f"Invalid JSON in questions file: {exc}") from exc

    if not isinstance(raw_data, list) or not raw_data:
        raise QuestionLoaderError("Questions file must contain a non-empty list of questions.")

    for index, question in enumerate(raw_data, start=1):
        _validate_question(question, index)

    return raw_data


def _validate_question(question: Any, index: int) -> None:
    if not isinstance(question, dict):
        raise QuestionLoaderError(f"Question #{index} must be an object.")

    missing = REQUIRED_QUESTION_FIELDS - question.keys()
    if missing:
        fields = ", ".join(sorted(missing))
        raise QuestionLoaderError(f"Question #{index} is missing required fields: {fields}")

    options = question["options"]
    _validate_localized_text(question["question"], index, "question")
    _validate_localized_text(question["explanation_correct"], index, "explanation_correct")

    if not isinstance(options, dict):
        raise QuestionLoaderError(
            f"Question #{index} options must be an object with uz and ru lists. "
            "Old flat option lists are not supported in Stage 2."
        )
    for language in SUPPORTED_LANGUAGE_FIELDS:
        language_options = options.get(language)
        if not isinstance(language_options, list) or len(language_options) < 2:
            raise QuestionLoaderError(f"Question #{index} options.{language} must have at least two options.")

    option_count = len(options["uz"])
    if len(options["ru"]) != option_count:
        raise QuestionLoaderError(f"Question #{index} options.uz and options.ru must have the same length.")

    correct_index = question["correct_index"]
    if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= option_count:
        raise QuestionLoaderError(f"Question #{index} has an invalid correct_index.")

    wrong_explanations = question["wrong_explanations"]
    if not isinstance(wrong_explanations, dict):
        raise QuestionLoaderError(f"Question #{index} wrong_explanations must be an object.")
    for language in SUPPORTED_LANGUAGE_FIELDS:
        if not isinstance(wrong_explanations.get(language), dict):
            raise QuestionLoaderError(f"Question #{index} wrong_explanations.{language} must be an object.")

    source_refs = question["source_refs"]
    if not isinstance(source_refs, list):
        raise QuestionLoaderError(f"Question #{index} source_refs must be a list.")
    for source_index, source in enumerate(source_refs, start=1):
        _validate_source_ref(source, index, source_index)


def _validate_localized_text(value: Any, index: int, field_name: str) -> None:
    if not isinstance(value, dict):
        raise QuestionLoaderError(
            f"Question #{index} {field_name} must be an object with uz and ru text. "
            "Old flat text values are not supported in Stage 2."
        )
    for language in SUPPORTED_LANGUAGE_FIELDS:
        if not isinstance(value.get(language), str) or not value[language].strip():
            raise QuestionLoaderError(f"Question #{index} {field_name}.{language} must be non-empty text.")


def _validate_source_ref(source: Any, question_index: int, source_index: int) -> None:
    if not isinstance(source, dict):
        raise QuestionLoaderError(f"Question #{question_index} source #{source_index} must be an object.")
    _validate_localized_text(source.get("book"), question_index, f"source_refs[{source_index}].book")
    _validate_localized_text(source.get("section"), question_index, f"source_refs[{source_index}].section")
