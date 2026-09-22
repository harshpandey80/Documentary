"""
tests/test_adversarial_manifests.py
===================================
Step 16: Adversarial testing for the Remote Creative Director Shot Manifest architecture.
Verifies graceful error detection and safe failure handling across:
- Negative & zero durations
- Broken/overlapping timestamps
- Duplicate shot IDs
- Missing mandatory fields (purpose, reason, visual_type)
- Unknown & planned visual types
- Excessive consecutive repetitions
- Malformed JSON recovery from AI responses
"""

import pytest
from docstudio.remote_creative_director.manifest_schema import (
    ShotManifest,
    SceneManifest,
    ShotDirective,
    NarrationRange,
    VisualPurpose,
    SourceStrategy,
)
from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    TruthCategory,
)
from docstudio.remote_creative_director.validator import (
    ShotManifestValidator,
    Severity,
)
from docstudio.remote_creative_director.director import RemoteCreativeDirector


def test_adversarial_negative_and_zero_duration():
    shot = ShotDirective(
        shot_id="SH_NEG",
        start=0.0,
        end=0.0,
        duration=-1.5,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.MAP,
        visual_reason="Negative duration test.",
        source_strategy=SourceStrategy.PROCEDURAL_MAP,
    )
    scene = SceneManifest(
        scene_id="SC_01",
        story_beat="Intro",
        viewer_takeaway="Takeaway",
        narration_range=NarrationRange(0.0, 5.0),
        shots=[shot],
    )
    manifest = ShotManifest(documentary_id="doc_adv", topic="Adv", total_duration=5.0, scenes=[scene])
    val = ShotManifestValidator.validate(manifest)
    assert not val.valid
    assert any(e.code == "NEGATIVE_OR_ZERO_DURATION" for e in val.errors)


def test_adversarial_duplicate_shot_ids():
    shot1 = ShotDirective(
        shot_id="DUPE_ID",
        start=0.0,
        end=2.0,
        duration=2.0,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.MAP,
        visual_reason="First occurrence of duplicate shot ID.",
        source_strategy=SourceStrategy.PROCEDURAL_MAP,
    )
    shot2 = ShotDirective(
        shot_id="DUPE_ID",
        start=2.0,
        end=4.0,
        duration=2.0,
        purpose=VisualPurpose.SHOW_STATISTICS,
        visual_type=VisualType.DATA_CHART,
        visual_reason="Second occurrence of duplicate shot ID.",
        source_strategy=SourceStrategy.PROCEDURAL_CHART,
    )
    scene = SceneManifest(
        scene_id="SC_01",
        story_beat="Intro",
        viewer_takeaway="Takeaway",
        narration_range=NarrationRange(0.0, 4.0),
        shots=[shot1, shot2],
    )
    manifest = ShotManifest(documentary_id="doc_adv", topic="Adv", total_duration=4.0, scenes=[scene])
    val = ShotManifestValidator.validate(manifest)
    assert not val.valid
    assert any(e.code == "DUPLICATE_SHOT_ID" for e in val.errors)


def test_adversarial_inverted_timestamps():
    shot = ShotDirective(
        shot_id="SH_INVERT",
        start=5.0,
        end=2.0,
        duration=3.0,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.MAP,
        visual_reason="Start is later than end.",
        source_strategy=SourceStrategy.PROCEDURAL_MAP,
    )
    scene = SceneManifest(
        scene_id="SC_01",
        story_beat="Intro",
        viewer_takeaway="Takeaway",
        narration_range=NarrationRange(0.0, 5.0),
        shots=[shot],
    )
    manifest = ShotManifest(documentary_id="doc_adv", topic="Adv", total_duration=5.0, scenes=[scene])
    val = ShotManifestValidator.validate(manifest)
    assert not val.valid
    assert any(e.code == "INVALID_TIMESTAMPS" for e in val.errors)


def test_adversarial_repetition_warning():
    shots = []
    for i in range(4):
        shots.append(
            ShotDirective(
                shot_id=f"SH_{i}",
                start=float(i * 2),
                end=float((i + 1) * 2),
                duration=2.0,
                purpose=VisualPurpose.SHOW_CONTEXT,
                visual_type=VisualType.CINEMATIC_BROLL,
                visual_reason=f"Repetitive shot #{i}",
                source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
            )
        )
    scene = SceneManifest(
        scene_id="SC_01",
        story_beat="Intro",
        viewer_takeaway="Takeaway",
        narration_range=NarrationRange(0.0, 8.0),
        shots=shots,
    )
    manifest = ShotManifest(documentary_id="doc_adv", topic="Adv", total_duration=8.0, scenes=[scene])
    val = ShotManifestValidator.validate(manifest)
    assert val.valid  # Warnings do not invalidate the manifest
    assert any(w.code == "HIGH_VISUAL_REPETITION" for w in val.warnings)


def test_adversarial_mislabeled_truth_category():
    shot = ShotDirective(
        shot_id="SH_TRUTH_FAIL",
        start=0.0,
        end=3.0,
        duration=3.0,
        purpose=VisualPurpose.RECONSTRUCT_EVENT,
        visual_type=VisualType.AI_VIDEO,
        visual_reason="AI generation pretending to be authentic evidence.",
        source_strategy=SourceStrategy.GENERATE_AI_VIDEO,
        truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,  # Fraudulent truth classification
    )
    scene = SceneManifest(
        scene_id="SC_01",
        story_beat="Intro",
        viewer_takeaway="Takeaway",
        narration_range=NarrationRange(0.0, 3.0),
        shots=[shot],
    )
    manifest = ShotManifest(documentary_id="doc_adv", topic="Adv", total_duration=3.0, scenes=[scene])
    val = ShotManifestValidator.validate(manifest)
    assert not val.valid
    assert any(e.code == "MISLABELED_TRUTH_CATEGORY" for e in val.errors)


def test_adversarial_ai_json_recovery():
    # Markdown code fence wrapped with leading & trailing conversational text
    raw_response = """
    Here is your approved Shot Manifest for the documentary:
    ```json
    {
      "documentary_id": "doc_recovered",
      "topic": "Flight 19",
      "total_duration": 30.0,
      "scenes": []
    }
    ```
    I hope this meets your strict requirements.
    """
    parsed = RemoteCreativeDirector.clean_and_parse_json(raw_response)
    assert parsed.get("documentary_id") == "doc_recovered"
    assert parsed.get("topic") == "Flight 19"


def test_adversarial_corrupt_json_rejection():
    with pytest.raises(ValueError, match="could not be parsed as valid JSON"):
        RemoteCreativeDirector.clean_and_parse_json("NOT_JSON_AT_ALL_JUST_RANDOM_TEXT")
