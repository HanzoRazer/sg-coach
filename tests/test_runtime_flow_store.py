"""
Tests for Runtime Flow Store.

Sprint 25: Queue-to-runtime practice session flow.
"""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sg_spec.schemas.runtime_flow import (
    RuntimeSessionEvent,
    RuntimeSessionEventType,
)

from sg_coach.runtime_flow_store import (
    RUNTIME_FLOW_STORE_VERSION,
    RuntimeFlowStore,
)


class TestVersion:
    """Test version constant."""

    def test_version_exists(self) -> None:
        assert RUNTIME_FLOW_STORE_VERSION == "0.1.0"


class TestRuntimeFlowStoreInit:
    """Test RuntimeFlowStore initialization."""

    def test_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store_dir = Path(tmpdir) / "runtime_store"
            store = RuntimeFlowStore(store_dir)

            assert store_dir.exists()

    def test_accepts_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            assert Path(tmpdir).exists()


class TestAppendEvent:
    """Test append_event method."""

    def test_appends_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            event = RuntimeSessionEvent(
                id="rse_test123",
                runtime_session_id="rts_abc123",
                event_type=RuntimeSessionEventType.session_started,
            )

            store.append_event(event)

            assert store.events_file.exists()

    def test_appends_multiple_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            event1 = RuntimeSessionEvent(
                id="rse_test1",
                runtime_session_id="rts_abc123",
                event_type=RuntimeSessionEventType.session_started,
            )
            event2 = RuntimeSessionEvent(
                id="rse_test2",
                runtime_session_id="rts_abc123",
                event_type=RuntimeSessionEventType.session_completed,
            )

            store.append_event(event1)
            store.append_event(event2)

            events = store.list_events()
            assert len(events) == 2

    def test_preserves_event_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            now = datetime.now(timezone.utc)
            event = RuntimeSessionEvent(
                id="rse_test123",
                runtime_session_id="rts_abc123",
                event_type=RuntimeSessionEventType.session_started,
                timestamp=now,
                metadata={"source": "test"},
            )

            store.append_event(event)

            events = store.list_events()
            assert len(events) == 1
            assert events[0].id == "rse_test123"
            assert events[0].runtime_session_id == "rts_abc123"
            assert events[0].event_type == RuntimeSessionEventType.session_started
            assert events[0].metadata["source"] == "test"


class TestListEvents:
    """Test list_events method."""

    def test_returns_empty_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            events = store.list_events()
            assert events == []

    def test_returns_all_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            for i in range(5):
                event = RuntimeSessionEvent(
                    id=f"rse_test{i}",
                    runtime_session_id="rts_abc123",
                    event_type=RuntimeSessionEventType.session_started,
                )
                store.append_event(event)

            events = store.list_events()
            assert len(events) == 5

    def test_filters_by_runtime_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            store.append_event(RuntimeSessionEvent(
                id="rse_1",
                runtime_session_id="rts_session1",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_2",
                runtime_session_id="rts_session2",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_3",
                runtime_session_id="rts_session1",
                event_type=RuntimeSessionEventType.session_completed,
            ))

            session1_events = store.list_events(runtime_session_id="rts_session1")
            assert len(session1_events) == 2
            assert all(e.runtime_session_id == "rts_session1" for e in session1_events)

            session2_events = store.list_events(runtime_session_id="rts_session2")
            assert len(session2_events) == 1


class TestLoadRuntimeSessionEvents:
    """Test load_runtime_session_events method."""

    def test_loads_session_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            store.append_event(RuntimeSessionEvent(
                id="rse_1",
                runtime_session_id="rts_target",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_2",
                runtime_session_id="rts_other",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_3",
                runtime_session_id="rts_target",
                event_type=RuntimeSessionEventType.session_completed,
            ))

            events = store.load_runtime_session_events("rts_target")
            assert len(events) == 2
            assert events[0].id == "rse_1"
            assert events[1].id == "rse_3"

    def test_returns_empty_for_unknown_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            store.append_event(RuntimeSessionEvent(
                id="rse_1",
                runtime_session_id="rts_exists",
                event_type=RuntimeSessionEventType.session_started,
            ))

            events = store.load_runtime_session_events("rts_unknown")
            assert events == []


class TestGetLatestEvent:
    """Test get_latest_event method."""

    def test_returns_latest_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            store.append_event(RuntimeSessionEvent(
                id="rse_1",
                runtime_session_id="rts_test",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_2",
                runtime_session_id="rts_test",
                event_type=RuntimeSessionEventType.outcome_processed,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_3",
                runtime_session_id="rts_test",
                event_type=RuntimeSessionEventType.session_completed,
            ))

            latest = store.get_latest_event("rts_test")
            assert latest is not None
            assert latest.id == "rse_3"
            assert latest.event_type == RuntimeSessionEventType.session_completed

    def test_returns_none_for_unknown_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            latest = store.get_latest_event("rts_unknown")
            assert latest is None

    def test_returns_none_for_empty_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            latest = store.get_latest_event("rts_test")
            assert latest is None


class TestGetSessionStatus:
    """Test get_session_status method."""

    def test_returns_latest_event_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            store.append_event(RuntimeSessionEvent(
                id="rse_1",
                runtime_session_id="rts_test",
                event_type=RuntimeSessionEventType.session_started,
            ))
            store.append_event(RuntimeSessionEvent(
                id="rse_2",
                runtime_session_id="rts_test",
                event_type=RuntimeSessionEventType.session_completed,
            ))

            status = store.get_session_status("rts_test")
            assert status == RuntimeSessionEventType.session_completed

    def test_returns_none_for_unknown_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            status = store.get_session_status("rts_unknown")
            assert status is None


class TestEventsFilePath:
    """Test events_file property."""

    def test_returns_correct_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = RuntimeFlowStore(tmpdir)

            expected = Path(tmpdir) / "runtime_events.jsonl"
            assert store.events_file == expected


class TestPersistence:
    """Test that events persist across store instances."""

    def test_events_persist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = RuntimeFlowStore(tmpdir)

            store1.append_event(RuntimeSessionEvent(
                id="rse_persist",
                runtime_session_id="rts_persist",
                event_type=RuntimeSessionEventType.session_started,
            ))

            store2 = RuntimeFlowStore(tmpdir)

            events = store2.list_events()
            assert len(events) == 1
            assert events[0].id == "rse_persist"
