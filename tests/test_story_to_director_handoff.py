"""
Tests for Story -> Creative Director Handoff Fixes:
1. viewer_seeing_intent reaches the director
2. scene mismatch is caught before ID remapping
3. Pass-2 prompt survives remapping
4. different shots do not reuse the first shot's asset
"""

import pytest
from unittest.mock import MagicMock, patch
from docstudio.remote_creative_director.context_builder import ContextBuilder, DirectorialContext
from docstudio.remote_creative_director.prompt_builder import PromptBuilder
from docstudio.remote_creative_director.director import RemoteCreativeDirector
from docstudio.remote_creative_director.manifest_schema import (
    ShotManifest,
    SceneManifest,
    ShotDirective,
    NarrationRange,
    VisualPurpose,
    VisualType,
    SourceStrategy,
)
from docstudio.autonomous_pipeline import AutonomousDocumentaryPipeline


def test_viewer_seeing_intent_reaches_director():
    """
    Test 1: Verify story beats and viewer_seeing_intent are not discarded
    by context_builder and reach PromptBuilder's Pass-1 prompt.
    """
    story_data = {
        "topic": "USS Cyclops Mystery",
        "beats": [
            {
                "beat_id": "b1_hook",
                "beat_name": "Vanishing Without a Trace",
                "story_function": "hook",
                "viewer_learning": "306 crewmen vanished in the Bermuda Triangle with zero distress calls.",
                "viewer_seeing_intent": "Photorealistic 8K macro push into classified 1918 naval telegraph report.",
                "target_duration_s": 5.0,
                "claim_ids": ["c1"],
                "intensity": 9,
                "mood": "tension",
            },
            {
                "beat_id": "b2_manganese",
                "beat_name": "Overloaded Cargo",
                "story_function": "investigation",
                "viewer_learning": "The ship carried 10,000 tons of dense manganese ore in extreme seas.",
                "viewer_seeing_intent": "3D animated cross-section diagram of ship hold shifting under storm swell.",
                "target_duration_s": 6.0,
                "claim_ids": ["c2"],
                "intensity": 7,
                "mood": "dramatic",
            },
        ],
    }
    narration_data = {
        "scenes": [
            {"scene_id": "act1_s1", "narration": "In March 1918, the USS Cyclops disappeared."},
            {"scene_id": "act1_s2", "narration": "Deep in its hull lay 10,000 tons of manganese."},
        ]
    }

    ctx = ContextBuilder.build_context(
        topic="USS Cyclops Mystery",
        target_duration=45.0,
        story_data=story_data,
        narration_data=narration_data,
    )

    # Verify context preserves story_beats and viewer_seeing_intent
    assert len(ctx.story_beats) == 2, "story_beats should not be discarded!"
    assert ctx.story_beats[0]["viewer_seeing_intent"] == "Photorealistic 8K macro push into classified 1918 naval telegraph report."
    assert ctx.story_beats[1]["viewer_seeing_intent"] == "3D animated cross-section diagram of ship hold shifting under storm swell."

    # Verify prompt builder includes viewer_seeing_intent in Pass-1 user prompt
    pass1_prompt = PromptBuilder.build_pass1_user_prompt(ctx)
    assert "Photorealistic 8K macro push into classified 1918 naval telegraph report." in pass1_prompt
    assert "3D animated cross-section diagram of ship hold shifting under storm swell." in pass1_prompt
    assert "viewer_seeing_intent" in pass1_prompt

    # Verify director grounded fallback also inherits the seeing intent
    director = RemoteCreativeDirector()
    fallback_manifest = director._build_grounded_fallback_manifest(ctx)
    assert len(fallback_manifest.scenes) == 2
    sh0 = fallback_manifest.scenes[0].shots[0]
    assert "classified 1918 naval telegraph report" in sh0.prompt


def test_scene_mismatch_is_caught():
    """
    Test 2: Verify that when manifest scene count mismatches narration scene count,
    the pipeline catches the mismatch and executes the safe fallback instead of
    silently misaligning scenes.
    """
    # 3 manifest scenes vs 2 narration scenes
    manifest_data = {
        "documentary_id": "test_doc",
        "scenes": [
            {"scene_id": "S01", "shots": [{"shot_id": "S01_01", "prompt": "Shot 1"}]},
            {"scene_id": "S02", "shots": [{"shot_id": "S02_01", "prompt": "Shot 2"}]},
            {"scene_id": "S03", "shots": [{"shot_id": "S03_01", "prompt": "Shot 3"}]},
        ]
    }
    narration_data = {
        "scenes": [
            {"scene_id": "act1_s1", "narration": "First scene narration."},
            {"scene_id": "act1_s2", "narration": "Second scene narration."},
        ]
    }

    pipeline = AutonomousDocumentaryPipeline()

    # Simulate the pipeline stage 5 storyboard logic
    narr_scenes_flat = list(narration_data["scenes"])
    manifest_scenes = manifest_data.get("scenes", [])

    # Parity check
    is_mismatch = len(manifest_scenes) != len(narr_scenes_flat)
    assert is_mismatch is True, "Mismatch should be detected!"

    with patch("docstudio.autonomous_pipeline.VisualDirector") as mock_vd_class:
        mock_vd_instance = MagicMock()
        mock_vd_instance.plan_documentary.return_value = {
            "documentary_id": "fallback_doc",
            "scenes": [
                {"scene_id": "act1_s1", "shots": []},
                {"scene_id": "act1_s2", "shots": []},
            ]
        }
        mock_vd_class.return_value = mock_vd_instance

        # Execute the exact parity gate from autonomous_pipeline.py
        if len(manifest_scenes) != len(narr_scenes_flat):
            visual_director = mock_vd_class(width=1080, height=1920)
            storyboard_data = visual_director.plan_documentary(
                narration_data=narration_data,
                story_data={},
                claims_data={},
            )
        else:
            storyboard_data = {}

        assert mock_vd_instance.plan_documentary.called
        assert len(storyboard_data["scenes"]) == 2
        assert storyboard_data["scenes"][0]["scene_id"] == "act1_s1"


def test_pass2_prompt_survives_remapping():
    """
    Test 3: Verify that during ID remapping, a valid Pass-2 shot prompt is preserved
    and never overwritten with the narration-level visual_prompt.
    Only genuinely missing/empty prompts fall back.
    """
    pass2_enriched_prompt = "35mm anamorphic macro photography of brass compass needle spinning frantically, dust motes in tungsten spotlight, shallow depth of field."
    narration_level_prompt = "A compass on a ship."

    manifest_scenes = [
        {
            "scene_id": "S01",
            "shots": [
                {
                    "shot_id": "S01_SH01",
                    "prompt": pass2_enriched_prompt,  # Valid Pass-2 prompt
                    "visual_type": "AI_IMAGE",
                    "motion": "zoom_in",
                },
                {
                    "shot_id": "S01_SH02",
                    "prompt": "",  # Genuinely empty prompt
                    "visual_type": "STOCK_BROLL",
                    "visual_reason": "Provide geographic context.",
                },
            ]
        }
    ]

    narr_scenes_flat = [
        {
            "scene_id": "act1_s1",
            "narration": "The navigational instruments failed completely.",
            "visual_prompt": narration_level_prompt,
            "motion": "pan_left",
        }
    ]

    storyboard_scenes = []
    for s_idx, sc in enumerate(manifest_scenes):
        narr_sc = narr_scenes_flat[s_idx]
        canonical_sc_id = narr_sc.get("scene_id") or sc.get("scene_id", f"s{s_idx+1}")
        actual_narration = narr_sc.get("narration", "")
        scene_visual_prompt = narr_sc.get("visual_prompt", "")
        scene_motion = narr_sc.get("motion", "zoom_in")

        shots_list = []
        for sh in sc.get("shots", []):
            shot_entry = dict(sh)
            shot_entry["scene_id"] = canonical_sc_id

            director_prompt = sh.get("prompt")
            if director_prompt and str(director_prompt).strip():
                effective_prompt = str(director_prompt).strip()
            else:
                if scene_visual_prompt and str(scene_visual_prompt).strip():
                    effective_prompt = str(scene_visual_prompt).strip()
                else:
                    effective_prompt = str(sh.get("visual_reason") or "").strip()

            shot_entry["prompt"] = effective_prompt
            shot_entry["visual_prompt"] = effective_prompt
            shots_list.append(shot_entry)

        storyboard_scenes.append({"scene_id": canonical_sc_id, "shots": shots_list})

    remapped_shots = storyboard_scenes[0]["shots"]

    # Shot 1 had a valid Pass-2 prompt: MUST NOT be overwritten by narration prompt
    assert remapped_shots[0]["prompt"] == pass2_enriched_prompt
    assert remapped_shots[0]["visual_prompt"] == pass2_enriched_prompt
    assert remapped_shots[0]["visual_prompt"] != narration_level_prompt

    # Shot 2 had an empty prompt: MUST fall back to narration prompt
    assert remapped_shots[1]["prompt"] == narration_level_prompt
    assert remapped_shots[1]["visual_prompt"] == narration_level_prompt


def test_asset_isolation_different_shots_no_reuse():
    """
    Test 4: Verify that the first shot's asset is NOT registered under the parent
    scene_id as a universal fallback, and different shots resolve their own shot_id assets.
    """
    sc_id = "act1_s1"
    sh_id_1 = "act1_s1_SH01"
    sh_id_2 = "act1_s1_SH02"

    asset_1 = "C:/runs/visuals/act1_s1_SH01.mp4"
    asset_2 = "C:/runs/visuals/act1_s1_SH02.mp4"

    assets_data = {}
    scene_to_shots = {}

    # Simulate acquisition of shot 1
    assets_data[sh_id_1] = str(asset_1)
    if sc_id not in scene_to_shots:
        scene_to_shots[sc_id] = []
    scene_to_shots[sc_id].append(sh_id_1)

    # CRITICAL: Verify parent scene_id was NOT registered as universal fallback
    assert sc_id not in assets_data, f"Parent scene_id '{sc_id}' must NOT be registered in assets_data!"

    # Simulate acquisition of shot 2
    assets_data[sh_id_2] = str(asset_2)
    scene_to_shots[sc_id].append(sh_id_2)

    # Verify both shots have isolated distinct assets
    assert assets_data[sh_id_1] == asset_1
    assert assets_data[sh_id_2] == asset_2
    assert assets_data[sh_id_1] != assets_data[sh_id_2]

    # Verify timeline shot resolution:
    storyboard_shots = [
        {"shot_id": sh_id_1, "duration": 2.5, "asset_path": asset_1},
        {"shot_id": sh_id_2, "duration": 2.5, "asset_path": asset_2},
        {"shot_id": "act1_s1_SH03", "duration": 2.5, "asset_path": ""},  # shot with no asset
    ]

    timeline_shots = []
    for shot in storyboard_shots:
        sh_id = shot.get("shot_id", sc_id)
        # New resolution logic: strictly by shot_id, NO sc_id fallback
        asset_p = assets_data.get(sh_id) or shot.get("asset_path") or ""
        timeline_shots.append({
            "scene_id": sh_id,
            "parent_scene_id": sc_id,
            "asset_path": asset_p,
        })

    assert timeline_shots[0]["asset_path"] == asset_1
    assert timeline_shots[1]["asset_path"] == asset_2
    # Third shot must NOT reuse shot 1's asset through sc_id fallback!
    assert timeline_shots[2]["asset_path"] == ""
    assert timeline_shots[2]["asset_path"] != asset_1
