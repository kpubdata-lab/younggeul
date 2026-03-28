from datetime import date, datetime
from typing import ClassVar, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RunMeta(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    run_id: str
    run_name: str
    created_at: datetime
    model_id: str
    config_hash: str | None = None


class SnapshotRef(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    dataset_snapshot_id: str
    created_at: datetime
    table_count: int

    @field_validator("dataset_snapshot_id")
    @classmethod
    def validate_dataset_snapshot_id(cls, value: str) -> str:
        if len(value) != 64:
            raise ValueError("dataset_snapshot_id must be exactly 64 hex characters")
        if any(character not in "0123456789abcdefABCDEF" for character in value):
            raise ValueError("dataset_snapshot_id must be hex")
        return value


class Shock(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    shock_type: Literal["interest_rate", "regulation", "supply", "demand", "external"]
    description: str
    magnitude: float
    target_segments: list[str] = Field(default_factory=list)

    @field_validator("magnitude")
    @classmethod
    def validate_magnitude(cls, value: float) -> float:
        if not -1.0 <= value <= 1.0:
            raise ValueError("magnitude must be between -1.0 and 1.0")
        return value


class ScenarioSpec(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    scenario_name: str
    target_gus: list[str]
    target_period_start: date
    target_period_end: date
    shocks: list[Shock] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_target_period(self) -> "ScenarioSpec":
        if self.target_period_end < self.target_period_start:
            raise ValueError("target_period_end must be greater than or equal to target_period_start")
        return self


class SegmentState(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    gu_code: str
    gu_name: str
    current_median_price: int
    current_volume: int
    price_trend: Literal["up", "down", "flat"]
    sentiment_index: float
    supply_pressure: float

    @field_validator("sentiment_index")
    @classmethod
    def validate_sentiment_index(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("sentiment_index must be between 0.0 and 1.0")
        return value

    @field_validator("supply_pressure")
    @classmethod
    def validate_supply_pressure(cls, value: float) -> float:
        if not -1.0 <= value <= 1.0:
            raise ValueError("supply_pressure must be between -1.0 and 1.0")
        return value


class ParticipantState(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    participant_id: str
    role: Literal["buyer", "investor", "tenant", "landlord", "broker"]
    capital: int
    holdings: int
    sentiment: Literal["bullish", "bearish", "neutral"]
    risk_tolerance: float

    @field_validator("risk_tolerance")
    @classmethod
    def validate_risk_tolerance(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("risk_tolerance must be between 0.0 and 1.0")
        return value


class ActionProposal(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    round_no: int
    action_type: Literal["buy", "sell", "hold", "rent_out", "regulate", "adjust_rate"]
    target_segment: str
    confidence: float
    reasoning_summary: str
    proposed_value: dict[str, object] | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class RoundOutcome(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    round_no: int
    cleared_volume: dict[str, int]
    price_changes: dict[str, float]
    governance_applied: list[str]
    market_actions_resolved: int


class ReportClaim(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    claim_id: str
    claim_json: dict[str, object]
    evidence_ids: list[str]
    gate_status: Literal["pending", "passed", "failed", "repaired"] = "pending"
    repair_count: int = 0

    @field_validator("repair_count")
    @classmethod
    def validate_repair_count(cls, value: int) -> int:
        if value > 2:
            raise ValueError("repair_count must be less than or equal to 2")
        return value


class SimulationState(TypedDict):
    run_meta: RunMeta
    snapshot: SnapshotRef
    scenario: ScenarioSpec
    round_no: int
    max_rounds: int
    world: dict[str, SegmentState]
    participants: dict[str, ParticipantState]
    governance_actions: dict[str, ActionProposal]
    market_actions: dict[str, ActionProposal]
    last_outcome: RoundOutcome | None
    event_refs: list[str]
    evidence_refs: list[str]
    report_claims: list[ReportClaim]
    warnings: list[str]
