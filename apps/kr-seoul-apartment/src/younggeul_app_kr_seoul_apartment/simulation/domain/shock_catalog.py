from __future__ import annotations

from typing import Literal, TypedDict

from younggeul_core.state.simulation import Shock


class _ShockTemplate(TypedDict):
    shock_type: Literal["interest_rate", "regulation", "supply", "demand", "external"]
    description: str
    magnitude: float


SUPPORTED_SHOCK_KEYS: dict[str, _ShockTemplate] = {
    "rate_up": {
        "shock_type": "interest_rate",
        "description": "Interest rate hike",
        "magnitude": 0.3,
    },
    "rate_down": {
        "shock_type": "interest_rate",
        "description": "Interest rate cut",
        "magnitude": -0.3,
    },
    "demand_surge": {
        "shock_type": "demand",
        "description": "Demand surge",
        "magnitude": 0.5,
    },
    "demand_drop": {
        "shock_type": "demand",
        "description": "Demand drop",
        "magnitude": -0.5,
    },
    "supply_increase": {
        "shock_type": "supply",
        "description": "Supply increase",
        "magnitude": 0.4,
    },
    "regulation_tighten": {
        "shock_type": "regulation",
        "description": "Tighter regulation",
        "magnitude": 0.4,
    },
    "regulation_loosen": {
        "shock_type": "regulation",
        "description": "Loosened regulation",
        "magnitude": -0.4,
    },
    "sentiment_drop": {
        "shock_type": "external",
        "description": "Market sentiment deterioration",
        "magnitude": -0.4,
    },
}

KOREAN_SHOCK_ALIASES: dict[str, str] = {
    "금리인상": "rate_up",
    "금리인하": "rate_down",
    "금리 인상": "rate_up",
    "금리 인하": "rate_down",
    "수요증가": "demand_surge",
    "수요감소": "demand_drop",
    "공급확대": "supply_increase",
    "공급 확대": "supply_increase",
    "규제강화": "regulation_tighten",
    "규제완화": "regulation_loosen",
    "규제 강화": "regulation_tighten",
    "규제 완화": "regulation_loosen",
    "심리위축": "sentiment_drop",
}


def normalize_shock_key(raw: str) -> str | None:
    candidate = raw.strip().lower()
    if candidate in SUPPORTED_SHOCK_KEYS:
        return candidate
    if candidate in KOREAN_SHOCK_ALIASES:
        return KOREAN_SHOCK_ALIASES[candidate]
    return None


def expand_shock(
    key: str,
    target_gus: list[str],
    start_period: str,
    end_period: str | None,
) -> Shock:
    del start_period
    del end_period
    template = SUPPORTED_SHOCK_KEYS[key]
    return Shock(
        shock_type=template["shock_type"],
        description=template["description"],
        magnitude=template["magnitude"],
        target_segments=list(target_gus),
    )
