"""Protocol definition for participant action policies."""

from __future__ import annotations

# pyright: reportMissingImports=false

from typing import Protocol, runtime_checkable

from younggeul_core.state.simulation import ActionProposal, ParticipantState

from ..schemas.round import DecisionContext


@runtime_checkable
class ParticipantPolicy(Protocol):
    """Interface for role-specific participant decision policies."""

    def decide(self, participant: ParticipantState, context: DecisionContext) -> ActionProposal:
        """Return an action proposal for a participant in context.

        Args:
            participant: Participant state to decide for.
            context: Round decision context.

        Returns:
            Proposed participant action.
        """

        ...
