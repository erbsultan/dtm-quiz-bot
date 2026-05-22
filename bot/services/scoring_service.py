import json
from pathlib import Path
from typing import Any

DEFAULT_PROFILE_CODE = "60310200"


class ExamProfileError(ValueError):
    pass


def load_exam_profiles(file_path: str | Path) -> list[dict[str, Any]]:
    path = Path(file_path)
    if not path.exists():
        raise ExamProfileError(f"Exam profiles file not found: {path}")

    try:
        profiles = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExamProfileError(f"Invalid JSON in exam profiles file: {exc}") from exc

    if not isinstance(profiles, list) or not profiles:
        raise ExamProfileError("Exam profiles file must contain a non-empty list.")

    for index, profile in enumerate(profiles, start=1):
        _validate_profile(profile, index)

    return profiles


def get_exam_profile(file_path: str | Path, profile_code: str | None = None) -> dict[str, Any]:
    profiles = load_exam_profiles(file_path)
    code = profile_code or DEFAULT_PROFILE_CODE
    for profile in profiles:
        if profile["code"] == code:
            return profile
    raise ExamProfileError(f"Exam profile not found: {code}")


def calculate_score(
    questions: list[dict[str, Any]],
    answers: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    rules_by_subject = {rule["subject"]: rule for rule in profile["subjects"]}
    breakdown: list[dict[str, Any]] = []
    total_score = 0.0

    for subject in sorted({question["subject"] for question in questions}):
        subject_questions = [question for question in questions if question["subject"] == subject]
        subject_indexes = {
            index for index, question in enumerate(questions) if question["subject"] == subject
        }
        correct = sum(
            1
            for answer in answers
            if answer["question_index"] in subject_indexes and answer["is_correct"]
        )
        total = len(subject_questions)
        rule = rules_by_subject.get(subject)
        points_per_correct = float(rule["points_per_correct"]) if rule else 0.0
        subject_group = rule["subject_group"] if rule else subject_questions[0].get("subject_group", "unknown")
        configured_total = int(rule["questions"]) if rule else total
        score = round(correct * points_per_correct, 2)
        max_score = round(configured_total * points_per_correct, 2)
        total_score += score

        breakdown.append(
            {
                "subject": subject,
                "subject_group": subject_group,
                "correct": correct,
                "total": total,
                "points_per_correct": points_per_correct,
                "score": score,
                "max_score": max_score,
            }
        )

    profile_max_score = float(profile["max_score"])
    total_score = round(total_score, 2)
    percentage = round((total_score / profile_max_score) * 100, 2) if profile_max_score else 0.0

    return {
        "total_score": total_score,
        "max_score": profile_max_score,
        "percentage": percentage,
        "breakdown": breakdown,
    }


def _validate_profile(profile: Any, index: int) -> None:
    if not isinstance(profile, dict):
        raise ExamProfileError(f"Profile #{index} must be an object.")
    for field in ("code", "name", "max_score", "subjects"):
        if field not in profile:
            raise ExamProfileError(f"Profile #{index} is missing required field: {field}")
    if not isinstance(profile["subjects"], list) or not profile["subjects"]:
        raise ExamProfileError(f"Profile #{index} subjects must be a non-empty list.")
    for subject_index, subject in enumerate(profile["subjects"], start=1):
        for field in ("subject", "subject_group", "questions", "points_per_correct"):
            if field not in subject:
                raise ExamProfileError(
                    f"Profile #{index} subject #{subject_index} is missing required field: {field}"
                )
