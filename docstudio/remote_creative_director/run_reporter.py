"""
DocStudio Remote Creative Director — Production Run Reporter.
Step 14 & 19: Generates machine-readable run reports and human-readable editorial summaries
for observability, QA auditing, and timeline diagnostics.
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from docstudio.remote_creative_director.manifest_schema import ShotManifest
from docstudio.remote_creative_director.validator import ValidationResult


class ProductionRunReporter:
    """
    Emits structured run metrics and editorial diagnostic logs.
    """

    @staticmethod
    def generate_report(
        run_id: str,
        topic: str,
        status: str,
        manifest: Optional[ShotManifest],
        validation_result: Optional[ValidationResult],
        router_stats: Optional[Dict[str, Any]] = None,
        final_video_path: Optional[Path] = None,
        execution_time_s: float = 0.0,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Creates and writes run_report.json and RUN_SUMMARY.md.
        """
        router_stats = router_stats or {}
        scenes_count = len(manifest.scenes) if manifest else 0
        shots_count = len(manifest.get_all_shots()) if manifest else 0

        cov_ratio = 1.0
        if validation_result and validation_result.coverage_report:
            cov_ratio = validation_result.coverage_report.coverage

        val_errors = len(validation_result.errors) if validation_result else 0
        val_warnings = len(validation_result.warnings) if validation_result else 0

        report = {
            "run_id": run_id,
            "topic": topic,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "execution_time_s": round(execution_time_s, 2),
            "scenes": scenes_count,
            "shots": shots_count,
            "coverage": round(cov_ratio, 3),
            "validation_errors": val_errors,
            "warnings": val_warnings,
            "cache_hits": router_stats.get("cache_hits", 0),
            "cache_misses": router_stats.get("cache_misses", 0),
            "fallbacks": router_stats.get("fallback_successes", 0),
            "failed_shots": router_stats.get("total_failures", 0),
            "output_video": str(final_video_path) if final_video_path and final_video_path.exists() else None,
            "video_size_bytes": final_video_path.stat().st_size if final_video_path and final_video_path.exists() else 0,
        }

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)

            # 1. JSON Report
            json_file = out_p / "run_report.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

            # 2. Human-Readable Editorial Summary
            md_file = out_p / "RUN_SUMMARY.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(ProductionRunReporter._build_markdown_summary(report, manifest, validation_result))

        return report

    @staticmethod
    def _build_markdown_summary(
        report: Dict[str, Any],
        manifest: Optional[ShotManifest],
        validation_result: Optional[ValidationResult],
    ) -> str:
        lines = [
            f"# Production Run Summary: {report['topic']}",
            f"- **Run ID**: `{report['run_id']}`",
            f"- **Status**: `{report['status'].upper()}`",
            f"- **Execution Time**: {report['execution_time_s']}s",
            f"- **Scenes / Shots**: {report['scenes']} scenes / {report['shots']} shots",
            f"- **Timeline Coverage**: {round(report['coverage'] * 100, 1)}%",
            f"- **Cache Hits / Misses**: {report['cache_hits']} / {report['cache_misses']}",
            f"- **Fallbacks Triggered**: {report['fallbacks']}",
            f"- **Output Video**: `{report['output_video']}` ({report['video_size_bytes']} bytes)",
            "",
            "## Directorial Manifest Breakdown",
            "",
            "| Shot ID | Timeline | Purpose | Visual Type | Directorial Rationale | Provider |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        if manifest:
            for sc in manifest.scenes:
                for sh in sc.shots:
                    reason = (sh.visual_reason or "").replace("|", "-")
                    lines.append(
                        f"| `{sh.shot_id}` | {sh.start:.1f}s - {sh.end:.1f}s ({sh.duration:.1f}s) | `{sh.purpose}` | `{sh.visual_type}` | {reason} | `{sh.generation_provider}` |"
                    )

        if validation_result and validation_result.warnings:
            lines.extend([
                "",
                "## Directorial Warnings",
                "",
            ])
            for w in validation_result.warnings:
                lines.append(f"- ⚠️ **[{w.code}]** {w.message}")

        return "\n".join(lines)
