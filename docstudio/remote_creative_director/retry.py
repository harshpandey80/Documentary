"""
DocStudio Remote Creative Director — Self-Healing Retry Loop.
If a generated ShotManifest fails validation (e.g. gaps, overlaps, missing purpose/reason),
this module formats the exact validation errors into a corrective prompt and instructs
the remote AI to fix only the defective elements.
"""

from __future__ import annotations
import json
from typing import Dict, Any, List
from docstudio.remote_creative_director.validator import ValidationResult


class ManifestRepairEngine:
    """
    Constructs targeted repair prompts for defective Shot Manifests.
    """

    @staticmethod
    def build_repair_prompt(
        defective_manifest: Dict[str, Any],
        validation_result: ValidationResult,
    ) -> str:
        errors_str = "\n".join(
            f"- [{getattr(e, 'code', 'ERROR')}] {getattr(e, 'message', str(e))}" for e in validation_result.errors
        )
        warnings_str = "\n".join(
            f"- [{getattr(w, 'code', 'WARNING')}] {getattr(w, 'message', str(w))}" for w in validation_result.warnings
        )

        return f"""The previous Shot Manifest failed strict structural validation.
CORRECT THE FOLLOWING ISSUES IMMEDIATELY:

VALIDATION ERRORS:
{errors_str}

WARNINGS:
{warnings_str}

ORIGINAL MANIFEST:
{json.dumps(defective_manifest, indent=2)}

REPAIR RULES:
1. Fix all timing overlaps, ensuring shot[i].start == shot[i-1].end.
2. Ensure EVERY shot includes:
   - "purpose": Valid purpose enum
   - "visual_type": Valid visual type
   - "visual_reason": Clear explanation of why this visual communicates the fact
   - "source_strategy": Valid execution strategy
3. Return the COMPLETE, repaired JSON Shot Manifest."""
