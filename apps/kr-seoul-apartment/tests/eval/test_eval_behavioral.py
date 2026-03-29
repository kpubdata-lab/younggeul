from __future__ import annotations

# pyright: reportMissingImports=false, reportMissingTypeStubs=false

from importlib import import_module
from typing import Protocol, TypedDict, cast

import pytest

from .conftest import load_all_eval_cases

event_store_module = import_module("younggeul_app_kr_seoul_apartment.simulation.event_store")
graph_module = import_module("younggeul_app_kr_seoul_apartment.simulation.graph")
graph_state_module = import_module("younggeul_app_kr_seoul_apartment.simulation.graph_state")
evidence_store_module = import_module("younggeul_app_kr_seoul_apartment.simulation.evidence.store")


class RunMetaLike(Protocol):
    run_id: str


class SegmentLike(Protocol):
    gu_code: str
    price_trend: str


class ParticipantLike(Protocol):
    role: str


class ClaimLike(Protocol):
    evidence_ids: list[str]
    claim_json: dict[str, object]


class EventLike(Protocol):
    event_type: str
    payload: dict[str, object]


class EvidenceRecordLike(Protocol):
    kind: str


class EventStoreLike(Protocol):
    def get_events(self, run_id: str) -> list[EventLike]: ...

    def get_events_by_type(self, run_id: str, event_type: str) -> list[EventLike]: ...


class EvidenceStoreLike(Protocol):
    def get(self, evidence_id: str) -> EvidenceRecordLike | None: ...

    def get_all(self) -> list[EvidenceRecordLike]: ...


class GraphLike(Protocol):
    def invoke(self, seed: dict[str, object]) -> FinalState: ...


class EventStoreFactoryLike(Protocol):
    def __call__(self) -> EventStoreLike: ...


class EvidenceStoreFactoryLike(Protocol):
    def __call__(self) -> EvidenceStoreLike: ...


class BuildSimulationGraphLike(Protocol):
    def __call__(
        self, event_store: EventStoreLike, *, evidence_store: EvidenceStoreLike | None = None
    ) -> GraphLike: ...


class SeedGraphStateLike(Protocol):
    def __call__(self, *, user_query: str, run_id: str, run_name: str, model_id: str) -> dict[str, object]: ...


class FinalState(TypedDict):
    run_meta: RunMetaLike
    round_no: int
    max_rounds: int
    world: dict[str, SegmentLike]
    participants: dict[str, ParticipantLike]
    event_refs: list[str]
    evidence_refs: list[str]
    report_claims: list[ClaimLike]


InMemoryEventStore = cast(EventStoreFactoryLike, event_store_module.InMemoryEventStore)
build_simulation_graph = cast(BuildSimulationGraphLike, graph_module.build_simulation_graph)
seed_graph_state = cast(SeedGraphStateLike, graph_state_module.seed_graph_state)
InMemoryEvidenceStore = cast(EvidenceStoreFactoryLike, evidence_store_module.InMemoryEvidenceStore)


def _run_with_stores(
    case: dict[str, object],
) -> tuple[FinalState, EventStoreLike, EvidenceStoreLike]:
    event_store = InMemoryEventStore()
    evidence_store = InMemoryEvidenceStore()
    graph = build_simulation_graph(event_store, evidence_store=evidence_store)
    seed = seed_graph_state(
        user_query=cast(str, case["query"]),
        run_id=cast(str, case["scenario_id"]),
        run_name=cast(str, case["run_name"]),
        model_id=cast(str, case["model_id"]),
    )
    seed["max_rounds"] = cast(int, case["max_rounds"])
    final = graph.invoke(seed)
    return final, event_store, evidence_store


def _claims_by_type(final: FinalState, claim_type: str) -> list[ClaimLike]:
    return [claim for claim in final["report_claims"] if claim.claim_json.get("type") == claim_type]


@pytest.mark.eval
class TestEvalBehavioral:
    def test_claim_types_coverage(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)

        claim_types = {cast(str, claim.claim_json["type"]) for claim in final["report_claims"]}
        required_types = {
            "simulation_overview",
            "direction",
            "volume",
            "participant_summary",
            "risk_factors",
        }

        assert required_types.issubset(claim_types)

    def test_evidence_count_scales_with_rounds(self) -> None:
        cases = load_all_eval_cases()
        by_id = {cast(str, case["scenario_id"]): case for case in cases}

        baseline_final, _, _ = _run_with_stores(cast(dict[str, object], by_id["seocho-0round-baseline"]))
        bull_final, _, _ = _run_with_stores(cast(dict[str, object], by_id["gangnam-2round-bull"]))
        stress_final, _, _ = _run_with_stores(cast(dict[str, object], by_id["gangnam-5round-stress"]))

        assert len(baseline_final["evidence_refs"]) < len(bull_final["evidence_refs"])
        assert len(bull_final["evidence_refs"]) <= len(stress_final["evidence_refs"])

    def test_participant_decisions_reflect_policy_for_round_cases(self, eval_case: dict[str, object]) -> None:
        if cast(int, eval_case["max_rounds"]) == 0:
            pytest.skip("No decision rounds when max_rounds=0")

        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id
        decision_events = event_store.get_events_by_type(run_id, "DECISIONS_MADE")

        assert decision_events, "Expected DECISIONS_MADE events for round scenarios"
        first_payload = decision_events[0].payload
        action_summary = cast(dict[str, dict[str, object]], first_payload["action_summary"])

        assert "p-001" in action_summary
        assert action_summary["p-001"]["action_type"] == "buy"
        assert any(details.get("action_type") == "buy" for details in action_summary.values())

    def test_zero_round_case_has_no_decision_events(self, eval_case: dict[str, object]) -> None:
        if cast(int, eval_case["max_rounds"]) != 0:
            pytest.skip("Only applies to the zero-round scenario")

        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id

        assert event_store.get_events_by_type(run_id, "DECISIONS_MADE") == []
        assert event_store.get_events_by_type(run_id, "ROUND_RESOLVED") == []

    def test_round_outcomes_have_non_negative_transactions(self, eval_case: dict[str, object]) -> None:
        if cast(int, eval_case["max_rounds"]) == 0:
            pytest.skip("No ROUND_RESOLVED events when max_rounds=0")

        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id

        for event in event_store.get_events_by_type(run_id, "ROUND_RESOLVED"):
            transactions_count = cast(int, event.payload["transactions_count"])
            assert transactions_count >= 0

    def test_round_outcomes_segment_deltas_subset_of_world(self, eval_case: dict[str, object]) -> None:
        if cast(int, eval_case["max_rounds"]) == 0:
            pytest.skip("No ROUND_RESOLVED events when max_rounds=0")

        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id
        world_keys = set(final["world"].keys())

        for event in event_store.get_events_by_type(run_id, "ROUND_RESOLVED"):
            segment_deltas = cast(dict[str, object], event.payload["segment_deltas"])
            assert set(segment_deltas.keys()).issubset(world_keys)

    def test_round_outcomes_nonzero_transactions_have_nonzero_price_change(
        self,
        eval_case: dict[str, object],
    ) -> None:
        if cast(int, eval_case["max_rounds"]) == 0:
            pytest.skip("No ROUND_RESOLVED events when max_rounds=0")

        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id

        for event in event_store.get_events_by_type(run_id, "ROUND_RESOLVED"):
            transactions_count = cast(int, event.payload["transactions_count"])
            segment_deltas = cast(dict[str, dict[str, object]], event.payload["segment_deltas"])

            if transactions_count > 0:
                assert any(cast(float, delta["price_change_pct"]) != 0.0 for delta in segment_deltas.values())

    def test_report_contains_expected_sections_and_keys(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        sections: set[str] = set()

        for claim in final["report_claims"]:
            payload = claim.claim_json
            for required_key in ("type", "section", "subject", "statement"):
                assert required_key in payload
            statement = cast(str, payload["statement"])
            assert statement.strip() != ""
            sections.add(cast(str, payload["section"]))

        required_sections = {"summary", "direction", "volume", "drivers", "risks"}
        assert required_sections.issubset(sections)

    def test_direction_claim_mentions_price_trend(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        direction_claims = _claims_by_type(final, "direction")

        assert direction_claims
        for claim in direction_claims:
            subject = cast(str, claim.claim_json["subject"])
            statement = cast(str, claim.claim_json["statement"]).lower()

            assert subject in final["world"]
            trend = final["world"][subject].price_trend
            assert trend in statement

    def test_overview_claim_has_correct_counts(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        overview_claims = _claims_by_type(final, "simulation_overview")

        assert len(overview_claims) == 1
        metrics = cast(dict[str, object], overview_claims[0].claim_json["metrics"])

        assert cast(int, metrics["segment_count"]) == len(final["world"])
        assert cast(int, metrics["participant_count"]) == len(final["participants"])
        assert cast(int, metrics["round_no"]) == final["round_no"]

    def test_volume_claim_has_numeric_metrics(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        volume_claims = _claims_by_type(final, "volume")

        assert volume_claims
        for claim in volume_claims:
            metrics = cast(dict[str, object], claim.claim_json["metrics"])
            assert isinstance(metrics.get("volume"), (int, float))
            assert isinstance(metrics.get("median_price"), (int, float))

    def test_participant_summary_claim_exists_for_each_role(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        expected_roles = {participant.role for participant in final["participants"].values()}

        summary_claims = _claims_by_type(final, "participant_summary")
        subjects = {cast(str, claim.claim_json["subject"]) for claim in summary_claims}

        for role in expected_roles:
            assert f"role:{role}" in subjects

    def test_exactly_one_risk_factors_claim_with_expected_metrics(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)
        risk_claims = _claims_by_type(final, "risk_factors")

        assert len(risk_claims) == 1
        claim = risk_claims[0]
        assert claim.claim_json["section"] == "risks"
        metrics = cast(dict[str, object], claim.claim_json["metrics"])
        assert "shock_count" in metrics
        assert "governance_actions" in metrics

    def test_event_count_formula(self, eval_case: dict[str, object]) -> None:
        final, event_store, _ = _run_with_stores(eval_case)
        run_id = final["run_meta"].run_id
        rounds = final["round_no"]
        events = event_store.get_events(run_id)

        expected_events = 8 + (2 * rounds)
        assert len(events) == expected_events

    def test_evidence_builder_produces_expected_kinds(self, eval_case: dict[str, object]) -> None:
        final, _, evidence_store = _run_with_stores(eval_case)
        kinds = {record.kind for record in evidence_store.get_all()}

        assert {"simulation_fact", "segment_fact", "participant_fact"}.issubset(kinds)
        if final["max_rounds"] > 0:
            assert "round_fact" in kinds

    def test_claims_per_segment_exactly_one_direction_and_volume(self, eval_case: dict[str, object]) -> None:
        final, _, _ = _run_with_stores(eval_case)

        for gu_code in final["world"]:
            direction_claims = [
                claim
                for claim in final["report_claims"]
                if claim.claim_json.get("type") == "direction" and claim.claim_json.get("subject") == gu_code
            ]
            volume_claims = [
                claim
                for claim in final["report_claims"]
                if claim.claim_json.get("type") == "volume" and claim.claim_json.get("subject") == gu_code
            ]

            assert len(direction_claims) == 1
            assert len(volume_claims) == 1
