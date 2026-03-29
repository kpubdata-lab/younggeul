"""Round-loop continuation gate for simulation execution."""

from __future__ import annotations

from typing import Literal

from ..graph_state import SimulationGraphState


def should_continue(state: SimulationGraphState) -> Literal["continue", "stop"]:
    """Determine whether the simulation should proceed to another round.

    Args:
        state: Current simulation graph state.

    Returns:
        ``"continue"`` when another round should run, otherwise ``"stop"``.
    """
    round_no = state.get("round_no", 0)
    max_rounds = state.get("max_rounds", 3)

    if round_no >= max_rounds:
        return "stop"

    last_outcome = state.get("last_outcome")
    if last_outcome is not None and last_outcome.market_actions_resolved == 0:
        return "stop"

    return "continue"
