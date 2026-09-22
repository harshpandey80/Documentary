import pytest
from docstudio.research_engine import ResearchEngine, ResearchFailureError

def test_research_engine_fallback_requires_grounding():
    engine = ResearchEngine()
    # Unverified/ungrounded fallback must raise ResearchFailureError
    with pytest.raises(ResearchFailureError):
        engine._generate_fallback_research("The D.B. Cooper Skyjacking")

def test_research_engine_validation():
    engine = ResearchEngine()
    invalid_data = {"topic": "Foo"}
    assert engine._validate_research_data(invalid_data) is False

    grounded_claims = [
        {"claim_id": "CLM-001", "statement": "Flight 19 departed Fort Lauderdale.", "source": "US Navy Court of Inquiry"},
        {"claim_id": "CLM-002", "statement": "Radio contact was lost over the Atlantic.", "source": "US Navy Operations Log"}
    ]
    valid_data = engine._generate_fallback_research("Flight 19", grounded_claims=grounded_claims)
    assert engine._validate_research_data(valid_data) is True

