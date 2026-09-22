"""
tests/test_golden_scenarios.py
==============================
Step 15: Golden Test Suite for the Remote Creative Director architecture.
Validates that across seven distinct documentary archetypes (History, Science, Biography,
Geography, Economics, Investigation, Conceptual), the system produces structurally valid,
semantically grounded, non-repetitive Shot Manifests.
"""

import pytest
from docstudio.remote_creative_director.manifest_schema import (
    ShotManifest,
    SceneManifest,
    ShotDirective,
    NarrationRange,
    VisualPurpose,
    SourceStrategy,
    ContinuityBible,
)
from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    TruthCategory,
    CostClass,
    ComputeClass,
)
from docstudio.remote_creative_director.validator import ShotManifestValidator


def test_golden_scenario_a_history():
    """History: Requires timeline, maps, archival evidence."""
    scenes = [
        SceneManifest(
            scene_id="SC_HIST_01",
            story_beat="The 1945 Naval Sortie",
            viewer_takeaway="Understand military departure context.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="HIST_01",
                    scene_id="SC_HIST_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.EXPLAIN_GEOGRAPHY,
                    visual_type=VisualType.MAP,
                    visual_reason="Display the flight route over the Florida coast.",
                    source_strategy=SourceStrategy.PROCEDURAL_MAP,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
                ShotDirective(
                    shot_id="HIST_02",
                    scene_id="SC_HIST_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_EVIDENCE,
                    visual_type=VisualType.AUTHENTIC_EVIDENCE,
                    visual_reason="Highlight the naval squadron dispatch logbook.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    evidence_claims=["claim_nav_01"],
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_hist",
        topic="The Lost Squadron of 1945",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid
    assert val.summary["shots_checked"] == 2
    assert VisualType.MAP.value in val.summary["type_distribution"]
    assert VisualType.AUTHENTIC_EVIDENCE.value in val.summary["type_distribution"]


def test_golden_scenario_b_science():
    """Science: Requires diagrams, explanatory graphics, numerical data."""
    scenes = [
        SceneManifest(
            scene_id="SC_SCI_01",
            story_beat="Gravitational Waves Detection",
            viewer_takeaway="Grasp the interferometer precision.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="SCI_01",
                    scene_id="SC_SCI_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_STATISTICS,
                    visual_type=VisualType.DATA_CHART,
                    visual_reason="Chart the strain amplitude of the wave over milliseconds.",
                    source_strategy=SourceStrategy.PROCEDURAL_CHART,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
                ShotDirective(
                    shot_id="SCI_02",
                    scene_id="SC_SCI_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_SCALE,
                    visual_type=VisualType.SCREEN_RECREATION,
                    visual_reason="Visualize laser interference fringe shifts.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    truth_category=TruthCategory.RECONSTRUCTION,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_sci",
        topic="Listening to Spacetime",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid
    assert val.summary["shots_checked"] == 2
    assert VisualType.DATA_CHART.value in val.summary["type_distribution"]


def test_golden_scenario_c_biography():
    """Biography: Requires photographs, chronology, human-centered visuals."""
    scenes = [
        SceneManifest(
            scene_id="SC_BIO_01",
            story_beat="Alan Turing Bletchley Park",
            viewer_takeaway="Observe cryptanalysis breakthrough.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="BIO_01",
                    scene_id="SC_BIO_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.INTRODUCE_PERSON,
                    visual_type=VisualType.PHOTOGRAPH,
                    visual_reason="Archival photographic portrait of Alan Turing in 1940.",
                    source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
                    truth_category=TruthCategory.ARCHIVAL,
                ),
                ShotDirective(
                    shot_id="BIO_02",
                    scene_id="SC_BIO_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_EVIDENCE,
                    visual_type=VisualType.AUTHENTIC_EVIDENCE,
                    visual_reason="Declassified Hut 8 deciphering work logs.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    evidence_claims=["turing_log_01"],
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_bio",
        topic="Alan Turing: The Codebreaker",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid
    assert VisualType.PHOTOGRAPH.value in val.summary["type_distribution"]


def test_golden_scenario_d_geography():
    """Geography: Requires maps, spatial transitions, geographic explanation."""
    scenes = [
        SceneManifest(
            scene_id="SC_GEO_01",
            story_beat="The Mariana Trench Subduction Zone",
            viewer_takeaway="Visualize Pacific tectonic subduction.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="GEO_01",
                    scene_id="SC_GEO_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.EXPLAIN_GEOGRAPHY,
                    visual_type=VisualType.MAP,
                    visual_reason="Satellite bathymetric contour map of Challenger Deep.",
                    source_strategy=SourceStrategy.PROCEDURAL_MAP,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
                ShotDirective(
                    shot_id="GEO_02",
                    scene_id="SC_GEO_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_SCALE,
                    visual_type=VisualType.DATA_CHART,
                    visual_reason="Vertical depth gauge comparing Mount Everest inverted to 10,994m.",
                    source_strategy=SourceStrategy.PROCEDURAL_CHART,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_geo",
        topic="The Mariana Abyss",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid


def test_golden_scenario_e_economics():
    """Economics: Requires charts, statistics, comparison graphics."""
    scenes = [
        SceneManifest(
            scene_id="SC_ECON_01",
            story_beat="The 2008 Subprime Collapse",
            viewer_takeaway="Analyze mortgage default acceleration.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="ECON_01",
                    scene_id="SC_ECON_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_STATISTICS,
                    visual_type=VisualType.DATA_CHART,
                    visual_reason="Bar chart depicting CDO issuance plummeting from $400B to near zero.",
                    source_strategy=SourceStrategy.PROCEDURAL_CHART,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
                ShotDirective(
                    shot_id="ECON_02",
                    scene_id="SC_ECON_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_CONTRADICTION,
                    visual_type=VisualType.AUTHENTIC_EVIDENCE,
                    visual_reason="AAA rating seal stamped on toxic tranche prospectus.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    evidence_claims=["cdo_rating_01"],
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_econ",
        topic="The Anatomy of Financial Contagion",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid


def test_golden_scenario_f_investigation():
    """Investigation: Requires documents, evidence, source traceability."""
    scenes = [
        SceneManifest(
            scene_id="SC_INV_01",
            story_beat="The Disclosed Surveillance Memo",
            viewer_takeaway="Examine unredacted executive warrant.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="INV_01",
                    scene_id="SC_INV_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.SHOW_EVIDENCE,
                    visual_type=VisualType.AUTHENTIC_EVIDENCE,
                    visual_reason="FOIA declassified agency memorandum with yellow forensic highlight.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    evidence_claims=["foia_memo_2024"],
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
                ShotDirective(
                    shot_id="INV_02",
                    scene_id="SC_INV_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.EMPHASIZE_REVEAL,
                    visual_type=VisualType.TIMELINE_DIAGRAM,
                    visual_reason="Timeline correlating meeting date with sudden surveillance initiation.",
                    source_strategy=SourceStrategy.PROCEDURAL_DOCUMENT,
                    truth_category=TruthCategory.DOCUMENTARY_EVIDENCE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_inv",
        topic="The Unsealed Wiretaps",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid


def test_golden_scenario_g_conceptual():
    """Conceptual: Requires metaphorical visuals, generated imagery, motion graphics."""
    scenes = [
        SceneManifest(
            scene_id="SC_CONC_01",
            story_beat="The Heat Death of the Universe",
            viewer_takeaway="Contemplate entropy reaching maximum.",
            narration_range=NarrationRange(0.0, 5.0),
            shots=[
                ShotDirective(
                    shot_id="CONC_01",
                    scene_id="SC_CONC_01",
                    start=0.0,
                    end=2.5,
                    duration=2.5,
                    purpose=VisualPurpose.CREATE_EMOTIONAL_WEIGHT,
                    visual_type=VisualType.AI_IMAGE_TO_VIDEO,
                    visual_reason="A dying solitary red dwarf star drifting into cold blackness.",
                    source_strategy=SourceStrategy.GENERATE_AI_VIDEO,
                    truth_category=TruthCategory.CONCEPTUAL,
                ),
                ShotDirective(
                    shot_id="CONC_02",
                    scene_id="SC_CONC_01",
                    start=2.5,
                    end=5.0,
                    duration=2.5,
                    purpose=VisualPurpose.RESET_VISUAL_PACING,
                    visual_type=VisualType.ATMOSPHERIC_VISUAL,
                    visual_reason="Abstract visual void representing complete thermodynamic equilibrium.",
                    source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
                    truth_category=TruthCategory.ILLUSTRATIVE,
                ),
            ],
        )
    ]
    manifest = ShotManifest(
        documentary_id="doc_conc",
        topic="Entropy: The Final Silence",
        total_duration=5.0,
        scenes=scenes,
    )
    val = ShotManifestValidator.validate(manifest)
    assert val.valid
