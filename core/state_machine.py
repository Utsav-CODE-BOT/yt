"""State Machine for Autonomous Faceless Shorts Factory.

Implements the 17 persistent pipeline states, valid transition rules,
failure handling, and restart recovery logic.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("factory.state_machine")


class PipelineState(str, Enum):
    """The 17 non-negotiable pipeline states defined in system architecture."""
    IDLE = "IDLE"
    TOPIC_DISCOVERY = "TOPIC_DISCOVERY"
    TOPIC_SELECTION = "TOPIC_SELECTION"
    RESEARCH = "RESEARCH"
    SCRIPT_GENERATION = "SCRIPT_GENERATION"
    SCRIPT_VALIDATION = "SCRIPT_VALIDATION"
    VOICE_GENERATION = "VOICE_GENERATION"
    CAPTION_ALIGNMENT = "CAPTION_ALIGNMENT"
    SCENE_PLANNING = "SCENE_PLANNING"
    VIDEO_RENDERING = "VIDEO_RENDERING"
    QUALITY_CONTROL = "QUALITY_CONTROL"
    APPROVAL = "APPROVAL"
    UPLOADING = "UPLOADING"
    UPLOAD_VERIFICATION = "UPLOAD_VERIFICATION"
    CLEANUP = "CLEANUP"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# Valid linear progression and fallback transitions
VALID_TRANSITIONS: Dict[PipelineState, Set[PipelineState]] = {
    PipelineState.IDLE: {PipelineState.TOPIC_DISCOVERY, PipelineState.FAILED},
    PipelineState.TOPIC_DISCOVERY: {PipelineState.TOPIC_SELECTION, PipelineState.FAILED},
    PipelineState.TOPIC_SELECTION: {PipelineState.RESEARCH, PipelineState.FAILED},
    PipelineState.RESEARCH: {PipelineState.SCRIPT_GENERATION, PipelineState.TOPIC_SELECTION, PipelineState.FAILED},
    PipelineState.SCRIPT_GENERATION: {PipelineState.SCRIPT_VALIDATION, PipelineState.FAILED},
    PipelineState.SCRIPT_VALIDATION: {PipelineState.VOICE_GENERATION, PipelineState.SCRIPT_GENERATION, PipelineState.FAILED},
    PipelineState.VOICE_GENERATION: {PipelineState.CAPTION_ALIGNMENT, PipelineState.SCRIPT_GENERATION, PipelineState.FAILED},
    PipelineState.CAPTION_ALIGNMENT: {PipelineState.SCENE_PLANNING, PipelineState.VOICE_GENERATION, PipelineState.FAILED},
    PipelineState.SCENE_PLANNING: {PipelineState.VIDEO_RENDERING, PipelineState.FAILED},
    PipelineState.VIDEO_RENDERING: {PipelineState.QUALITY_CONTROL, PipelineState.SCENE_PLANNING, PipelineState.COMPLETED, PipelineState.FAILED},
    PipelineState.QUALITY_CONTROL: {PipelineState.APPROVAL, PipelineState.VIDEO_RENDERING, PipelineState.FAILED},
    PipelineState.APPROVAL: {PipelineState.UPLOADING, PipelineState.FAILED},
    PipelineState.UPLOADING: {PipelineState.UPLOAD_VERIFICATION, PipelineState.FAILED},
    PipelineState.UPLOAD_VERIFICATION: {PipelineState.CLEANUP, PipelineState.UPLOADING, PipelineState.FAILED},
    PipelineState.CLEANUP: {PipelineState.COMPLETED, PipelineState.FAILED},
    PipelineState.COMPLETED: {PipelineState.IDLE},
    PipelineState.FAILED: set(PipelineState),
}


class StateMachineError(Exception):
    """Raised when an illegal transition is requested."""
    pass


class JobStateMachine:
    """Manages state transitions and validation for a single pipeline job."""

    def __init__(self, job_id: str, current_state: PipelineState = PipelineState.IDLE):
        self.job_id = job_id
        self._current_state = current_state

    @property
    def current_state(self) -> PipelineState:
        return self._current_state

    def can_transition_to(self, new_state: PipelineState) -> bool:
        """Check if transition from current state to new_state is permissible."""
        valid_targets = VALID_TRANSITIONS.get(self._current_state, set())
        return new_state in valid_targets

    def transition_to(self, new_state: PipelineState | str, reason: str = "") -> PipelineState:
        """Transition to a new state if valid."""
        if isinstance(new_state, str):
            try:
                new_state = PipelineState(new_state)
            except ValueError:
                raise StateMachineError(f"Unknown state string '{new_state}' for job {self.job_id}")

        if new_state == self._current_state:
            return self._current_state

        if not self.can_transition_to(new_state):
            msg = f"Illegal transition for job {self.job_id}: {self._current_state.value} -> {new_state.value} ({reason})"
            logger.error(msg)
            raise StateMachineError(msg)

        old_state = self._current_state
        self._current_state = new_state
        logger.info("Job %s transitioned: %s -> %s [%s]", self.job_id, old_state.value, new_state.value, reason)
        return self._current_state

    @staticmethod
    def determine_resume_state(last_recorded_state: str, has_upload_verified: bool = False, has_rendered_video: bool = False) -> PipelineState:
        """Determines safe resumption point following unexpected shutdown/restart."""
        try:
            state = PipelineState(last_recorded_state)
        except ValueError:
            return PipelineState.IDLE

        if state == PipelineState.COMPLETED:
            return PipelineState.COMPLETED

        # Guard against duplicate uploads
        if has_upload_verified:
            return PipelineState.CLEANUP

        # If upload was in progress, we verify before re-uploading
        if state in (PipelineState.UPLOADING, PipelineState.UPLOAD_VERIFICATION):
            return PipelineState.UPLOAD_VERIFICATION

        # If video was rendered, we resume at quality control
        if state in (PipelineState.QUALITY_CONTROL, PipelineState.APPROVAL):
            return state

        if has_rendered_video:
            return PipelineState.QUALITY_CONTROL

        # Otherwise resume from the last known state
        return state
