import json
from pathlib import Path
from typing import Any


REQUIRED_QUESTION_FIELDS = {
    "id",
    "subject",
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
    if not isinstance(options, list) or len(options) < 2:
        raise QuestionLoaderError(f"Question #{index} must have at least two options.")

    correct_index = question["correct_index"]
    if not isinstance(correct_index, int) or correct_index < 0 or correct_index >= len(options):
        raise QuestionLoaderError(f"Question #{index} has an invalid correct_index.")

    wrong_explanations = question["wrong_explanations"]
    if not isinstance(wrong_explanations, dict):
        raise QuestionLoaderError(f"Question #{index} wrong_explanations must be an object.")

    source_refs = question["source_refs"]
    if not isinstance(source_refs, list):
        raise QuestionLoaderError(f"Question #{index} source_refs must be a list.")
