import pytest
from pathlib import Path

from docstudio.motion_graphics.graphic_intent import GraphicIntent, validate_graphic_intent
from docstudio.evidence_engine import EvidenceVisualizationEngine, InformationType


def test_graphic_intent_validation():
    # 1. Null/empty purpose must be rejected
    invalid_intent_1 = GraphicIntent(
        purpose="",
        source_claims=["C01"],
        key_message="Missing purpose",
        visualization_type="line_chart",
        data=[{"value": 10}],
    )
    valid, reason = validate_graphic_intent(invalid_intent_1)
    assert valid is False
    assert "purpose" in reason

    # 2. Chart with no source claims must be rejected
    invalid_intent_2 = GraphicIntent(
        purpose="Show revenue growth",
        source_claims=[],
        key_message="Revenue grew 3x",
        visualization_type="bar_chart",
        data=[{"value": 10}, {"value": 30}],
    )
    valid, reason = validate_graphic_intent(invalid_intent_2)
    assert valid is False
    assert "source_claims" in reason

    # 3. Chart with no data must be rejected
    invalid_intent_3 = GraphicIntent(
        purpose="Show casualty count",
        source_claims=["C02"],
        key_message="Casualties dropped",
        visualization_type="statistic",
        data=[],
    )
    valid, reason = validate_graphic_intent(invalid_intent_3)
    assert valid is False
    assert "data points" in reason

    # 4. Valid intent passes cleanly
    valid_intent = GraphicIntent(
        purpose="Show verified revenue growth",
        source_claims=["C31"],
        key_message="Revenue increased 3x",
        visualization_type="bar_chart",
        data=[{"year": 2019, "value": 12}, {"year": 2023, "value": 36}],
    )
    valid, reason = validate_graphic_intent(valid_intent)
    assert valid is True
    assert reason == "Valid"


def test_evidence_visualization_engine_mappings():
    engine = EvidenceVisualizationEngine()

    # Distance -> route
    info_dist = engine.detect_information_type("The subject was last seen 4.2 kilometers from the hotel.")
    assert info_dist == InformationType.DISTANCE

    # Money -> money
    info_money = engine.detect_information_type("The project exceeded its twelve million dollar budget.")
    assert info_money == InformationType.MONEY

    # Contradiction -> contradiction
    info_contra = engine.detect_information_type("The naval logbook contradicted civilian radar records.")
    assert info_contra == InformationType.CONTRADICTION

    # Document -> document
    info_doc = engine.detect_information_type("Investigators examined a declassified memo from 1984.")
    assert info_doc == InformationType.DOCUMENT

    # Create intent from evidence
    intent, is_valid, msg = engine.create_graphic_intent(
        shot_id="S02_A",
        narration_text="The subject traveled 4.2 kilometers northeast.",
        claim_entry={"claim_id": "C05", "statement": "Travel distance was 4.2 km"},
        duration_s=3.0,
    )
    assert is_valid is True
    assert intent.visualization_type == "route"
    assert "C05" in intent.source_claims
