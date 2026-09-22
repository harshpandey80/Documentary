from docstudio.story_engine import StoryEngine

def test_story_engine_fallback():
    engine = StoryEngine()
    fake_research = {
        "topic": "The D.B. Cooper Incident",
        "central_question": "Did Dan Cooper survive the parachute jump into the freezing storm?",
        "claims": [
            {"claim_id": "C001", "claim": "Cooper demanded $200,000 and four parachutes."},
            {"claim_id": "C002", "claim": "He jumped from the aft stairs of a Boeing 727 at 10,000 feet."},
            {"claim_id": "C003", "claim": "No trace of Cooper was ever recovered in the wilderness."},
        ],
        "unknowns": ["Whether the parachutes deployed properly in the sub-zero storm"],
    }

    story = engine._generate_fallback_story(fake_research, duration_target_s=240.0)
    assert story["topic"] == "The D.B. Cooper Incident"
    assert "beats" in story
    assert len(story["beats"]) == 4
    for b in story["beats"]:
        assert "viewer_learning" in b
        assert "viewer_seeing_intent" in b
        assert "claim_ids" in b
        assert len(b["claim_ids"]) > 0
        assert b["target_duration_s"] == 60.0

def test_story_engine_validation():
    engine = StoryEngine()
    assert engine._validate_story_data({}) is False
    assert engine._validate_story_data({"beats": []}) is False
