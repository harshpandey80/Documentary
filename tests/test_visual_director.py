import json
from pathlib import Path
import pytest

from docstudio.visual_director import (
    VisualDirector,
    SemanticVisualClassifier,
    VisualStrategy,
    VisualStatus,
    VisualLayer,
)


@pytest.fixture
def sample_narration_data():
    return {
        "topic": "The Disappearance of Flight 19",
        "paragraphs": [
            {
                "paragraph_id": "P01",
                "scene_id": "S01",
                "story_beat": "hook",
                "text": "Five combat-ready bombers departed the naval air station on a calm afternoon, only to vanish into the Atlantic abyss.",
                "claim_ids": ["C01"],
                "estimated_duration_sec": 5.4,
                "visual_prompt": "Five TBM Avenger bombers in tight formation over dark ocean",
                "broll_keywords": ["flight 19", "bomber", "ocean"],
            },
            {
                "paragraph_id": "P02",
                "scene_id": "S02",
                "story_beat": "investigation",
                "text": "The phone was last detected 4.2 kilometers from the hotel before the signal vanished.",
                "claim_ids": ["C02"],
                "estimated_duration_sec": 5.2,
                "visual_prompt": "Route map showing distance between hotel and last tower ping",
                "broll_keywords": ["map", "route", "hotel", "cell tower"],
            },
            {
                "paragraph_id": "P03",
                "scene_id": "S03",
                "story_beat": "evidence",
                "text": "Revenue tripled between 2019 and 2023, surging from twelve million to thirty-six million dollars.",
                "claim_ids": ["C03"],
                "estimated_duration_sec": 5.0,
                "visual_prompt": "Financial bar chart comparing revenue growth across five years",
                "broll_keywords": ["revenue", "chart", "growth"],
            },
            {
                "paragraph_id": "P04",
                "scene_id": "S04",
                "story_beat": "contradiction",
                "text": "Investigators found three direct contradictions between the naval logbook and the civilian radio transcript.",
                "claim_ids": ["C04"],
                "estimated_duration_sec": 5.5,
                "visual_prompt": "Side by side document comparison highlighting conflicting timestamps",
                "broll_keywords": ["contradiction", "comparison", "logbook"],
            },
        ],
    }


def test_semantic_classifier_rules():
    classifier = SemanticVisualClassifier()

    # Cold hook anomaly -> AI video recreation
    strat_hook, status_hook, _ = classifier.classify_shot(
        narration="The aircraft shuddered violently as magnetic compasses spun in circles.",
        story_beat="hook",
        is_cold_hook=True,
    )
    assert strat_hook == VisualStrategy.AI_CINEMATIC_VIDEO
    assert status_hook == VisualStatus.AI_GENERATED

    # Distance / Route -> ROUTE_MAP
    strat_route, status_route, _ = classifier.classify_shot(
        narration="The vehicle was tracked 4.2 kilometers along the northern highway.",
        story_beat="investigation",
    )
    assert strat_route == VisualStrategy.ROUTE_MAP
    assert status_route == VisualStatus.PROCEDURAL

    # Revenue / Financial Data -> DATA_CHART
    strat_chart, status_chart, _ = classifier.classify_shot(
        narration="Annual revenue tripled over five years.",
        story_beat="investigation",
    )
    assert strat_chart == VisualStrategy.DATA_CHART
    assert status_chart == VisualStatus.PROCEDURAL

    # Contradiction -> COMPARISON
    strat_comp, status_comp, _ = classifier.classify_shot(
        narration="The forensic testimony presented two direct contradictions.",
        story_beat="investigation",
    )
    assert strat_comp == VisualStrategy.COMPARISON
    assert status_comp == VisualStatus.PROCEDURAL

    # Declassified document -> PRIMARY_DOCUMENT
    strat_doc, status_doc, _ = classifier.classify_shot(
        narration="A declassified telegram from the naval command center was unsealed forty years later.",
        story_beat="evidence",
        referenced_claims=[{"source_type": "primary"}],
    )
    assert strat_doc == VisualStrategy.PRIMARY_DOCUMENT
    assert status_doc == VisualStatus.AUTHENTIC_SOURCE


def test_visual_director_storyboard_generation(sample_narration_data, tmp_path):
    director = VisualDirector(topic="The Disappearance of Flight 19")
    out_file = tmp_path / "storyboard.json"

    storyboard = director.create_storyboard(
        narration_data=sample_narration_data,
        output_file=out_file,
    )

    assert out_file.exists()
    assert storyboard["total_scenes"] == 4
    # Multiple shots per scene (not 1 visual per paragraph)
    assert storyboard["total_shots"] >= 8
    assert storyboard["total_duration_s"] > 15.0

    # Inspect scene shots
    for sc in storyboard["scenes"]:
        assert len(sc["shots"]) >= 2
        for sh in sc["shots"]:
            assert "shot_id" in sh
            assert "purpose" in sh
            assert "visual_strategy" in sh
            assert "visual_status" in sh
            assert 1.5 <= sh["duration"] <= 4.0
            assert "layers" in sh
            assert len(sh["layers"]) >= 2
            assert "BACKGROUND" in sh["layers"]
            assert "motion" in sh

    # Verify analytics
    analytics = storyboard.get("directorial_analytics", {})
    assert analytics["total_shots"] == storyboard["total_shots"]
    assert analytics["has_motion_graphics"] is True
    assert analytics["has_ai_video_or_stills"] is True
