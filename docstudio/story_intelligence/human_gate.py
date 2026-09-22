"""
docstudio/story_intelligence/human_gate.py
==========================================
Human Gate lifecycle management and status transitions (Section 22).
Enforces that machine passing only achieves READY_FOR_HUMAN_GATE.
Transition to APPROVED_FOR_CREATIVE_DIRECTOR requires explicit human approval.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional, Tuple

from docstudio.story_intelligence.models import MasterStoryOutput, StoryStatus


class HumanGateController:
    """Controls the mandatory editorial human gate."""

    @staticmethod
    def evaluate_machine_readiness(story: MasterStoryOutput) -> StoryStatus:
        """
        Determines the state of the story following machine lint and quality rubric.
        Passing all automated gates moves status strictly to READY_FOR_HUMAN_GATE.
        """
        # Check quality scores
        if not story.quality_scores.passed:
            story.status = StoryStatus.QUALITY_FAILED.value
            return StoryStatus.QUALITY_FAILED

        # Check hard lint results
        hard_failed = any(
            (not r.passed and r.classification == "HARD") for r in story.lint_results
        )
        if hard_failed:
            story.status = StoryStatus.LINT_FAILED.value
            return StoryStatus.LINT_FAILED

        # Passed all machine gates
        story.status = StoryStatus.READY_FOR_HUMAN_GATE.value
        return StoryStatus.READY_FOR_HUMAN_GATE

    @staticmethod
    def approve_for_creative_director(
        story: MasterStoryOutput,
        reviewer_name: str = "Chief Editor",
        notes: str = "Approved for visual manifestation.",
    ) -> Tuple[bool, str]:
        """
        Transitions status from READY_FOR_HUMAN_GATE to APPROVED_FOR_CREATIVE_DIRECTOR.
        """
        if story.status != StoryStatus.READY_FOR_HUMAN_GATE.value:
            return False, f"Cannot approve story in status '{story.status}'. Must be in READY_FOR_HUMAN_GATE."

        story.status = StoryStatus.APPROVED_FOR_CREATIVE_DIRECTOR.value
        story.human_approved = True
        timestamp = datetime.datetime.now().isoformat()
        story.human_notes = f"Approved by {reviewer_name} at {timestamp}. Notes: {notes}"
        print(f"[HumanGate] Story '{story.story_id}' successfully APPROVED for Creative Director by {reviewer_name}.")
        return True, story.status

    @staticmethod
    def request_human_revision(
        story: MasterStoryOutput,
        notes: str,
    ) -> StoryStatus:
        """Allows human editor to send story back for targeted rewrite."""
        story.status = StoryStatus.NEEDS_REWRITE.value
        story.human_approved = False
        story.human_notes = f"Revision requested: {notes}"
        return StoryStatus.NEEDS_REWRITE
