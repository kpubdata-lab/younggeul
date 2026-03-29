"""Event store implementations for in-memory and file-backed persistence."""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from pathlib import Path

from .events import EventStore, SimulationEvent


class InMemoryEventStore(EventStore):
    """Thread-safe in-memory event store grouped by run ID."""

    def __init__(self) -> None:
        self._events_by_run: dict[str, list[SimulationEvent]] = defaultdict(list)
        self._lock = threading.Lock()

    def append(self, event: SimulationEvent) -> None:
        """Append an event to the in-memory store.

        Args:
            event: Event to persist.
        """
        with self._lock:
            self._events_by_run[event.run_id].append(event)

    def get_events(self, run_id: str) -> list[SimulationEvent]:
        """Return all events for a run sorted by timestamp.

        Args:
            run_id: Simulation run identifier.

        Returns:
            Events associated with the run.
        """
        with self._lock:
            events = list(self._events_by_run.get(run_id, []))
        return sorted(events, key=lambda event: event.timestamp)

    def get_events_by_type(self, run_id: str, event_type: str) -> list[SimulationEvent]:
        """Return events for a run filtered by event type.

        Args:
            run_id: Simulation run identifier.
            event_type: Event type to filter by.

        Returns:
            Matching events sorted by timestamp.
        """
        return [event for event in self.get_events(run_id) if event.event_type == event_type]

    def count(self, run_id: str) -> int:
        """Count events recorded for a run.

        Args:
            run_id: Simulation run identifier.

        Returns:
            Number of stored events.
        """
        with self._lock:
            return len(self._events_by_run.get(run_id, []))

    def clear(self, run_id: str) -> None:
        """Remove all events for a run.

        Args:
            run_id: Simulation run identifier.
        """
        with self._lock:
            self._events_by_run.pop(run_id, None)


class FileEventStore(EventStore):
    """JSONL-backed event store with one file per run."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _run_path(self, run_id: str) -> Path:
        return self._base_dir / f"{run_id}.jsonl"

    def append(self, event: SimulationEvent) -> None:
        """Append an event as a JSON line to the run file.

        Args:
            event: Event to persist.
        """
        line = event.model_dump_json()
        with self._lock:
            with self._run_path(event.run_id).open("a", encoding="utf-8") as file:
                file.write(f"{line}\n")

    def get_events(self, run_id: str) -> list[SimulationEvent]:
        """Load all events for a run sorted by timestamp.

        Args:
            run_id: Simulation run identifier.

        Returns:
            Parsed events for the run.
        """
        run_path = self._run_path(run_id)
        if not run_path.exists():
            return []

        events: list[SimulationEvent] = []
        with run_path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if not stripped:
                    continue
                payload = json.loads(stripped)
                events.append(SimulationEvent.model_validate(payload))

        return sorted(events, key=lambda event: event.timestamp)

    def get_events_by_type(self, run_id: str, event_type: str) -> list[SimulationEvent]:
        """Return events for a run filtered by event type.

        Args:
            run_id: Simulation run identifier.
            event_type: Event type to filter by.

        Returns:
            Matching events sorted by timestamp.
        """
        return [event for event in self.get_events(run_id) if event.event_type == event_type]

    def count(self, run_id: str) -> int:
        """Count persisted events for a run.

        Args:
            run_id: Simulation run identifier.

        Returns:
            Number of events in the run file.
        """
        run_path = self._run_path(run_id)
        if not run_path.exists():
            return 0

        with run_path.open("r", encoding="utf-8") as file:
            return sum(1 for _ in file)

    def clear(self, run_id: str) -> None:
        """Delete the persisted event file for a run.

        Args:
            run_id: Simulation run identifier.
        """
        run_path = self._run_path(run_id)
        with self._lock:
            if run_path.exists():
                run_path.unlink()
