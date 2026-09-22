"""
Higgsfield AI Prompt Engineering Engine (inspired by OSideMedia/higgsfield-ai-prompt-skill)
Implements the MCSLA Formula (Model, Camera, Subject, Look, Action) with 18 cinematic
camera motion presets, vintage film stock emulation, and documentary lighting schemas
tailored for high-end AI video diffusion models (Wan2.1, Kling, Luma, Runway Gen-3, Sora 2, Veo).
"""

from __future__ import annotations
import random
from typing import Dict, Any, List

# 18 Verified Cinematic Camera Motion Presets
CAMERA_PRESETS = [
    {"name": "Slow Push-In", "code": "slow_dolly_in", "prompt": "slow dramatic forward push-in, low 24mm wide angle, shallow depth of field"},
    {"name": "Slow Pull-Back", "code": "slow_dolly_out", "prompt": "slow dramatic pull-back revealing grand scale, 35mm lens"},
    {"name": "Cinematic Orbit 360", "code": "orbit_360", "prompt": "smooth circular 360 degree orbit around focal subject, stabilized gimbal"},
    {"name": "Crane High to Low", "code": "crane_down", "prompt": "majestic high-altitude crane down descending into intimate street level view"},
    {"name": "Crane Low to High", "code": "crane_up", "prompt": "dramatic low-angle crane booming upward into expansive cinematic sky shot"},
    {"name": "Tracking Lateral Follow", "code": "tracking_lateral", "prompt": "smooth lateral tracking shot moving parallel to the motion, cinematic parallax"},
    {"name": "Rack Focus Macro", "code": "rack_focus", "prompt": "extreme macro shallow depth of field with slow rack focus from foreground element to background subject"},
    {"name": "Aerial Top-Down Flyover", "code": "aerial_top_down", "prompt": "birds-eye-view 90 degree straight down aerial flyover, subtle forward drift"},
    {"name": "Dutch Angle Slow Creep", "code": "dutch_angle_creep", "prompt": "unsettling subtle dutch angle tilt with slow creeping forward camera motion, psychological tension"},
    {"name": "Handheld Archival Shimmer", "code": "handheld_shimmer", "prompt": "authentic 16mm combat camera organic handheld micro-shake, gritty tactile motion"},
    {"name": "Whip Pan Transition", "code": "whip_pan", "prompt": "dynamic directional whip pan with cinematic motion blur snapping into sharp focus"},
    {"name": "FPV Low-Altitude Sweep", "code": "fpv_sweep", "prompt": "high-speed low-altitude terrain hugging flyover, cinematic motion blur on edges"},
    {"name": "Zolly / Vertigo Push-Pull", "code": "dolly_zoom", "prompt": "vertigo effect dolly zoom, background warps while subject size remains locked in frame"},
    {"name": "Slow Steadicam Glide", "code": "steadicam_glide", "prompt": "fluid steadicam glide through hallway or terrain, perfectly floating camera path"},
    {"name": "Macro Tilt-Shift Miniature", "code": "tilt_shift", "prompt": "tilt-shift optical blur, shallow horizontal focal band, high-angle miniature documentary look"},
    {"name": "Elevated 45-Degree Drifting Pan", "code": "elevated_drift", "prompt": "elevated 45-degree angle slow drifting pan across landscape and military formations"},
    {"name": "Over-The-Shoulder Push", "code": "ots_push", "prompt": "intimate over-the-shoulder perspective slowly pushing past silhouette into central action"},
    {"name": "Static Lockdown with Internal Motion", "code": "static_lockdown", "prompt": "locked-off tripod master shot with intense dynamic subject motion and atmospheric particle drift"},
]

# Documentary Film Stocks & Aesthetic Lighting Schemas
LOOK_SCHEMAS = [
    {
        "style": "1940s_combat_tri_x",
        "description": "archival 35mm Kodak Tri-X black and white film grain, high silver halide contrast, deep rich blacks, authentic emulsion scratches, soft vintage halation",
    },
    {
        "style": "technicolor_3_strip",
        "description": "vintage 1940s-1950s 3-strip Technicolor saturation, rich dye-transfer primary colors, warm amber highlights, authentic vintage newsreel print",
    },
    {
        "style": "chiaroscuro_tungsten",
        "description": "heavy chiaroscuro low-key lighting, single harsh tungsten bulb cutting through dense darkness, volumetric god-rays and drifting dust particles",
    },
    {
        "style": "modern_4k_cinematic",
        "description": "masterpiece 8k cinema, Arri Alexa Mini LF, Cooke anamorphic prime lenses, subtle oval bokeh, balanced golden hour rim lighting, clean color grade",
    },
    {
        "style": "declassified_forensic",
        "description": "forensic investigative aesthetic, cold desaturated slate blue and charcoal tones, high micro-contrast, clinical fluorescent lighting",
    },
    {
        "style": "battlefield_smoke_dawn",
        "description": "early dawn mist, rising cordite smoke, silhouetted silhouettes against pale orange horizon, atmospheric haze, heavy practical volumetric fog",
    },
]

class HiggsfieldPrompter:
    """
    Higgsfield MCSLA Prompt Builder for AI Video Models.
    Turns raw narrative cues into hyper-detailed director-level cinematic video prompts.
    """

    def __init__(self):
        self.camera_presets = CAMERA_PRESETS
        self.look_schemas = LOOK_SCHEMAS

    def build_mcsla_prompt(
        self,
        scene_description: str,
        topic: str,
        historical_era: str = "World War II",
        camera_override: str | None = None,
        look_override: str | None = None,
        negative_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Constructs a complete MCSLA prompt object:
        M = Model Directive
        C = Camera Movement & Lens
        S = Subject & Composition
        L = Look, Lighting & Film Stock
        A = Action & Atmospheric Physics
        """
        if camera_override:
            camera_preset = next((p for p in self.camera_presets if p["code"] == camera_override), random.choice(self.camera_presets))
        else:
            camera_preset = random.choice(self.camera_presets)

        if look_override:
            look_schema = next((l for l in self.look_schemas if l["style"] == look_override), random.choice(self.look_schemas))
        else:
            look_schema = random.choice(self.look_schemas)

        subject_core = f"{topic}: {scene_description}".strip()

        model_tag = "Cinematic 35mm Documentary Film"
        camera_str = camera_preset["prompt"]
        look_str = look_schema["description"]
        action_str = "photorealistic physics, dynamic motion, subtle organic micro-expressions, hyper-realistic atmospheric smoke and lighting interaction, 30fps smooth filmic cadence"

        unified_prompt = (
            f"A masterwork cinematic documentary shot of {subject_core}. "
            f"Camera: {camera_str}. "
            f"Visual Look: {look_str}. "
            f"Action: {action_str}. "
            f"Historical accuracy for {historical_era}, 8k resolution, award-winning cinematography."
        )

        neg_prompt = (
            "blurry, low resolution, 3d render, cartoon, deformed faces, bad anatomy, text watermarks, "
            "overexposed, glitchy temporal artifacts, plastic skin, jittery frame drops, oversaturated neon"
        )

        return {
            "prompt": unified_prompt,
            "negative_prompt": neg_prompt if negative_prompt else "",
            "camera_preset": camera_preset["name"],
            "camera_code": camera_preset["code"],
            "look_style": look_schema["style"],
            "mcsla": {
                "model": model_tag,
                "camera": camera_str,
                "subject": subject_core,
                "look": look_str,
                "action": action_str,
            }
        }

    def get_prompt_for_scene(self, scene: Dict[str, Any], topic: str) -> str:
        """Helper to get a prompt string directly from a script scene object."""
        narration = scene.get("narration", "")
        visual_desc = scene.get("visual_prompt") or scene.get("headline") or narration[:120]
        mcsla_obj = self.build_mcsla_prompt(
            scene_description=visual_desc,
            topic=topic,
        )
        return mcsla_obj["prompt"]
