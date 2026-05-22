from bot.services.scoring_service import calculate_score, get_exam_profile, load_exam_profiles


def test_load_exam_profile_from_example_file():
    profiles = load_exam_profiles("data/exam_profiles.example.json")
    profile = get_exam_profile("data/exam_profiles.example.json", "60310200")

    assert len(profiles) == 1
    assert profile["code"] == "60310200"
    assert profile["max_score"] == 189.0


def test_calculate_dtm_score():
    profile = get_exam_profile("data/exam_profiles.example.json", "60310200")
    questions = [
        {"subject": "tarix", "subject_group": "special_1"},
        {"subject": "tarix", "subject_group": "special_1"},
        {"subject": "ozbekiston_tarixi", "subject_group": "mandatory"},
    ]
    answers = [
        {"question_index": 0, "is_correct": True},
        {"question_index": 1, "is_correct": False},
        {"question_index": 2, "is_correct": True},
    ]

    result = calculate_score(questions, answers, profile)

    assert result["total_score"] == 4.2
    assert result["max_score"] == 7.3
    assert result["percentage"] == 57.53
    assert result["accuracy_percent"] == 66.67
    assert result["projected_full_score"] == 126.01
    assert result["full_max_score"] == 189.0
    assert result["breakdown"][0]["subject"] == "tarix"
    assert result["breakdown"][0]["max_score"] == 6.2
    assert result["breakdown"][1]["subject"] == "ozbekiston_tarixi"
    assert result["breakdown"][1]["max_score"] == 1.1
