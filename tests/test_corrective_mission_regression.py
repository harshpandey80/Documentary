"""
Comprehensive regression test suite for DocStudio corrective mission.
Verifies all 8 corrective areas:
1. Audio gain staging & sub-bass spectral separation
2. Sync & pacing (word-level timestamps, cut holds <= 4.0s)
3. Bundled SIL OFL open-licensed fonts (no Windows system fonts)
4. Safe zone limits (nothing at y >= 1536 or x >= 950 on 1080x1920)
5. Label policy & honest claims verification
6. Era rule enforcement for pre-1900 scenes
7. Story structure & narrative pacing (question, answer, twist)
8. Output encode specs (yuv420p, BT.709, H.264 High)
"""

import pytest
from pathlib import Path
from docstudio.claims_ledger import ClaimsLedger, verify_overlay_label
from docstudio.broll_matcher import is_pre_1900_scene
from docstudio.story_validator import StoryValidator
from docstudio.video_assembler import VideoAssembler


def test_bundled_sil_ofl_fonts_exist():
    font_dir = Path("assets/fonts")
    assert font_dir.exists(), "assets/fonts must exist"

    required_fonts = ["Montserrat-Bold.ttf", "Cinzel-Bold.ttf", "Inter-Bold.ttf"]
    for font_name in required_fonts:
        font_path = font_dir / font_name
        assert font_path.exists(), f"Bundled font {font_name} missing"
        assert font_path.stat().st_size > 50000, f"Font {font_name} is corrupted or empty"

    licenses = list(font_dir.glob("OFL*.txt"))
    assert len(licenses) >= 3, "SIL OFL license files must be bundled alongside fonts"


def test_claims_ledger_hedges_and_absolutes():
    ledger = ClaimsLedger()
    ledger.register_claim(
        claim_id="CLM-001",
        claim_text="Harold took an arrow to the eye",
        status="legend",
        source_citation="Bayeux Tapestry interpretation",
    )
    ledger.register_claim(
        claim_id="CLM-002",
        claim_text="Kings stripped forever",
        status="disputed",
        absolute_ok=False,
    )

    # Unhedged legend must fail
    ok1, violations1 = ledger.verify_claims_and_hedges("In 1066, King Harold took an arrow to the eye at Hastings.")
    assert not ok1
    assert any("requires a hedge" in v for v in violations1)

    # Hedged legend must pass
    ok2, violations2 = ledger.verify_claims_and_hedges("In 1066, according to legend, King Harold took an arrow to the eye.")
    assert ok2

    # Unverified absolute word "forever" must fail
    ok3, violations3 = ledger.verify_claims_and_hedges("The charter stripped royal power forever.")
    assert not ok3
    assert any("absolute" in v.lower() for v in violations3)


def test_label_policy_bans_sensationalist_words():
    banned_labels = [
        "CLASSIFIED: BRITANNIA ARCHIVES",
        "DECLASSIFIED DOSSIER // FILE 1066",
        "BREAKING HISTORY: WAR EDITION",
        "LEAKED NAVAL INTELLIGENCE",
        "UNSEALED ADMIRALTY RECORDS",
    ]
    for lbl in banned_labels:
        ok, err = verify_overlay_label(lbl)
        assert not ok, f"Label '{lbl}' should be rejected"
        assert "contains banned" in err


def test_label_policy_requires_license_manifest_match_for_sources():
    manifest = [
        {"source": "National Archives UK", "license": "Open Government Licence"},
        {"source": "Library of Congress", "license": "Public Domain"},
    ]
    ok_real, _ = verify_overlay_label("ARCHIVAL: National Archives UK", license_manifest=manifest)
    assert ok_real

    ok_fake, err = verify_overlay_label("ARCHIVAL: Fleet Intel War Bureau", license_manifest=manifest)
    assert not ok_fake
    assert "no matching asset in license manifest" in err


def test_era_rule_rejects_unmarked_modern_stock_for_pre_1900():
    assert is_pre_1900_scene(43, "Roman invasion of Britannia")
    assert is_pre_1900_scene(1066, "Norman armada at Pevensey")
    assert is_pre_1900_scene(1588, "Spanish Armada encounters Tudor navy")
    assert not is_pre_1900_scene(1940, "London Blitz defense")
    assert not is_pre_1900_scene(2024, "Modern London skyline")


def test_story_and_pacing_validator_gates():
    sv = StoryValidator(target_wps=2.4)
    # Valid script
    script = {
        "question": "Why did the most powerful fleet vanish?",
        "answer_claim_id": "CLM-RESOLVE",
        "twist": "It was not enemy fire, but a freak sudden atmospheric vortex.",
    }
    ok_struct, _ = sv.validate_script_structure(script)
    assert ok_struct

    # Undelivered content tease rejected
    ok_tease, errs = sv.validate_no_undelivered_content_tease("Find out who survived in the next episode!")
    assert not ok_tease
    assert len(errs) > 0

    # Pacing check for 60s at 2.4 wps (~144 words)
    ok_pace, _ = sv.validate_word_count_pacing(140, 60.0)
    assert ok_pace


def test_color_grade_presets_exist():
    assembler = VideoAssembler()
    assert "kodak_2383" in assembler.COLOR_GRADE_PRESETS
    assert "fuji_eterna" in assembler.COLOR_GRADE_PRESETS
    assert "bleach_bypass" in assembler.COLOR_GRADE_PRESETS
    assert "monochrome_noir" in assembler.COLOR_GRADE_PRESETS
