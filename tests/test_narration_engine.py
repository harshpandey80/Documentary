import json
from pathlib import Path
import pytest

from docstudio.scriptwriter import ScriptWriter
from docstudio.claims_ledger import ClaimsLedger


@pytest.fixture
def sample_story():
    return {
        "topic": "The Mystery of Flight 19",
        "logline": "Five US Navy torpedo bombers vanish into the Atlantic without a trace.",
        "central_question": "How did five combat-ready aircraft and their rescue plane vanish?",
        "stakes": "The worst peacetime training disaster in naval aviation history.",
        "structure_type": "investigative_forensic",
        "target_total_duration_s": 300.0,
        "beats": [
            {
                "beat_id": "B01",
                "beat_name": "The Vanishing",
                "story_function": "hook",
                "viewer_learning": "Five Navy Avengers departed on a routine patrol and never returned.",
                "viewer_seeing_intent": "Archival 1945 airbase flightline photos with radar graphic overlay",
                "target_duration_s": 15.0,
                "claim_ids": ["C01"],
                "intensity": 9,
                "mood": "tension",
            },
            {
                "beat_id": "B02",
                "beat_name": "The Compass Anomaly",
                "story_function": "investigation",
                "viewer_learning": "Lieutenant Taylor radioed that both of his compasses had suffered simultaneous electrical failure.",
                "viewer_seeing_intent": "Declassified naval telegram zoom with glowing compass failure highlight",
                "target_duration_s": 25.0,
                "claim_ids": ["C02"],
                "intensity": 7,
                "mood": "tension",
            },
            {
                "beat_id": "B03",
                "beat_name": "The Unresolved Enigma",
                "story_function": "resolution",
                "viewer_learning": "Despite the largest peacetime search in history covering 250,000 square miles, no wreckage was ever located.",
                "viewer_seeing_intent": "Expansive sea search map showing grid search coordinates",
                "target_duration_s": 20.0,
                "claim_ids": ["C01", "C03"],
                "intensity": 6,
                "mood": "somber",
            },
        ],
        "unanswered_questions": ["Where is the wreckage?"],
        "ending_takeaway": "The event remains classified as cause unknown.",
    }


@pytest.fixture
def sample_claims():
    return {
        "topic": "The Mystery of Flight 19",
        "claims": [
            {
                "claim_id": "C01",
                "statement": "Five TBM Avenger bombers vanished on December 5, 1945.",
                "source": "Naval Board of Inquiry Report 1946",
                "source_type": "primary",
                "verification_status": "verified",
                "confidence": 1.0,
            },
            {
                "claim_id": "C02",
                "statement": "Lieutenant Charles Taylor reported simultaneous compass failure at 15:45.",
                "source": "Radio transcript FT-28",
                "source_type": "primary",
                "verification_status": "verified",
                "confidence": 0.98,
            },
            {
                "claim_id": "C03",
                "statement": "Search operations covered 250,000 square miles of the Atlantic.",
                "source": "Coast Guard Historical Office",
                "source_type": "secondary",
                "verification_status": "verified",
                "confidence": 0.95,
            },
        ],
    }


def test_scriptwriter_generate_narration_deterministic(sample_story, sample_claims, tmp_path, monkeypatch):
    writer = ScriptWriter()
    monkeypatch.setattr(writer, "_generate_narration_with_llm", lambda **kwargs: None)
    out_file = tmp_path / "narration.json"

    narration = writer.generate_narration_from_story(
        story_data=sample_story,
        claims_data=sample_claims,
        output_file=out_file,
        runtime_target="5m",
    )

    assert out_file.exists()
    assert "paragraphs" in narration
    assert len(narration["paragraphs"]) == len(sample_story["beats"])

    # Verify paragraph schema
    for idx, p in enumerate(narration["paragraphs"]):
        assert p["paragraph_id"] == f"P{idx+1:02d}"
        assert p["beat_id"] == sample_story["beats"][idx]["beat_id"]
        assert len(p["text"]) > 10
        assert p["claim_ids"] == sample_story["beats"][idx]["claim_ids"]
        assert p["emotional_tag"] in ["tension", "reveal", "somber", "triumphant", "ambient_drone"]
        assert p["intensity"] >= 1
        assert p["estimated_duration_sec"] > 0
        assert "visual_prompt" in p
        assert "broll_keywords" in p
        assert "motion" in p

    # Verify backward-compatible acts array
    assert "acts" in narration
    assert len(narration["acts"]) > 0
    scenes_count = sum(len(a["scenes"]) for a in narration["acts"])
    assert scenes_count == len(narration["paragraphs"])


def test_narration_claim_provenance_integration(sample_story, sample_claims, monkeypatch):
    writer = ScriptWriter()
    monkeypatch.setattr(writer, "_generate_narration_with_llm", lambda **kwargs: None)
    narration = writer.generate_narration_from_story(
        story_data=sample_story,
        claims_data=sample_claims,
    )

    ledger = ClaimsLedger()
    ledger.ingest_research_claims(sample_claims)

    provenance_report = ledger.get_provenance_report(narration)
    assert provenance_report["all_claims_verified"] is True, f"Report: {provenance_report}"
    assert provenance_report["unknown_claims"] == []
    assert provenance_report["verified_count"] >= 2

    ok, violations = ledger.verify_narration_claim_provenance(narration)
    assert ok is True
    assert violations == []
