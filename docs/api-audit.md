# Docstring Coverage Audit Report

**Generated**: 2026-03-29
**Total files scanned**: 78
**Total public symbols**: 289

## Summary

| Metric | Count |
|--------|-------|
| ✅ Full docstring | 272 |
| ⚠️ Partial docstring | 17 |
| ❌ Missing docstring | 0 |
| **Total** | **289** |
| **Coverage (full)** | **94.1%** |
| **Coverage (full+partial)** | **100.0%** |

## Per-Module Breakdown

### Core (`younggeul_core`)

| Module | Total | ✅ Full | ⚠️ Partial | ❌ Missing | Coverage |
|--------|-------|---------|------------|------------|----------|
| `younggeul_core` | 1 | 1 | 0 | 0 | 100% |
| `core.agents` | 1 | 1 | 0 | 0 | 100% |
| `core.connectors` | 1 | 1 | 0 | 0 | 100% |
| `core.connectors.hashing` | 2 | 2 | 0 | 0 | 100% |
| `core.connectors.manifest` | 2 | 2 | 0 | 0 | 100% |
| `core.connectors.protocol` | 4 | 4 | 0 | 0 | 100% |
| `core.connectors.rate_limit` | 5 | 5 | 0 | 0 | 100% |
| `core.connectors.retry` | 4 | 4 | 0 | 0 | 100% |
| `core.evidence` | 1 | 1 | 0 | 0 | 100% |
| `core.evidence.schemas` | 9 | 9 | 0 | 0 | 100% |
| `core.evidence.sql` | 1 | 1 | 0 | 0 | 100% |
| `core.runtime` | 1 | 1 | 0 | 0 | 100% |
| `core.state` | 1 | 1 | 0 | 0 | 100% |
| `core.state.bronze` | 7 | 7 | 0 | 0 | 100% |
| `core.state.gold` | 5 | 5 | 0 | 0 | 100% |
| `core.state.silver` | 7 | 7 | 0 | 0 | 100% |
| `core.state.simulation` | 19 | 19 | 0 | 0 | 100% |
| `core.storage` | 1 | 1 | 0 | 0 | 100% |
| `core.storage.snapshot` | 11 | 11 | 0 | 0 | 100% |

### App (`younggeul_app_kr_seoul_apartment`)

| Module | Total | ✅ Full | ⚠️ Partial | ❌ Missing | Coverage |
|--------|-------|---------|------------|------------|----------|
| `younggeul_app_kr_seoul_apartment` | 1 | 1 | 0 | 0 | 100% |
| `app.canonical` | 1 | 1 | 0 | 0 | 100% |
| `app.cli` | 10 | 2 | 8 | 0 | 20% |
| `app.connectors` | 1 | 1 | 0 | 0 | 100% |
| `app.connectors.bok` | 4 | 4 | 0 | 0 | 100% |
| `app.connectors.kostat` | 4 | 4 | 0 | 0 | 100% |
| `app.connectors.molit` | 4 | 4 | 0 | 0 | 100% |
| `app.entity_resolution` | 1 | 1 | 0 | 0 | 100% |
| `app.eval` | 1 | 1 | 0 | 0 | 100% |
| `app.features` | 1 | 1 | 0 | 0 | 100% |
| `app.forecaster` | 3 | 3 | 0 | 0 | 100% |
| `app.pipeline` | 5 | 5 | 0 | 0 | 100% |
| `app.policies` | 1 | 1 | 0 | 0 | 100% |
| `app.reports` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.domain` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.domain.gu_resolver` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.domain.shock_catalog` | 3 | 3 | 0 | 0 | 100% |
| `app.simulation.event_store` | 13 | 13 | 0 | 0 | 100% |
| `app.simulation.events` | 8 | 3 | 5 | 0 | 38% |
| `app.simulation.evidence` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.evidence.store` | 16 | 12 | 4 | 0 | 75% |
| `app.simulation.graph` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.graph_state` | 5 | 5 | 0 | 0 | 100% |
| `app.simulation.llm` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.llm.litellm_adapter` | 5 | 5 | 0 | 0 | 100% |
| `app.simulation.llm.ports` | 4 | 4 | 0 | 0 | 100% |
| `app.simulation.nodes` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.nodes.citation_gate_node` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.continue_gate` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.evidence_builder` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.intake_planner` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.participant_decider` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.report_renderer` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.report_writer` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.round_resolver` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.round_summarizer` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.nodes.scenario_builder` | 4 | 4 | 0 | 0 | 100% |
| `app.simulation.nodes.world_initializer` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.policies` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.policies.heuristic` | 11 | 11 | 0 | 0 | 100% |
| `app.simulation.policies.protocol` | 3 | 3 | 0 | 0 | 100% |
| `app.simulation.policies.registry` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.ports` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.ports.snapshot_reader` | 6 | 6 | 0 | 0 | 100% |
| `app.simulation.replay` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.replay.engine` | 6 | 6 | 0 | 0 | 100% |
| `app.simulation.schemas` | 1 | 1 | 0 | 0 | 100% |
| `app.simulation.schemas.intake` | 2 | 2 | 0 | 0 | 100% |
| `app.simulation.schemas.participant_roster` | 3 | 3 | 0 | 0 | 100% |
| `app.simulation.schemas.report` | 4 | 4 | 0 | 0 | 100% |
| `app.simulation.schemas.round` | 7 | 7 | 0 | 0 | 100% |
| `app.simulation.tracing` | 4 | 4 | 0 | 0 | 100% |
| `app.snapshot` | 3 | 3 | 0 | 0 | 100% |
| `app.transforms` | 1 | 1 | 0 | 0 | 100% |
| `app.transforms.gold_district` | 2 | 2 | 0 | 0 | 100% |
| `app.transforms.gold_enrichment` | 2 | 2 | 0 | 0 | 100% |
| `app.transforms.silver_apt` | 12 | 12 | 0 | 0 | 100% |
| `app.transforms.silver_macro` | 9 | 9 | 0 | 0 | 100% |

## Gap List (Missing & Partial Docstrings)

### Priority: Missing Docstrings

| File | Symbol | Kind | Line |
|------|--------|------|------|

### Lower Priority: Partial Docstrings (missing Args/Returns sections)

| File | Symbol | Kind | Line |
|------|--------|------|------|
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `main` | function | L196 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `ingest_command` | function | L210 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `snapshot_publish_command` | function | L269 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `snapshot_list_command` | function | L303 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `baseline_command` | function | L371 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `simulate_command` | function | L412 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `report_command` | function | L449 |
| `src/younggeul_app_kr_seoul_apartment/cli.py` | `eval_command` | function | L466 |
| `src/younggeul_app_kr_seoul_apartment/simulation/events.py` | `EventStore.append` | method | L28 |
| `src/younggeul_app_kr_seoul_apartment/simulation/events.py` | `EventStore.get_events` | method | L33 |
| `src/younggeul_app_kr_seoul_apartment/simulation/events.py` | `EventStore.get_events_by_type` | method | L38 |
| `src/younggeul_app_kr_seoul_apartment/simulation/events.py` | `EventStore.count` | method | L43 |
| `src/younggeul_app_kr_seoul_apartment/simulation/events.py` | `EventStore.clear` | method | L48 |
| `src/younggeul_app_kr_seoul_apartment/simulation/evidence/store.py` | `EvidenceStore.add` | method | L38 |
| `src/younggeul_app_kr_seoul_apartment/simulation/evidence/store.py` | `EvidenceStore.get` | method | L40 |
| `src/younggeul_app_kr_seoul_apartment/simulation/evidence/store.py` | `EvidenceStore.get_by_kind` | method | L44 |
| `src/younggeul_app_kr_seoul_apartment/simulation/evidence/store.py` | `EvidenceStore.get_by_subject` | method | L46 |
