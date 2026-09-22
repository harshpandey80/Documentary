import pytest
from docstudio.story_validator import StoryValidator

def test_story_validator_fields():
    sv = StoryValidator()
    valid_script = {
        "question": "How did a small island forge a global empire?",
        "answer_claim_id": "CLM-004",
        "twist": "Coal and steam, not military might alone, transformed the economy.",
    }
    ok, errs = sv.validate_script_structure(valid_script)
    assert ok
    assert len(errs) == 0

    invalid_script = {
        "question": "Where is the lost fleet?",
    }
    ok, errs = sv.validate_script_structure(invalid_script)
    assert not ok
    assert len(errs) == 2


def test_answer_timing_last_25_percent():
    sv = StoryValidator()
    script_data = {
        "answer_claim_id": "CLM-ANS",
    }
    # Total duration 48.0s -> last 25% starts at 36.0s
    scenes = [
        {"scene_id": "SCENE-01", "start": 0.0, "duration": 10.0, "claim_ids": ["CLM-001"]},
        {"scene_id": "SCENE-02", "start": 10.0, "duration": 15.0, "claim_ids": ["CLM-002"]},
        {"scene_id": "SCENE-03", "start": 25.0, "duration": 12.0, "claim_ids": ["CLM-003"]},
        {"scene_id": "SCENE-04", "start": 37.0, "duration": 11.0, "claim_ids": ["CLM-ANS"]},
    ]
    ok, msg = sv.validate_answer_timing(script_data, scenes, 48.0)
    assert ok
    assert "in last 25% window" in msg

    # Answer too early
    scenes_early = [
        {"scene_id": "SCENE-01", "start": 0.0, "duration": 10.0, "claim_ids": ["CLM-ANS"]},
        {"scene_id": "SCENE-02", "start": 10.0, "duration": 38.0, "claim_ids": ["CLM-002"]},
    ]
    ok_early, msg_early = sv.validate_answer_timing(script_data, scenes_early, 48.0)
    assert not ok_early


def test_banned_undelivered_content_tease():
    sv = StoryValidator()
    clean_narration = "Like and subscribe to uncover the unsealed files."
    ok, violations = sv.validate_no_undelivered_content_tease(clean_narration)
    assert ok
    assert len(violations) == 0

    tease_narration = "Find out what happened next in part 2 of our investigation."
    ok, violations = sv.validate_no_undelivered_content_tease(tease_narration)
    assert not ok
    assert len(violations) > 0


def test_word_count_pacing():
    sv = StoryValidator(target_wps=2.4)
    # 45s at 2.4 wps = 108 words. Range: [81, 135]
    ok, msg = sv.validate_word_count_pacing(105, 45.0)
    assert ok

    ok_fail, msg_fail = sv.validate_word_count_pacing(50, 45.0)
    assert not ok_fail


def test_static_holds_validation():
    sv = StoryValidator()
    shots = [
        {"duration": 2.5, "motion": "zoom_in"},
        {"duration": 3.0, "motion": "pan_left"},
        {"duration": 4.5, "motion": "none"},  # static hold > 4.0s
    ]
    ok, violations = sv.validate_static_holds(shots, max_static_hold_s=4.0)
    assert not ok
    assert len(violations) == 1

    shots_fixed = [
        {"duration": 2.5, "motion": "zoom_in"},
        {"duration": 3.0, "motion": "pan_left"},
        {"duration": 4.5, "motion": "zoom_out"},
    ]
    ok_fixed, violations_fixed = sv.validate_static_holds(shots_fixed, max_static_hold_s=4.0)
    assert ok_fixed
