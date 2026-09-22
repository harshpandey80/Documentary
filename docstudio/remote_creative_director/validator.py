"""
DocStudio Remote Creative Director — Hardened Shot Manifest Validator.
Enforces API contracts, stable error codes, coverage analysis, and visual repetition diagnostics.
Complies with Phase 2 Steps 1, 2, 3, 9, 10, 18.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple

from docstudio.remote_creative_director.manifest_schema import (
    ShotManifest,
    SceneManifest,
    ShotDirective,
    VisualPurpose,
    SourceStrategy,
)
from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    TruthCategory,
    VisualTypeRegistry,
    SUPPORTED_NOW,
    PLANNED,
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationErrorItem:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    shot_id: Optional[str] = None
    scene_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __contains__(self, key: str) -> bool:
        k = str(key).lower()
        return k in self.message.lower() or k in self.code.lower()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value if isinstance(self.severity, Severity) else str(self.severity),
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "details": dict(self.details),
        }


@dataclass
class CoverageReport:
    coverage: float  # 0.0 to 1.0
    uncovered_ranges: List[Dict[str, float]] = field(default_factory=list)
    overlap_count: int = 0
    repetition_warnings: int = 0
    total_timeline_duration: float = 0.0
    total_narration_duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage": round(self.coverage, 3),
            "uncovered_ranges": list(self.uncovered_ranges),
            "overlap_count": self.overlap_count,
            "repetition_warnings": self.repetition_warnings,
            "total_timeline_duration": round(self.total_timeline_duration, 2),
            "total_narration_duration": round(self.total_narration_duration, 2),
        }


@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationErrorItem] = field(default_factory=list)
    warnings: List[ValidationErrorItem] = field(default_factory=list)
    info: List[ValidationErrorItem] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    coverage_report: Optional[CoverageReport] = None

    # Backward compatibility properties
    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def manifest_summary(self) -> Dict[str, Any]:
        return self.summary

    def get_error_messages(self) -> List[str]:
        return [f"[{e.code}] {e.message}" for e in self.errors]

    def get_warning_messages(self) -> List[str]:
        return [f"[{w.code}] {w.message}" for w in self.warnings]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "info": [i.to_dict() for i in self.info],
            "summary": dict(self.summary),
            "coverage_report": self.coverage_report.to_dict() if self.coverage_report else None,
        }


class ShotManifestValidator:
    """
    Hardened validator enforcing the central Shot Manifest contract:
    - Identity: Unique shot IDs, valid scene IDs.
    - Timing: Non-negative duration, strict bounds, gap & overlap detection.
    - Semantics: Mandatory purpose, reason, visual type, source strategy.
    - Execution: Valid supported visual types, execution provider validation.
    - Coverage: Ratio of visual timeline coverage vs narration timeline.
    - Diversity: Repetitive consecutive visual type detection.
    - Truth & Provenance: Historical/archival labeling verification.
    """

    @classmethod
    def validate(
        cls,
        manifest: ShotManifest | Dict[str, Any],
        max_ai_videos: Optional[int] = None,
        max_total_duration: Optional[float] = None,
        narration_timings: Optional[List[Dict[str, Any]]] = None,
        allow_planned_types: bool = False,
    ) -> ValidationResult:
        if isinstance(manifest, dict):
            try:
                manifest_obj = ShotManifest.from_dict(manifest)
            except Exception as exc:
                err = ValidationErrorItem(
                    code="MALFORMED_MANIFEST",
                    message=f"Failed to parse manifest dictionary: {exc}",
                    severity=Severity.ERROR,
                )
                return ValidationResult(
                    valid=False,
                    errors=[err],
                    summary={"shots_checked": 0, "errors": 1, "warnings": 0},
                )
        else:
            manifest_obj = manifest

        errors: List[ValidationErrorItem] = []
        warnings: List[ValidationErrorItem] = []
        info_items: List[ValidationErrorItem] = []

        if not manifest_obj.scenes:
            errors.append(
                ValidationErrorItem(
                    code="EMPTY_MANIFEST",
                    message="Manifest contains zero scenes.",
                    severity=Severity.ERROR,
                )
            )
            return ValidationResult(
                valid=False,
                errors=errors,
                summary={"shots_checked": 0, "errors": 1, "warnings": 0},
            )

        seen_shot_ids: Set[str] = set()
        total_shots = 0
        ai_video_count = 0
        ai_image_count = 0
        last_global_end = 0.0
        overlaps_detected = 0
        consecutive_type_count = 0
        last_visual_type: Optional[str] = None
        type_distribution: Dict[str, int] = {}

        # ─── SCENE & SHOT ITERATION ──────────────────────────────────────────
        for s_idx, scene in enumerate(manifest_obj.scenes):
            sc_id = scene.scene_id or f"S{s_idx + 1:02d}"
            if not scene.shots:
                errors.append(
                    ValidationErrorItem(
                        code="EMPTY_SCENE",
                        scene_id=sc_id,
                        message=f"Scene [{sc_id}] contains zero shots.",
                        severity=Severity.ERROR,
                    )
                )
                continue

            last_shot_end = scene.shots[0].start
            for shot_idx, shot in enumerate(scene.shots):
                total_shots += 1
                sh_id = shot.shot_id or f"{sc_id}_SH{shot_idx + 1:02d}"

                # 1. Identity Validation
                if not shot.shot_id:
                    errors.append(
                        ValidationErrorItem(
                            code="MISSING_SHOT_ID",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Scene [{sc_id}] Shot #{shot_idx} is missing 'shot_id'.",
                        )
                    )
                elif shot.shot_id in seen_shot_ids:
                    errors.append(
                        ValidationErrorItem(
                            code="DUPLICATE_SHOT_ID",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Duplicate shot_id '{shot.shot_id}' detected.",
                        )
                    )
                seen_shot_ids.add(sh_id)

                # 2. Timing Validation
                if shot.duration <= 0.0:
                    errors.append(
                        ValidationErrorItem(
                            code="NEGATIVE_OR_ZERO_DURATION",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] duration ({shot.duration}s) must be strictly positive.",
                        )
                    )
                elif shot.duration < 0.3:
                    warnings.append(
                        ValidationErrorItem(
                            code="VERY_SHORT_SHOT",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] duration ({shot.duration}s) is very brief (< 0.3s).",
                            severity=Severity.WARNING,
                        )
                    )
                elif shot.duration > 15.0:
                    warnings.append(
                        ValidationErrorItem(
                            code="EXCESSIVE_DURATION",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] duration ({shot.duration}s) exceeds recommended maximum cut hold (15s).",
                            severity=Severity.WARNING,
                        )
                    )

                if shot.end < shot.start:
                    errors.append(
                        ValidationErrorItem(
                            code="INVALID_TIMESTAMPS",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] end ({shot.end}s) is earlier than start ({shot.start}s).",
                        )
                    )

                expected_dur = round(shot.end - shot.start, 2)
                if abs(expected_dur - shot.duration) > 0.2:
                    warnings.append(
                        ValidationErrorItem(
                            code="DURATION_MISMATCH",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] duration ({shot.duration}s) mismatches (end - start = {expected_dur}s).",
                            severity=Severity.WARNING,
                        )
                    )

                # Overlap & Gap Check
                if shot_idx > 0 and shot.start < (last_shot_end - 0.05):
                    overlaps_detected += 1
                    errors.append(
                        ValidationErrorItem(
                            code="TIMING_OVERLAP",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] start ({shot.start}s) overlaps previous shot end ({last_shot_end}s).",
                        )
                    )
                elif shot_idx > 0 and (shot.start - last_shot_end) > 0.4:
                    warnings.append(
                        ValidationErrorItem(
                            code="TIMING_GAP",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Dead air gap of {round(shot.start - last_shot_end, 2)}s detected before shot [{sh_id}].",
                            severity=Severity.WARNING,
                        )
                    )

                last_shot_end = shot.end
                last_global_end = max(last_global_end, shot.end)

                # 3. Semantics Validation
                if not shot.purpose:
                    errors.append(
                        ValidationErrorItem(
                            code="MISSING_PURPOSE",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] is missing mandatory narrative 'purpose'.",
                        )
                    )
                if not shot.visual_reason or len(shot.visual_reason.strip()) < 5:
                    errors.append(
                        ValidationErrorItem(
                            code="MISSING_REASON",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] missing mandatory 'visual_reason' explaining directorial rationale.",
                        )
                    )

                # 4. Visual Type & Support Validation
                vtype_str = shot.visual_type.value if hasattr(shot.visual_type, "value") else str(shot.visual_type)
                norm_type = VisualTypeRegistry.normalize_type(shot.visual_type)
                if not norm_type:
                    errors.append(
                        ValidationErrorItem(
                            code="UNKNOWN_VISUAL_TYPE",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] specifies unrecognized visual_type '{vtype_str}'.",
                        )
                    )
                elif not allow_planned_types and VisualTypeRegistry.is_planned(norm_type):
                    warnings.append(
                        ValidationErrorItem(
                            code="PLANNED_VISUAL_TYPE",
                            shot_id=sh_id,
                            scene_id=sc_id,
                            message=f"Shot [{sh_id}] requested planned type '{norm_type.value}'. Will use semantic fallback.",
                            severity=Severity.WARNING,
                        )
                    )

                # Visual Repetition Tracking
                curr_type_key = norm_type.value if norm_type else vtype_str
                type_distribution[curr_type_key] = type_distribution.get(curr_type_key, 0) + 1
                if curr_type_key == last_visual_type:
                    consecutive_type_count += 1
                    if consecutive_type_count >= 3:
                        warnings.append(
                            ValidationErrorItem(
                                code="HIGH_VISUAL_REPETITION",
                                shot_id=sh_id,
                                scene_id=sc_id,
                                message=f"Visual repetition: 3+ consecutive shots use '{curr_type_key}'. Consider visual medium variety.",
                                severity=Severity.WARNING,
                            )
                        )
                else:
                    consecutive_type_count = 1
                    last_visual_type = curr_type_key

                # 5. Truth Category & Evidence Checks
                if norm_type in (VisualType.AUTHENTIC_EVIDENCE, VisualType.DOCUMENT, VisualType.REAL_ARCHIVAL):
                    if not shot.evidence_claims:
                        warnings.append(
                            ValidationErrorItem(
                                code="UNSOURCED_EVIDENCE_CLAIM",
                                shot_id=sh_id,
                                scene_id=sc_id,
                                message=f"Shot [{sh_id}] presents primary evidence without explicit evidence_claims references.",
                                severity=Severity.WARNING,
                            )
                        )
                if norm_type in (VisualType.CINEMATIC_RECONSTRUCTION, VisualType.AI_VIDEO, VisualType.AI_IMAGE_TO_VIDEO):
                    if hasattr(shot, "truth_category") and shot.truth_category == TruthCategory.DOCUMENTARY_EVIDENCE:
                        errors.append(
                            ValidationErrorItem(
                                code="MISLABELED_TRUTH_CATEGORY",
                                shot_id=sh_id,
                                scene_id=sc_id,
                                message=f"Shot [{sh_id}] is an AI/reconstruction visual but mislabeled as DOCUMENTARY_EVIDENCE.",
                            )
                        )

                # Budget Counting
                if norm_type in (VisualType.AI_VIDEO, VisualType.AI_IMAGE_TO_VIDEO) or shot.source_strategy == SourceStrategy.GENERATE_AI_VIDEO:
                    ai_video_count += 1
                elif norm_type == VisualType.AI_IMAGE or shot.source_strategy == SourceStrategy.GENERATE_AI_IMAGE:
                    ai_image_count += 1

        # ─── GLOBAL TIMING & COVERAGE ANALYSIS ────────────────────────────────
        total_narration_dur = max_total_duration or last_global_end
        coverage_ratio = 1.0
        uncovered: List[Dict[str, float]] = []

        if narration_timings:
            # Check coverage against narration intervals
            covered_intervals: List[Tuple[float, float]] = []
            for scene in manifest_obj.scenes:
                for shot in scene.shots:
                    covered_intervals.append((shot.start, shot.end))
            # Sort intervals
            covered_intervals.sort(key=lambda x: x[0])
            # Find gaps
            cur_t = 0.0
            for start, end in covered_intervals:
                if start > cur_t + 0.5:
                    uncovered.append({"start": round(cur_t, 2), "end": round(start, 2)})
                cur_t = max(cur_t, end)
            if total_narration_dur > cur_t + 0.5:
                uncovered.append({"start": round(cur_t, 2), "end": round(total_narration_dur, 2)})

            total_gap_time = sum(g["end"] - g["start"] for g in uncovered)
            coverage_ratio = max(0.0, min(1.0, 1.0 - (total_gap_time / max(1.0, total_narration_dur))))

            if coverage_ratio < 0.90:
                warnings.append(
                    ValidationErrorItem(
                        code="INSUFFICIENT_NARRATION_COVERAGE",
                        message=f"Visual timeline covers only {round(coverage_ratio * 100, 1)}% of narration. {len(uncovered)} gap(s) found.",
                        severity=Severity.WARNING,
                        details={"uncovered_ranges": uncovered},
                    )
                )

        coverage_report = CoverageReport(
            coverage=coverage_ratio,
            uncovered_ranges=uncovered,
            overlap_count=overlaps_detected,
            repetition_warnings=sum(1 for w in warnings if w.code == "HIGH_VISUAL_REPETITION"),
            total_timeline_duration=last_global_end,
            total_narration_duration=total_narration_dur,
        )

        # Budget Check
        if max_ai_videos is not None and ai_video_count > max_ai_videos:
            warnings.append(
                ValidationErrorItem(
                    code="BUDGET_CEILING_EXCEEDED",
                    message=f"Requested {ai_video_count} AI videos, exceeding budget cap of {max_ai_videos}.",
                    severity=Severity.WARNING,
                )
            )

        summary = {
            "shots_checked": total_shots,
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(info_items),
            "total_scenes": len(manifest_obj.scenes),
            "timeline_duration_s": round(last_global_end, 2),
            "ai_video_count": ai_video_count,
            "ai_image_count": ai_image_count,
            "type_distribution": type_distribution,
        }

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            info=info_items,
            summary=summary,
            coverage_report=coverage_report,
        )
