"""Registry for resolving default participant policies by role."""

from __future__ import annotations

from .heuristic import BrokerPolicy, BuyerPolicy, InvestorPolicy, LandlordPolicy, TenantPolicy
from .protocol import ParticipantPolicy

_POLICY_MAP: dict[str, ParticipantPolicy] = {
    "buyer": BuyerPolicy(),
    "investor": InvestorPolicy(),
    "tenant": TenantPolicy(),
    "landlord": LandlordPolicy(),
    "broker": BrokerPolicy(),
}


def get_default_policy(role: str) -> ParticipantPolicy:
    """Return the default policy instance for a participant role.

    Args:
        role: Participant role key.

    Returns:
        Policy instance for the role.

    Raises:
        ValueError: When no default policy is registered for the role.
    """
    policy = _POLICY_MAP.get(role)
    if policy is None:
        raise ValueError(f"No default policy for role: {role}")
    return policy
